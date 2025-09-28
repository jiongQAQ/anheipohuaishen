import threading
import time
import logging
from account_manager import AccountManager

logging.basicConfig(level=logging.INFO)

POOL_KEY = "account_pool_v3_concurrent"
TOTAL_ACCOUNTS = 20
THREADS = 50
COOLDOWN_SECONDS = 5
MAX_WAIT_SECONDS = 120

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
    {"username": f"concurrent_user_{i}", "password": "pass"}
    for i in range(1, TOTAL_ACCOUNTS + 1)
]
am.save_accounts(accounts, POOL_KEY)

start_event = threading.Event()
lock = threading.Lock()
results = {}
failures = {}


def worker(idx):
    deadline = time.time() + MAX_WAIT_SECONDS
    attempt = 0
    account = None
    start_event.wait()
    while time.time() < deadline and account is None:
        attempt += 1
        account = am.acquire_account(POOL_KEY)
        if account:
            am.release_account(account, POOL_KEY, cooldown_seconds=COOLDOWN_SECONDS)
            with lock:
                results[idx] = (account.get("username"), attempt)
            return
        time.sleep(0.3)
    with lock:
        failures[idx] = attempt

threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
for t in threads:
    t.start()

start_event.set()

for t in threads:
    t.join()

print(f"[Result] total threads: {THREADS}")
print(f"[Result] success threads: {len(results)}")
print(f"[Result] failed threads: {len(failures)}")
print("[Result] sample successes (thread -> (username, attempts)):")
for idx in sorted(list(results.keys()))[:10]:
    print(f"  {idx}: {results[idx]}")

if failures:
    print("[Result] failures detail:")
    for idx, attempts in failures.items():
        print(f"  thread {idx}: attempts={attempts}")
else:
    print("[Result] all threads acquired an account")

status = am.get_account_status(POOL_KEY)
print("[Status]", status)

client.delete(*keys)
print("[Cleanup] Cleared keys")
