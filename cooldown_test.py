import time
import logging
from account_manager import AccountManager

POOL_KEY = "account_pool_v3_test"

logging.basicConfig(level=logging.INFO)

am = AccountManager()
am.update_config(host="118.145.197.212", port=6379, password="redis_AGZ8Gd", db=0)

client = am.get_redis_client()
keys = [POOL_KEY, f"{POOL_KEY}:used", f"{POOL_KEY}:available_index", f"{POOL_KEY}:used_index", f"{POOL_KEY}:cooldown"]
client.delete(*keys)
print("[Setup] Cleared keys:", keys)

accounts = [{"username": "test_success", "password": "pass123"}]
am.save_accounts(accounts, POOL_KEY)
print("[Setup] Seeded 1 account into", POOL_KEY)

# Scenario 1: successful flow (cooldown 5s)
account = am.acquire_account(POOL_KEY)
print("[Scenario1] acquire_account ->", account)
if not account:
    raise SystemExit("Failed to acquire account for scenario 1")

am.release_account(account, POOL_KEY, cooldown_seconds=5)
print("[Scenario1] Released with 5s cooldown")
print("[Scenario1] Available count: ", client.llen(POOL_KEY))
print("[Scenario1] Cooldown count: ", client.zcard(f"{POOL_KEY}:cooldown"))

acc_before_expire = am.acquire_account(POOL_KEY)
print("[Scenario1] Acquire during cooldown ->", acc_before_expire)

print("[Scenario1] Waiting 6 seconds for cooldown to expire...")
time.sleep(6)

acc_after_expire = am.acquire_account(POOL_KEY)
print("[Scenario1] Acquire after cooldown ->", acc_after_expire)
if not acc_after_expire:
    raise SystemExit("Account did not return after cooldown")

# Scenario 2: failure flow (cooldown 30s)
am.release_account(acc_after_expire, POOL_KEY, cooldown_seconds=30)
print("[Scenario2] Released with 30s cooldown")
print("[Scenario2] Available count: ", client.llen(POOL_KEY))
print("[Scenario2] Cooldown count: ", client.zcard(f"{POOL_KEY}:cooldown"))

acc_during_30 = am.acquire_account(POOL_KEY)
print("[Scenario2] Acquire during 30s cooldown ->", acc_during_30)

print("[Scenario2] Waiting 31 seconds for cooldown to expire...")
time.sleep(31)

acc_after_30 = am.acquire_account(POOL_KEY)
print("[Scenario2] Acquire after 30s cooldown ->", acc_after_30)

status = am.get_account_status(POOL_KEY)
print("[Final] Account status:", status)

client.delete(*keys)
print("[Cleanup] Cleared keys again.")
