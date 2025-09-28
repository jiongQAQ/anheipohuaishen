import threading
import time
import logging
from account_manager import AccountManager

logging.basicConfig(level=logging.INFO)

POOL_KEY = "account_pool_v3_fail30"
TOTAL_ACCOUNTS = 5
THREADS = 10
FAIL_COOLDOWN = 30
MAX_WAIT_SECONDS = 180

am = AccountManager()
am.update_config(host="118.145.197.212", port=6379, password="redis_AGZ8Gd", db=0)
client = am.get_redis_client()

keys = [
    POOL_KEY,
    f"{POOL_KEY}:used",
    f"{POOL_KEY}:available_index",
    f"{POOL_KEY}:used_index",
    f"{POOL_KEY}:cooldown",
]
client.delete(*keys)
accounts = [
    {"username": f"fail30_user_{i}", "password": "pass"}
    for i in range(1, TOTAL_ACCOUNTS + 1)
]
am.save_accounts(accounts, POOL_KEY)

start_event = threading.Event()
lock = threading.Lock()
results = {}


def worker(idx):
    start_event.wait()
    deadline = time.time() + MAX_WAIT_SECONDS
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        account = am.acquire_account(POOL_KEY)
        if account:
            # 模拟失败后进入 30 秒冷却
            am.release_account(account, POOL_KEY, cooldown_seconds=FAIL_COOLDOWN)
            with lock:
                results[idx] = (account.get("username"), attempt)
            return
        time.sleep(0.5)
    with lock:
        results[idx] = (None, attempt)

threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
for t in threads:
    t.start()

start_event.set()
for t in threads:
    t.join()

failures = [idx for idx, (name, _) in results.items() if name is None]
print("[Scenario] thread results:")
for idx in sorted(results.keys()):
    print(f"  thread {idx}: {results[idx]}")

print(f"[Summary] total threads: {THREADS}")
print(f"[Summary] success threads: {THREADS - len(failures)}")
print(f"[Summary] failed threads: {len(failures)} {failures}")

status = am.get_account_status(POOL_KEY)
print("[Status]", status)

client.delete(*keys)
print("[Cleanup] Cleared keys")
