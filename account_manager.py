import json
import logging
import time
from typing import Dict, List, Optional

import redis
from redis.exceptions import WatchError


class AccountManager:
    def __init__(self):
        self.logger = logging.getLogger("AccountManager")
        self.redis_client: Optional[redis.Redis] = None
        self.config = {
            "host": "localhost",
            "port": 6379,
            "password": "",
            "db": 0,
        }

    def update_config(self, host="localhost", port=6379, password="", db=0):
        """更新 Redis 连接配置"""
        self.config.update({
            "host": host,
            "port": port,
            "password": password,
            "db": db,
        })

        # 重新建立连接
        self.redis_client = None
        self.logger.info(f"更新 Redis 配置: {host}:{port}, DB: {db}")

    def get_redis_client(self) -> redis.Redis:
        """延迟初始化 Redis 客户端"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(
                    host=self.config["host"],
                    port=self.config["port"],
                    password=self.config["password"] or None,
                    db=self.config["db"],
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                self.redis_client.ping()
                self.logger.info("Redis 连接成功")
            except Exception as exc:
                self.logger.error(f"Redis 连接失败: {exc}")
                self.redis_client = None
                raise

        return self.redis_client

    def test_connection(self) -> bool:
        """测试 Redis 连接是否可用"""
        try:
            client = self.get_redis_client()
            client.ping()
            return True
        except Exception as exc:
            self.logger.error(f"Redis 连接测试失败: {exc}")
            return False

    # ---- Redis key helpers -------------------------------------------------
    def _used_list_key(self, pool_key: str) -> str:
        return f"{pool_key}:used"

    def _available_index_key(self, pool_key: str) -> str:
        return f"{pool_key}:available_index"

    def _used_index_key(self, pool_key: str) -> str:
        return f"{pool_key}:used_index"

    # ---- 内部工具方法 ------------------------------------------------------
    def _safe_load(self, payload: str, source: str) -> Optional[Dict]:
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            self.logger.warning(f"无法解析账号数据({source}): {payload}")
            return None

    def _normalize_pool(self, client: redis.Redis, pool_key: str) -> None:
        """去重并重建账号池和使用池的索引结构"""
        used_key = self._used_list_key(pool_key)
        available_index_key = self._available_index_key(pool_key)
        used_index_key = self._used_index_key(pool_key)

        available_raw = client.lrange(pool_key, 0, -1)
        used_raw = client.lrange(used_key, 0, -1)

        seen_usernames = set()
        normalized_available: List[str] = []
        normalized_used: List[str] = []
        available_usernames: List[str] = []
        used_usernames: List[str] = []

        # 先处理使用池，确保 in_use 状态优先生效
        for entry in used_raw:
            account = self._safe_load(entry, used_key)
            if not account:
                continue
            username = account.get("username")
            if not username or username in seen_usernames:
                continue
            account["in_use"] = True
            normalized_used.append(json.dumps(account, ensure_ascii=False))
            used_usernames.append(username)
            seen_usernames.add(username)

        # 再处理可用池，过滤掉重复账号
        for entry in available_raw:
            account = self._safe_load(entry, pool_key)
            if not account:
                continue
            username = account.get("username")
            if not username or username in seen_usernames:
                continue
            account["in_use"] = False
            normalized_available.append(json.dumps(account, ensure_ascii=False))
            available_usernames.append(username)
            seen_usernames.add(username)

        with client.pipeline() as pipe:
            pipe.delete(pool_key, used_key, available_index_key, used_index_key)
            if normalized_available:
                pipe.rpush(pool_key, *normalized_available)
            if normalized_used:
                pipe.rpush(used_key, *normalized_used)
            if available_usernames:
                pipe.sadd(available_index_key, *available_usernames)
            if used_usernames:
                pipe.sadd(used_index_key, *used_usernames)
            pipe.execute()

        self.logger.info(
            "账号池已去重: 可用 %d 个, 使用中 %d 个", len(available_usernames), len(used_usernames)
        )

    def _ensure_indexes(self, client: redis.Redis, pool_key: str) -> None:
        """检测索引是否缺失或失真，必要时触发修复"""
        used_key = self._used_list_key(pool_key)
        available_index_key = self._available_index_key(pool_key)
        used_index_key = self._used_index_key(pool_key)

        available_len = client.llen(pool_key)
        used_len = client.llen(used_key)
        available_index_len = client.scard(available_index_key) if client.exists(available_index_key) else 0
        used_index_len = client.scard(used_index_key) if client.exists(used_index_key) else 0

        if (
            (available_len and available_len != available_index_len)
            or (used_len and used_len != used_index_len)
            or (available_len and not client.exists(available_index_key))
            or (used_len and not client.exists(used_index_key))
        ):
            self._normalize_pool(client, pool_key)

    # ---- 对外方法 ----------------------------------------------------------
    def save_accounts(self, accounts: List[Dict], pool_key: str = "account_pool_v3") -> bool:
        """保存账号列表到 Redis"""
        try:
            client = self.get_redis_client()
            used_key = self._used_list_key(pool_key)
            available_index_key = self._available_index_key(pool_key)
            used_index_key = self._used_index_key(pool_key)

            seen_usernames = set()
            with client.pipeline() as pipe:
                pipe.delete(pool_key, used_key, available_index_key, used_index_key)

                for account in accounts:
                    username = account.get("username")
                    password = account.get("password")
                    if not username or not password:
                        self.logger.warning(f"忽略无效账号: {account}")
                        continue
                    if username in seen_usernames:
                        self.logger.warning(f"跳过重复账号: {username}")
                        continue

                    seen_usernames.add(username)
                    account_data = {
                        "username": username,
                        "password": password,
                        "in_use": False,
                        "created_at": time.time(),
                    }
                    payload = json.dumps(account_data, ensure_ascii=False)
                    pipe.rpush(pool_key, payload)
                    pipe.sadd(available_index_key, username)

                pipe.execute()

            self.logger.info("成功写入 %d 个账号到 '%s'", len(seen_usernames), pool_key)
            return True

        except Exception as exc:
            self.logger.error(f"保存账号失败: {exc}")
            return False

    def get_all_accounts(self, pool_key: str = "account_pool_v3") -> List[Dict]:
        """获取账号池中全部账号（含使用中）"""
        try:
            client = self.get_redis_client()
            self._ensure_indexes(client, pool_key)

            used_key = self._used_list_key(pool_key)
            accounts_by_username: Dict[str, Dict] = {}

            for entry in client.lrange(pool_key, 0, -1):
                account = self._safe_load(entry, pool_key)
                if not account:
                    continue
                account["in_use"] = False
                username = account.get("username")
                if username:
                    accounts_by_username[username] = account

            for entry in client.lrange(used_key, 0, -1):
                account = self._safe_load(entry, used_key)
                if not account:
                    continue
                account["in_use"] = True
                username = account.get("username")
                if username:
                    accounts_by_username[username] = account

            return list(accounts_by_username.values())

        except Exception as exc:
            self.logger.error(f"获取账号列表失败: {exc}")
            return []

    def acquire_account(self, pool_key: str = "account_pool_v3") -> Optional[Dict]:
        """从账号池取出一个账号，标记为使用中"""
        client = self.get_redis_client()
        used_key = self._used_list_key(pool_key)
        available_index_key = self._available_index_key(pool_key)
        used_index_key = self._used_index_key(pool_key)

        while True:
            try:
                self._ensure_indexes(client, pool_key)
                with client.pipeline() as pipe:
                    pipe.watch(pool_key)
                    account_str = pipe.lindex(pool_key, 0)
                    if account_str is None:
                        pipe.unwatch()
                        self.logger.warning(f"账号池 '{pool_key}' 暂无可用账号")
                        return None

                    account = self._safe_load(account_str, pool_key)
                    if not account:
                        pipe.multi()
                        pipe.lpop(pool_key)
                        pipe.execute()
                        continue

                    username = account.get("username")
                    account["in_use"] = True
                    account["acquired_at"] = time.time()
                    payload = json.dumps(account, ensure_ascii=False)

                    pipe.multi()
                    pipe.lpop(pool_key)
                    pipe.lpush(used_key, payload)
                    if username:
                        pipe.srem(available_index_key, username)
                        pipe.sadd(used_index_key, username)
                    pipe.execute()

                    self.logger.info(f"取出账号: {username}")
                    return account

            except WatchError:
                continue
            except Exception as exc:
                self.logger.error(f"获取账号失败: {exc}")
                return None

    def release_account(self, account: Dict, pool_key: str = "account_pool_v3") -> bool:
        """释放账号并放回账号池"""
        if not account:
            self.logger.warning("release_account 收到空账号对象")
            return False

        username = account.get("username")
        if not username:
            self.logger.warning(f"release_account 缺少用户名: {account}")
            return False

        client = self.get_redis_client()
        used_key = self._used_list_key(pool_key)
        available_index_key = self._available_index_key(pool_key)
        used_index_key = self._used_index_key(pool_key)

        while True:
            try:
                self._ensure_indexes(client, pool_key)
                with client.pipeline() as pipe:
                    pipe.watch(used_key)
                    used_accounts = pipe.lrange(used_key, 0, -1)

                    target_payload = None
                    target_account: Optional[Dict] = None
                    for entry in used_accounts:
                        candidate = self._safe_load(entry, used_key)
                        if candidate and candidate.get("username") == username:
                            target_payload = entry
                            target_account = candidate
                            break

                    if target_payload is None or target_account is None:
                        pipe.unwatch()
                        self.logger.warning(f"账号 '{username}' 不在使用池中，跳过释放")
                        return False

                    target_account["in_use"] = False
                    target_account.pop("acquired_at", None)
                    target_account["released_at"] = time.time()
                    payload = json.dumps(target_account, ensure_ascii=False)

                    pipe.multi()
                    pipe.lrem(used_key, 1, target_payload)
                    pipe.rpush(pool_key, payload)
                    pipe.srem(used_index_key, username)
                    pipe.sadd(available_index_key, username)
                    pipe.execute()

                    self.logger.info(f"释放账号: {username}")
                    return True

            except WatchError:
                continue
            except Exception as exc:
                self.logger.error(f"释放账号失败: {exc}")
                return False

    def get_account_status(self, pool_key: str = "account_pool_v3") -> Dict:
        """返回账号池状态统计"""
        try:
            client = self.get_redis_client()
            self._ensure_indexes(client, pool_key)

            available_count = client.llen(pool_key)
            used_count = client.llen(self._used_list_key(pool_key))
            return {
                "total": available_count + used_count,
                "in_use": used_count,
                "available": available_count,
            }

        except Exception as exc:
            self.logger.error(f"获取账号状态失败: {exc}")
            return {"total": 0, "in_use": 0, "available": 0}

    def cleanup_expired_accounts(self, pool_key: str = "account_pool_v3", timeout: int = 3600) -> int:
        """释放超过 timeout 秒未归还的账号"""
        try:
            client = self.get_redis_client()
            self._ensure_indexes(client, pool_key)

            current_time = time.time()
            used_key = self._used_list_key(pool_key)
            cleaned_count = 0

            for entry in client.lrange(used_key, 0, -1):
                account = self._safe_load(entry, used_key)
                if not account:
                    continue

                acquired_at = account.get("acquired_at")
                if (
                    account.get("in_use")
                    and isinstance(acquired_at, (int, float))
                    and current_time - acquired_at > timeout
                ):
                    if self.release_account(account, pool_key):
                        cleaned_count += 1

            if cleaned_count:
                self.logger.info(f"已回收 {cleaned_count} 个超时账号")

            return cleaned_count

        except Exception as exc:
            self.logger.error(f"清理超时账号失败: {exc}")
            return 0

    def release_all_accounts(self, pool_key: str = "account_pool_v3") -> int:
        """一键释放所有正在使用的账号"""
        try:
            client = self.get_redis_client()
            self._ensure_indexes(client, pool_key)

            used_key = self._used_list_key(pool_key)
            available_index_key = self._available_index_key(pool_key)
            used_index_key = self._used_index_key(pool_key)

            while True:
                try:
                    with client.pipeline() as pipe:
                        pipe.watch(used_key, pool_key, available_index_key, used_index_key)
                        used_accounts = pipe.lrange(used_key, 0, -1)
                        if not used_accounts:
                            pipe.unwatch()
                            self.logger.info("没有正在使用的账号需要释放")
                            return 0

                        release_payloads: List[str] = []
                        usernames: List[str] = []
                        for entry in used_accounts:
                            account = self._safe_load(entry, used_key)
                            if not account:
                                continue
                            account["in_use"] = False
                            account.pop("acquired_at", None)
                            account["released_at"] = time.time()
                            release_payloads.append(json.dumps(account, ensure_ascii=False))
                            username = account.get("username")
                            if username:
                                usernames.append(username)

                        if not release_payloads:
                            pipe.unwatch()
                            return 0

                        pipe.multi()
                        pipe.delete(used_key)
                        pipe.rpush(pool_key, *release_payloads)
                        if usernames:
                            pipe.srem(used_index_key, *usernames)
                            pipe.sadd(available_index_key, *usernames)
                        pipe.execute()

                        self.logger.info("已一键释放 %d 个账号", len(release_payloads))
                        self._normalize_pool(client, pool_key)
                        return len(release_payloads)

                except WatchError:
                    continue
        except Exception as exc:
            self.logger.error(f"一键释放账号失败: {exc}")
            return 0

    def remove_duplicate_accounts(self, pool_key: str = "account_pool_v3") -> Dict[str, int]:
        """删除重复账号并返回最新统计"""
        try:
            client = self.get_redis_client()
            used_key = self._used_list_key(pool_key)

            available_before = client.llen(pool_key)
            used_before = client.llen(used_key)

            self._normalize_pool(client, pool_key)

            available_after = client.llen(pool_key)
            used_after = client.llen(used_key)
            removed = (available_before + used_before) - (available_after + used_after)
            if removed < 0:
                removed = 0

            self.logger.info(
                "删除重复账号: 共移除 %d 个, 可用 %d 个, 使用中 %d 个",
                removed,
                available_after,
                used_after,
            )
            return {
                "removed": removed,
                "available": available_after,
                "in_use": used_after,
            }
        except Exception as exc:
            self.logger.error(f"删除重复账号失败: {exc}")
            return {"removed": 0, "available": 0, "in_use": 0}

