import json
import logging
import time
from typing import Dict, List, Optional

import redis

LUA_ACQUIRE_ACCOUNT = """
local pool_key = KEYS[1]
local used_key = KEYS[2]
local available_index_key = KEYS[3]
local used_index_key = KEYS[4]
local now = tonumber(ARGV[1])
local max_attempts = tonumber(ARGV[2]) or 50
local attempt = 0

while attempt < max_attempts do
    attempt = attempt + 1
    local payload = redis.call('LPOP', pool_key)
    if not payload then
        return nil
    end

    local ok, account = pcall(cjson.decode, payload)
    if ok and type(account) == 'table' then
        local username = account['username']
        account['in_use'] = true
        account['acquired_at'] = now
        account['released_at'] = nil
        account['cooldown_until'] = nil
        local updated = cjson.encode(account)
        redis.call('LPUSH', used_key, updated)
        if username and username ~= '' then
            redis.call('SREM', available_index_key, username)
            redis.call('SADD', used_index_key, username)
        end
        return updated
    end
end

return nil
"""

LUA_RELEASE_ACCOUNT = """
local used_key = KEYS[1]
local pool_key = KEYS[2]
local used_index_key = KEYS[3]
local available_index_key = KEYS[4]
local cooldown_key = KEYS[5]
local username = ARGV[1]
local cooldown_seconds = tonumber(ARGV[2]) or 0
local now = tonumber(ARGV[3])
local sentinel = '__lua_removed__'

if not username or username == '' then
    return 0
end

local length = redis.call('LLEN', used_key)
local target_payload = nil

for i = 0, length - 1 do
    local payload = redis.call('LINDEX', used_key, i)
    if payload then
        local ok, account = pcall(cjson.decode, payload)
        if ok and type(account) == 'table' and account['username'] == username then
            target_payload = payload
            redis.call('LSET', used_key, i, sentinel)
            break
        end
    end
end

if not target_payload then
    return 0
end

redis.call('LREM', used_key, 1, sentinel)

local ok, account = pcall(cjson.decode, target_payload)
if not ok or type(account) ~= 'table' then
    return 0
end

account['in_use'] = false
account['released_at'] = now
account['acquired_at'] = nil
account['cooldown_until'] = nil

redis.call('SREM', used_index_key, username)
redis.call('SREM', available_index_key, username)

if cooldown_seconds > 0 then
    local ready_at = now + cooldown_seconds
    account['cooldown_until'] = ready_at
    local updated = cjson.encode(account)
    redis.call('ZADD', cooldown_key, ready_at, updated)
    return 1
else
    local updated = cjson.encode(account)
    redis.call('RPUSH', pool_key, updated)
    redis.call('SADD', available_index_key, username)
    return 1
end
"""

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

    def _cooldown_zset_key(self, pool_key: str) -> str:
        return f"{pool_key}:cooldown"

    # ---- 内部工具方法 ------------------------------------------------------
    def _safe_load(self, payload: str, source: str) -> Optional[Dict]:
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            self.logger.warning(f"无法解析账号数据({source}): {payload}")
            return None

    def _normalize_pool(self, client: redis.Redis, pool_key: str) -> None:
        """去重并重建账号池结构，包含冷却集合"""
        used_key = self._used_list_key(pool_key)
        available_index_key = self._available_index_key(pool_key)
        used_index_key = self._used_index_key(pool_key)
        cooldown_key = self._cooldown_zset_key(pool_key)

        available_raw = client.lrange(pool_key, 0, -1)
        used_raw = client.lrange(used_key, 0, -1)
        cooldown_raw = client.zrange(cooldown_key, 0, -1, withscores=True)

        seen_usernames = set()
        normalized_available = []
        normalized_used = []
        normalized_cooldown = []
        available_usernames = []
        used_usernames = []

        # 优先保留占用中的账号
        for entry in used_raw:
            account = self._safe_load(entry, used_key)
            if not account:
                continue
            username = account.get("username")
            if not username or username in seen_usernames:
                continue
            account["in_use"] = True
            account.pop("cooldown_until", None)
            normalized_used.append(json.dumps(account, ensure_ascii=False))
            used_usernames.append(username)
            seen_usernames.add(username)

        # 处理冷却中的账号
        for entry, score in cooldown_raw:
            account = self._safe_load(entry, cooldown_key)
            if not account:
                continue
            username = account.get("username")
            if not username or username in seen_usernames:
                continue
            account["in_use"] = False
            try:
                cooldown_until = float(score)
            except (TypeError, ValueError):
                cooldown_until = time.time() + 5
            account["cooldown_until"] = cooldown_until
            normalized_cooldown.append((json.dumps(account, ensure_ascii=False), cooldown_until))
            seen_usernames.add(username)

        # 最后填充可用账号
        for entry in available_raw:
            account = self._safe_load(entry, pool_key)
            if not account:
                continue
            username = account.get("username")
            if not username or username in seen_usernames:
                continue
            account["in_use"] = False
            account.pop("cooldown_until", None)
            normalized_available.append(json.dumps(account, ensure_ascii=False))
            available_usernames.append(username)
            seen_usernames.add(username)

        with client.pipeline() as pipe:
            pipe.delete(pool_key, used_key, available_index_key, used_index_key, cooldown_key)
            if normalized_available:
                pipe.rpush(pool_key, *normalized_available)
            if normalized_used:
                pipe.rpush(used_key, *normalized_used)
            if normalized_cooldown:
                pipe.zadd(cooldown_key, dict(normalized_cooldown))
            if available_usernames:
                pipe.sadd(available_index_key, *available_usernames)
            if used_usernames:
                pipe.sadd(used_index_key, *used_usernames)
            pipe.execute()

        self.logger.info(
            "账号池重建: 可用 %d 个, 使用中 %d 个, 冷却 %d 个",
            len(available_usernames),
            len(used_usernames),
            len(normalized_cooldown),
        )

    def _requeue_expired_cooldown(self, client: redis.Redis, pool_key: str) -> int:
        """将冷却到期的账号重新加入可用列表"""
        cooldown_key = self._cooldown_zset_key(pool_key)
        available_index_key = self._available_index_key(pool_key)

        while True:
            try:
                with client.pipeline() as pipe:
                    pipe.watch(cooldown_key, pool_key, available_index_key)
                    now = time.time()
                    expired_entries = pipe.zrangebyscore(cooldown_key, 0, now)
                    if not expired_entries:
                        pipe.unwatch()
                        return 0

                    seen_usernames = set()
                    payloads = []
                    usernames = []
                    for entry in expired_entries:
                        account = self._safe_load(entry, cooldown_key)
                        if not account:
                            continue
                        username = account.get("username")
                        if not username or username in seen_usernames:
                            continue
                        account["in_use"] = False
                        account.pop("cooldown_until", None)
                        payloads.append(json.dumps(account, ensure_ascii=False))
                        usernames.append(username)
                        seen_usernames.add(username)

                    pipe.multi()
                    pipe.zremrangebyscore(cooldown_key, 0, now)
                    if payloads:
                        pipe.rpush(pool_key, *payloads)
                    if usernames:
                        pipe.sadd(available_index_key, *usernames)
                    pipe.execute()

                    if payloads:
                        self.logger.info("从冷却池恢复 %d 个账号", len(payloads))
                        return len(payloads)
                    return 0

            except WatchError:
                continue
            except Exception as exc:
                self.logger.error(f"处理冷却账号失败: {exc}")
                return 0

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
            cooldown_key = self._cooldown_zset_key(pool_key)

            with client.pipeline() as pipe:
                pipe.delete(pool_key, used_key, available_index_key, used_index_key, cooldown_key)

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
        """获取账号池的完整列表，包含使用中和冷却中的账号"""
        try:
            client = self.get_redis_client()
            self._ensure_indexes(client, pool_key)
            self._requeue_expired_cooldown(client, pool_key)

            used_key = self._used_list_key(pool_key)
            cooldown_key = self._cooldown_zset_key(pool_key)
            accounts_by_username: Dict[str, Dict] = {}

            for entry in client.lrange(pool_key, 0, -1):
                account = self._safe_load(entry, pool_key)
                if not account:
                    continue
                account["in_use"] = False
                account.pop("cooldown_until", None)
                account["status"] = "available"
                username = account.get("username")
                if username:
                    accounts_by_username[username] = account

            for entry in client.lrange(used_key, 0, -1):
                account = self._safe_load(entry, used_key)
                if not account:
                    continue
                account["in_use"] = True
                account.pop("cooldown_until", None)
                account["status"] = "in_use"
                username = account.get("username")
                if username:
                    accounts_by_username[username] = account

            for payload, score in client.zrange(cooldown_key, 0, -1, withscores=True):
                account = self._safe_load(payload, cooldown_key)
                if not account:
                    continue
                account["in_use"] = False
                try:
                    cooldown_until = float(score)
                except (TypeError, ValueError):
                    cooldown_until = time.time() + 5
                account["cooldown_until"] = cooldown_until
                account["status"] = "cooldown"
                username = account.get("username")
                if username:
                    accounts_by_username[username] = account

            return list(accounts_by_username.values())

        except Exception as exc:
            self.logger.error(f"获取账号列表失败: {exc}")
            return []

    def acquire_account(self, pool_key: str = "account_pool_v3") -> Optional[Dict]:
        """从账号池原子地取出一个账号并标记为使用中"""
        client = self.get_redis_client()
        used_key = self._used_list_key(pool_key)
        available_index_key = self._available_index_key(pool_key)
        used_index_key = self._used_index_key(pool_key)

        while True:
            try:
                self._requeue_expired_cooldown(client, pool_key)
                result = client.eval(
                    LUA_ACQUIRE_ACCOUNT,
                    4,
                    pool_key,
                    used_key,
                    available_index_key,
                    used_index_key,
                    time.time(),
                    100,
                )
                if result is None:
                    self.logger.warning(f"账号池 '{pool_key}' 暂无可用账号")
                    return None

                account = self._safe_load(result, pool_key)
                if account:
                    self.logger.info("取回账号: %s", account.get("username"))
                    return account

            except WatchError:
                continue
            except Exception as exc:
                self.logger.error(f"获取账号失败: {exc}")
                return None
    def release_account(self, account: Dict, pool_key: str = "account_pool_v3", cooldown_seconds: int = 0) -> bool:
        """释放账号，并根据需要推入冷却队列"""
        if not account:
            self.logger.warning("release_account 收到空账号对象")
            return False

        username = account.get("username")
        if not username:
            self.logger.warning(f"release_account 缺少用户名: {account}")
            return False

        client = self.get_redis_client()
        cooldown_seconds = max(0, int(cooldown_seconds or 0))
        used_key = self._used_list_key(pool_key)
        pool_key_main = pool_key
        used_index_key = self._used_index_key(pool_key)
        available_index_key = self._available_index_key(pool_key)
        cooldown_key = self._cooldown_zset_key(pool_key)

        try:
            released = client.eval(
                LUA_RELEASE_ACCOUNT,
                5,
                used_key,
                pool_key_main,
                used_index_key,
                available_index_key,
                cooldown_key,
                username,
                cooldown_seconds,
                time.time(),
            )
            if released:
                if cooldown_seconds > 0:
                    self.logger.info("账号 %s 进入冷却 %s 秒", username, cooldown_seconds)
                else:
                    self.logger.info("释放账号: %s", username)
                return True
            else:
                self.logger.warning(f"账号 '%s' 不在使用列表中，跳过释放", username)
                return False
        except Exception as exc:
            self.logger.error(f"释放账号失败: {exc}")
            return False
    def get_account_status(self, pool_key: str = "account_pool_v3") -> Dict:
        """返回账号池状态统计"""
        try:
            client = self.get_redis_client()
            self._ensure_indexes(client, pool_key)
            self._requeue_expired_cooldown(client, pool_key)

            available_count = client.llen(pool_key)
            used_count = client.llen(self._used_list_key(pool_key))
            cooldown_count = client.zcard(self._cooldown_zset_key(pool_key))
            return {
                "total": available_count + used_count + cooldown_count,
                "in_use": used_count,
                "available": available_count,
                "cooldown": cooldown_count,
            }

        except Exception as exc:
            self.logger.error(f"获取账号状态失败: {exc}")
            return {"total": 0, "in_use": 0, "available": 0, "cooldown": 0}

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
                    if self.release_account(account, pool_key, cooldown_seconds=30):
                        cleaned_count += 1

            if cleaned_count:
                self.logger.info(f"已回收 {cleaned_count} 个超时账号")

            return cleaned_count

        except Exception as exc:
            self.logger.error(f"清理超时账号失败: {exc}")
            return 0

    def release_all_accounts(self, pool_key: str = "account_pool_v3") -> int:
        """逐个释放使用中的账号（无冷却）"""
        try:
            client = self.get_redis_client()
            used_key = self._used_list_key(pool_key)
            used_accounts = client.lrange(used_key, 0, -1)
            released = 0
            for entry in used_accounts:
                account = self._safe_load(entry, used_key)
                if not account:
                    continue
                if self.release_account(account, pool_key, cooldown_seconds=0):
                    released += 1
            self.logger.info("已一键释放 %d 个账号", released)
            return released
        except Exception as exc:
            self.logger.error(f"一键释放账号失败: {exc}")
            return 0
    def remove_duplicate_accounts(self, pool_key: str = "account_pool_v3") -> Dict[str, int]:
        """删除重复账号并返回最新统计"""
        try:
            client = self.get_redis_client()
            used_key = self._used_list_key(pool_key)
            cooldown_key = self._cooldown_zset_key(pool_key)

            available_before = client.llen(pool_key)
            used_before = client.llen(used_key)
            cooldown_before = client.zcard(cooldown_key)

            self._normalize_pool(client, pool_key)

            available_after = client.llen(pool_key)
            used_after = client.llen(used_key)
            cooldown_after = client.zcard(cooldown_key)
            removed = (available_before + used_before + cooldown_before) - (
                available_after + used_after + cooldown_after
            )
            if removed < 0:
                removed = 0

            self.logger.info(
                "删除重复账号: 共移除 %d 个, 可用 %d 个, 使用中 %d 个, 冷却 %d 个",
                removed,
                available_after,
                used_after,
                cooldown_after,
            )
            return {
                "removed": removed,
                "available": available_after,
                "in_use": used_after,
                "cooldown": cooldown_after,
            }
        except Exception as exc:
            self.logger.error(f"删除重复账号失败: {exc}")
            return {"removed": 0, "available": 0, "in_use": 0, "cooldown": 0}

