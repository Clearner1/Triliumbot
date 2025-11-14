#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
豆包ASR连接测试工具
用于验证API密钥配置和WebSocket连接
"""

import sys
import os
import io

# 设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from asr import DoubaoASRClient
import logging

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_api_key_format():
    """测试API密钥格式"""
    print("\n" + "="*60)
    print("测试1: API密钥格式检查")
    print("="*60)
    
    app_key = Config.DOUBAO_APP_KEY
    access_key = Config.DOUBAO_ACCESS_KEY
    
    print(f"APP_KEY: {app_key}")
    print(f"ACCESS_KEY: {access_key[:20]}...{access_key[-10:] if len(access_key) > 30 else ''}")
    print(f"APP_KEY长度: {len(app_key)}")
    print(f"ACCESS_KEY长度: {len(access_key)}")
    
    # 检查APP_KEY格式
    issues = []
    
    if app_key.startswith('api-key-'):
        issues.append("❌ APP_KEY不应包含'api-key-'前缀")
        issues.append("   正确格式应该是纯数字，例如：123456789")
    
    if not app_key.isdigit():
        issues.append("❌ APP_KEY应该是纯数字")
        issues.append("   当前包含非数字字符")
    
    if len(app_key) < 8 or len(app_key) > 15:
        issues.append("⚠️  APP_KEY长度异常")
        issues.append(f"   通常APP_KEY是9-12位数字，当前长度：{len(app_key)}")
    
    if len(access_key) < 20:
        issues.append("⚠️  ACCESS_KEY长度可能过短")
    
    if issues:
        print("\n发现问题：")
        for issue in issues:
            print(issue)
        return False
    else:
        print("\n✅ API密钥格式看起来正确")
        return True


def test_websocket_connection():
    """测试WebSocket连接"""
    print("\n" + "="*60)
    print("测试2: WebSocket连接测试")
    print("="*60)
    
    try:
        client = DoubaoASRClient(
            app_key=Config.DOUBAO_APP_KEY,
            access_key=Config.DOUBAO_ACCESS_KEY
        )
        
        print("正在尝试连接WebSocket...")
        result = client._connect()
        
        if result:
            print("✅ WebSocket连接成功！")
            client._close()
            return True
        else:
            print("❌ WebSocket连接失败")
            return False
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        
        # 分析错误
        error_str = str(e)
        if "401" in error_str and "Unauthorized" in error_str:
            print("\n错误分析：")
            print("- 这是认证错误，API密钥不正确或已过期")
            print("- 请检查APP_KEY和ACCESS_KEY是否正确")
            print("- 确认在火山引擎控制台获取的密钥格式")
        elif "load grant" in error_str:
            print("\n错误分析：")
            print("- 服务器无法找到对应的授权信息")
            print("- 可能的原因：")
            print("  1. APP_KEY格式错误（应该是纯数字）")
            print("  2. ACCESS_KEY已过期或无效")
            print("  3. 项目未启用或已停用")
        
        return False


def test_config_source():
    """测试配置来源"""
    print("\n" + "="*60)
    print("测试3: 配置来源检查")
    print("="*60)
    
    import os
    from dotenv import load_dotenv
    
    # 检查.env文件
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_file):
        print(f"✓ 找到.env文件: {env_file}")
        load_dotenv(env_file)
        
        env_app_key = os.getenv('DOUBAO_APP_KEY')
        env_access_key = os.getenv('DOUBAO_ACCESS_KEY')
        
        if env_app_key:
            print(f"  DOUBAO_APP_KEY (from .env): {env_app_key}")
        if env_access_key:
            print(f"  DOUBAO_ACCESS_KEY (from .env): {env_access_key[:20]}...")
    else:
        print(f"✗ 未找到.env文件: {env_file}")
    
    # 检查config.py中的默认值
    print(f"\nconfig.py中的配置:")
    print(f"  DOUBAO_APP_KEY: {Config.DOUBAO_APP_KEY}")
    print(f"  DOUBAO_ACCESS_KEY: {Config.DOUBAO_ACCESS_KEY[:20]}...")
    
    # 检查env.md文件
    env_md = os.path.join(os.path.dirname(__file__), 'env.md')
    if os.path.exists(env_md):
        print(f"\n✓ 找到env.md文件: {env_md}")
        with open(env_md, 'r', encoding='utf-8') as f:
            content = f.read()
            print("内容预览：")
            for line in content.split('\n')[:5]:
                print(f"  {line}")


def generate_fix_instructions():
    """生成修复指南"""
    print("\n" + "="*60)
    print("修复指南")
    print("="*60)
    
    print("\n请按以下步骤修复API密钥配置：")
    print("\n步骤1: 获取正确的API密钥")
    print("------")
    print("1. 访问：https://console.volcengine.com/")
    print("2. 进入「语音技术」→「项目管理」")
    print("3. 创建或选择一个项目")
    print("4. 获取：")
    print("   - APP ID (纯数字，例如：123456789)")
    print("   - Access Token")
    
    print("\n步骤2: 更新配置（选择一种方法）")
    print("------")
    print("方法A - 修改 asr/env.md:")
    print("""
X-Api-App-Key:你的纯数字APP_ID
X-Api-Access-Key:你的Access_Token
    """)
    
    print("方法B - 修改 config.py:")
    print("""
DOUBAO_APP_KEY = '你的纯数字APP_ID'
DOUBAO_ACCESS_KEY = '你的Access_Token'
    """)
    
    print("方法C - 创建 .env 文件:")
    print("""
DOUBAO_APP_KEY=你的纯数字APP_ID
DOUBAO_ACCESS_KEY=你的Access_Token
    """)
    
    print("\n步骤3: 重新运行测试")
    print("------")
    print("python asr/test_asr_connection.py")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("豆包ASR连接测试工具")
    print("="*60)
    
    print(f"\nASR功能状态: {'启用' if Config.ASR_ENABLED else '禁用'}")
    
    if not Config.ASR_ENABLED:
        print("\n⚠️  ASR功能已禁用")
        print("如需测试，请在config.py中设置 ASR_ENABLED = True")
        return
    
    # 运行测试
    results = {
        'format': test_api_key_format(),
        'connection': False,  # 暂不测试，等格式正确后再测
    }
    
    # 如果格式正确，再测试连接
    if results['format']:
        results['connection'] = test_websocket_connection()
    else:
        print("\n⚠️  跳过连接测试（API密钥格式不正确）")
    
    # 显示配置来源
    test_config_source()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    if results['format'] and results['connection']:
        print("\n🎉 所有测试通过！API配置正确，可以正常使用。")
    elif results['format'] and not results['connection']:
        print("\n⚠️  格式正确但连接失败")
        print("可能原因：")
        print("- ACCESS_KEY不正确或已过期")
        print("- 项目未启用")
        print("- 网络问题")
    else:
        print("\n❌ 测试失败，需要修复API密钥配置")
        generate_fix_instructions()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

