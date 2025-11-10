@echo off
chcp 65001 > nul
echo ====================================
echo 🚀 Trilium Telegram Bot 一键安装
echo ====================================

echo.
echo 📋 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

echo 📦 安装依赖包...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖包安装失败
    pause
    exit /b 1
)

echo ✅ 依赖包安装完成
echo.

echo 📝 创建配置文件...
if not exist .env (
    copy .env.example .env >nul
    echo ✅ 已创建 .env 配置文件
    echo ⚠️  请编辑 .env 文件，填入您的配置信息
    echo.
    echo 配置说明：
    echo 1. TELEGRAM_BOT_TOKEN - 从 @BotFather 获取
    echo 2. TRILIUM_API_TOKEN - 从您的Trilium实例获取
    echo 3. TRILIUM_SERVER_URL - 您的Trilium服务器地址
    echo.
) else (
    echo ✅ 配置文件已存在
)

echo.
echo 🎉 安装完成！
echo.
echo 下一步操作：
echo 1. 编辑 .env 文件，填入配置信息
echo 2. 运行 python run.py 启动程序
echo    或运行 python main.py 直接启动
echo.
pause