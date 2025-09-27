#!/usr/bin/env python3
"""
测试账号管理的并发安全性
"""
import time
import threading
from account_manager import AccountManager
import json

def test_concurrent_acquire():
    """测试并发获取账号"""
    
    # 创建账号管理器
    am = AccountManager()
    
    # 配置Redis连接（使用项目中的配置）
    am.update_config(
        host="118.145.197.212",
        port=6379,
        password="redis_AGZ8Gd",
        db=0
    )
    
    # 准备测试账号
    test_accounts = [
        {"username": "test1", "password": "pass1"},
        {"username": "test2", "password": "pass2"},
        {"username": "test3", "password": "pass3"},
    ]
    
    # 保存测试账号
    print("🔧 保存测试账号...")
    am.save_accounts(test_accounts, "test_pool")
    
    # 存储获取结果
    acquired_accounts = []
    results_lock = threading.Lock()
    
    def worker(worker_id):
        """工作线程"""
        print(f"🚀 工作线程 {worker_id} 开始")
        
        # 尝试获取账号
        account = am.acquire_account("test_pool")
        
        with results_lock:
            if account:
                acquired_accounts.append((worker_id, account["username"]))
                print(f"✅ 工作线程 {worker_id} 获取账号: {account['username']}")
            else:
                print(f"❌ 工作线程 {worker_id} 未获取到账号")
        
        # 模拟使用账号
        time.sleep(2)
        
        # 释放账号
        if account:
            am.release_account(account, "test_pool")
            print(f"🔄 工作线程 {worker_id} 释放账号: {account['username']}")
    
    # 创建多个线程同时获取账号
    threads = []
    for i in range(5):  # 5个线程竞争3个账号
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
    
    # 启动所有线程
    print("\n🏁 启动并发测试...")
    for t in threads:
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    print("\n📊 测试结果:")
    print(f"总共获取到账号: {len(acquired_accounts)}")
    print(f"获取的账号: {[acc[1] for acc in acquired_accounts]}")
    
    # 检查是否有重复
    usernames = [acc[1] for acc in acquired_accounts]
    if len(usernames) == len(set(usernames)):
        print("✅ 测试通过：没有重复获取账号")
    else:
        print("❌ 测试失败：存在重复获取账号")
    
    # 清理测试数据
    print("\n🧹 清理测试数据...")
    am.get_redis_client().delete("test_pool", "test_pool:used")
    
    print("✅ 测试完成")

if __name__ == "__main__":
    test_concurrent_acquire() 