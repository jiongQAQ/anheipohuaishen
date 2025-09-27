@echo off
chcp 65001 >nul
title 自动化任务管理工具 v3 打包器

echo.
echo ==============================================
echo     自动化任务管理工具 v3 打包器
echo ==============================================
echo.

echo 📋 正在检查环境...

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python，请确保Python已正确安装并添加到PATH
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

REM 检查PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到PyInstaller，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ PyInstaller安装失败
        pause
        exit /b 1
    )
)

echo ✅ PyInstaller检查通过

REM 检查主程序文件
if not exist "main.py" (
    echo ❌ 错误：未找到main.py文件
    pause
    exit /b 1
)

echo ✅ 项目文件检查通过

echo.
echo 🚀 开始执行打包...
echo.

REM 执行打包脚本
python build_exe_v3.py

if errorlevel 1 (
    echo.
    echo ❌ 打包失败！
    pause
    exit /b 1
)

echo.
echo 🎉 打包完成！
echo.
echo 📁 请查看 release_v3 目录中的文件
echo.

REM 尝试打开发布目录
if exist "release_v3" (
    echo 📂 正在打开发布目录...
    start "" "release_v3"
)

echo.
echo ✅ 操作完成，按任意键退出...
pause >nul 