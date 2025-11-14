#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频文件诊断工具
分析Telegram语音文件的格式和兼容性
"""

import os
import sys
import subprocess
import json

def analyze_audio_file(file_path):
    """使用ffprobe分析音频文件"""
    print(f"\n{'='*60}")
    print(f"分析文件: {file_path}")
    print(f"{'='*60}\n")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return None
    
    file_size = os.path.getsize(file_path)
    print(f"文件大小: {file_size} bytes ({file_size/1024:.2f} KB)")
    
    # 使用ffprobe获取详细信息
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            print(f"❌ ffprobe执行失败: {result.stderr}")
            return None
        
        data = json.loads(result.stdout)
        
        # 分析格式信息
        if 'format' in data:
            fmt = data['format']
            print(f"\n📦 容器格式:")
            print(f"  格式名称: {fmt.get('format_name', 'unknown')}")
            print(f"  格式全名: {fmt.get('format_long_name', 'unknown')}")
            print(f"  时长: {float(fmt.get('duration', 0)):.2f} 秒")
            print(f"  比特率: {int(fmt.get('bit_rate', 0))/1000:.1f} kbps")
        
        # 分析音频流信息
        if 'streams' in data:
            for i, stream in enumerate(data['streams']):
                if stream.get('codec_type') == 'audio':
                    print(f"\n🎵 音频流 #{i}:")
                    print(f"  编码格式: {stream.get('codec_name', 'unknown')}")
                    print(f"  编码全名: {stream.get('codec_long_name', 'unknown')}")
                    print(f"  采样率: {stream.get('sample_rate', 'unknown')} Hz")
                    print(f"  声道数: {stream.get('channels', 'unknown')}")
                    print(f"  比特率: {int(stream.get('bit_rate', 0))/1000:.1f} kbps" if 'bit_rate' in stream else "  比特率: 未知")
                    print(f"  时长: {float(stream.get('duration', 0)):.2f} 秒")
        
        return data
        
    except subprocess.TimeoutExpired:
        print("❌ ffprobe执行超时")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return None


def check_compatibility(data):
    """检查与豆包ASR的兼容性"""
    print(f"\n{'='*60}")
    print("兼容性检查")
    print(f"{'='*60}\n")
    
    if not data:
        print("❌ 无法进行兼容性检查")
        return
    
    issues = []
    warnings = []
    
    # 检查格式
    if 'format' in data:
        fmt = data['format']
        format_name = fmt.get('format_name', '')
        
        if 'ogg' not in format_name:
            warnings.append(f"⚠️  容器格式不是OGG: {format_name}")
        
        duration = float(fmt.get('duration', 0))
        if duration == 0:
            issues.append("❌ 音频时长为0，文件可能损坏或为空")
        elif duration < 0.5:
            warnings.append(f"⚠️  音频时长过短: {duration:.2f}秒")
    
    # 检查音频流
    audio_streams = []
    if 'streams' in data:
        for stream in data['streams']:
            if stream.get('codec_type') == 'audio':
                audio_streams.append(stream)
    
    if not audio_streams:
        issues.append("❌ 未找到音频流")
    else:
        stream = audio_streams[0]
        codec_name = stream.get('codec_name', '')
        sample_rate = int(stream.get('sample_rate', 0))
        channels = int(stream.get('channels', 0))
        
        # 豆包ASR要求
        print("豆包ASR要求:")
        print("  - 格式: OGG Opus / MP3 / WAV")
        print("  - 采样率: 16000 Hz (推荐)")
        print("  - 声道: 1 (单声道)")
        print()
        
        print("当前文件:")
        print(f"  - 编码: {codec_name}")
        print(f"  - 采样率: {sample_rate} Hz")
        print(f"  - 声道: {channels}")
        print()
        
        if codec_name != 'opus':
            warnings.append(f"⚠️  音频编码不是Opus: {codec_name}")
        
        if sample_rate != 16000:
            warnings.append(f"⚠️  采样率不是16000: {sample_rate} Hz（可能影响识别效果）")
        
        if channels != 1:
            warnings.append(f"⚠️  不是单声道: {channels}声道")
    
    # 输出结果
    if not issues and not warnings:
        print("✅ 文件格式完全兼容")
    else:
        if issues:
            print("严重问题:")
            for issue in issues:
                print(f"  {issue}")
        
        if warnings:
            print("\n警告:")
            for warning in warnings:
                print(f"  {warning}")
    
    return len(issues) == 0


def convert_for_asr(input_file, output_file):
    """转换音频为ASR兼容格式"""
    print(f"\n{'='*60}")
    print("转换音频格式")
    print(f"{'='*60}\n")
    
    print(f"输入: {input_file}")
    print(f"输出: {output_file}")
    print()
    
    # FFmpeg转换命令
    # 转换为: OGG Opus, 16kHz, 单声道
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-ar', '16000',           # 采样率16kHz
        '-ac', '1',               # 单声道
        '-c:a', 'libopus',        # Opus编码
        '-b:a', '16k',            # 比特率16kbps
        '-f', 'ogg',              # OGG容器
        '-y',                     # 覆盖输出文件
        output_file
    ]
    
    try:
        print("正在转换...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ 转换成功！")
            return True
        else:
            print(f"❌ 转换失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 转换超时")
        return False
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("豆包ASR音频文件诊断工具")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\n用法: python diagnose_audio.py <音频文件路径>")
        print("\n示例:")
        print("  python diagnose_audio.py voice.ogg")
        print("  python diagnose_audio.py voice.mp3")
        return
    
    input_file = sys.argv[1]
    
    # 步骤1: 分析原始文件
    data = analyze_audio_file(input_file)
    
    # 步骤2: 检查兼容性
    compatible = check_compatibility(data)
    
    # 步骤3: 如果不兼容，提供转换建议
    if not compatible and data:
        print(f"\n{'='*60}")
        print("建议")
        print(f"{'='*60}\n")
        print("文件格式可能不完全兼容，建议进行转换。")
        
        response = input("\n是否要转换文件？(y/n): ")
        if response.lower() == 'y':
            output_file = input_file.rsplit('.', 1)[0] + '_converted.ogg'
            if convert_for_asr(input_file, output_file):
                print(f"\n转换后的文件: {output_file}")
                print("请使用转换后的文件进行识别测试。")
    
    print(f"\n{'='*60}")
    print("诊断完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

