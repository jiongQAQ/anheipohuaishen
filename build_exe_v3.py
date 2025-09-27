#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化任务管理工具 v3 打包脚本
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("🚀 开始打包自动化任务管理工具 v3...")
    
    # 项目信息
    app_name = "自动化任务管理工具"
    version = "3.1.0"
    main_script = "main.py"
    
    # 确保在正确的目录
    if not os.path.exists(main_script):
        print(f"❌ 错误：找不到主程序文件 {main_script}")
        sys.exit(1)
    
    # 清理之前的构建
    build_dirs = ["build", "dist", "__pycache__"]
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            print(f"🧹 清理目录: {dir_name}")
            shutil.rmtree(dir_name, ignore_errors=True)
    
    # 清理 .spec 文件
    spec_files = [f for f in os.listdir(".") if f.endswith(".spec")]
    for spec_file in spec_files:
        print(f"🧹 清理文件: {spec_file}")
        os.remove(spec_file)
    
    # PyInstaller 打包命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", f"{app_name}_v3",
        "--onefile",  # 打包成单个exe文件
        "--windowed",  # 无控制台窗口
        "--noconfirm",  # 不询问确认
        
        # 包含额外的Python模块
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui", 
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "win32gui",
        "--hidden-import", "win32con",
        "--hidden-import", "win32api",
        "--hidden-import", "win32process",
        "--hidden-import", "psutil",
        "--hidden-import", "redis",
        "--hidden-import", "pyautogui",
        "--hidden-import", "uuid",
        "--hidden-import", "hashlib",
        "--hidden-import", "platform",
        "--hidden-import", "subprocess",
        
        # 添加数据文件
        "--add-data", "config.json;.",
        "--add-data", "requirements.txt;.",
        
        # 收集所有子模块
        "--collect-submodules", "PyQt5",
        "--collect-submodules", "pyautogui",
        
        # 主程序
        main_script
    ]
    
    print("🔧 执行PyInstaller打包命令...")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print("✅ PyInstaller 执行成功")
        if result.stdout:
            print("输出:", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller 执行失败: {e}")
        if e.stdout:
            print("标准输出:", e.stdout)
        if e.stderr:
            print("错误输出:", e.stderr)
        sys.exit(1)
    
    # 检查生成的文件
    exe_path = f"dist/{app_name}_v3.exe"
    if os.path.exists(exe_path):
        file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
        print(f"✅ 打包成功！")
        print(f"📁 文件位置: {os.path.abspath(exe_path)}")
        print(f"📊 文件大小: {file_size:.1f} MB")
        
        # 创建发布目录
        release_dir = "release_v3"
        if os.path.exists(release_dir):
            shutil.rmtree(release_dir)
        os.makedirs(release_dir)
        
        # 复制exe文件
        release_exe = os.path.join(release_dir, f"{app_name}_v3.exe")
        shutil.copy2(exe_path, release_exe)
        print(f"📦 已复制到发布目录: {os.path.abspath(release_exe)}")
        
        # 复制重要文件到发布目录
        important_files = [
            "config.json",
            "requirements.txt", 
            "README.md",
            "运行时间记录功能说明.md"
        ]
        
        for file_name in important_files:
            if os.path.exists(file_name):
                shutil.copy2(file_name, release_dir)
                print(f"📄 已复制: {file_name}")
        
        # 创建版本信息文件
        version_info = f"""# 自动化任务管理工具 v3.1.0

## 版本信息
- 版本号: {version}
- 打包时间: {subprocess.run(['powershell', 'Get-Date -Format "yyyy-MM-dd HH:mm:ss"'], capture_output=True, text=True).stdout.strip()}
- 文件大小: {file_size:.1f} MB

## v3.0.2 功能特性
🚀 **账号轮换策略优化** - 提升账号利用效率和任务成功率
   - 重试次数优化: 每个账号从3次重试改为1次尝试
   - 无限账号轮换: 移除最多5个账号的限制，支持无限轮换
   - 快速切换: 失败即切换，大幅提升账号轮换速度
   - 智能计数: 清晰显示当前使用第几个账号

## v3.0.1 & v3.0.0 核心功能
✅ Redis账号池并发安全 - 解决多台电脑同时使用时的账号冲突问题
✅ 软件B运行时间记录 - 自动记录开始、结束时间和运行持续时间
✅ 软件B启动检测优化 - 等待时间从30秒延长到20秒
✅ 智能账号切换逻辑 - 完全重启进程确保环境干净

## 使用方法
1. 双击 {app_name}_v3.exe 运行
2. 根据界面提示配置Redis和软件路径
3. 使用Ctrl+3记录5个坐标点
4. 添加账号到Redis账号池
5. 点击"开始任务"即可

## 文件说明
- {app_name}_v3.exe - 主程序
- config.json - 配置文件模板
- requirements.txt - 依赖包列表
- README.md - 详细使用说明
- 运行时间记录功能说明.md - 运行时间记录功能说明

## 注意事项
- 需要Redis服务器支持
- 建议在Windows 10/11系统上使用
- 首次运行可能需要管理员权限
"""
        
        with open(os.path.join(release_dir, "版本说明_v3.1.0.txt"), 'w', encoding='utf-8') as f:
            f.write(version_info)
        
        print(f"\n🎉 打包完成！")
        print(f"📁 发布目录: {os.path.abspath(release_dir)}")
        print(f"🚀 可执行文件: {app_name}_v3.exe")
        
    else:
        print(f"❌ 错误：未找到生成的exe文件 {exe_path}")
        sys.exit(1)

if __name__ == "__main__":
    main() 