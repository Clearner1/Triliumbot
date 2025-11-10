#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
便捷启动脚本
"""

import sys
import os
import subprocess

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 9):
        print("❌ 错误: 需要 Python 3.9 或更高版本")
        print(f"当前版本: {sys.version}")
        sys.exit(1)
    else:
        print(f"✅ Python版本检查通过: {sys.version}")

def check_dependencies():
    """检查依赖包"""
    try:
        import telegram
        import trilium_py
        import dotenv
        print("✅ 核心依赖包检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def check_config():
    """检查配置文件"""
    if not os.path.exists('.env'):
        print("❌ 找不到 .env 配置文件")
        print("请复制 .env.example 为 .env 并配置相关信息")
        return False

    try:
        from dotenv import load_dotenv
        load_dotenv()

        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        trilium_token = os.getenv('TRILIUM_API_TOKEN')
        trilium_url = os.getenv('TRILIUM_SERVER_URL')

        if not all([telegram_token, trilium_token, trilium_url]):
            print("❌ 配置文件中缺少必要信息")
            return False

        print("✅ 配置文件检查通过")
        return True

    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

def install_dependencies():
    """安装依赖包"""
    print("📦 正在安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖包安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖包安装失败")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("🚀 Trilium Telegram Bot 启动器")
    print("=" * 50)

    # 检查Python版本
    check_python_version()

    # 检查依赖包
    if not check_dependencies():
        # 尝试自动安装
        if input("是否自动安装依赖包? (y/n): ").lower() == 'y':
            if not install_dependencies():
                sys.exit(1)
        else:
            sys.exit(1)

    # 检查配置
    if not check_config():
        sys.exit(1)

    print("\n🎉 所有检查通过，正在启动程序...")
    print("=" * 50)

    # 启动主程序
    try:
        from main import main as start_bot
        start_bot()
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序启动失败: {e}")
        print("请检查配置和网络连接")
        sys.exit(1)

if __name__ == "__main__":
    main()