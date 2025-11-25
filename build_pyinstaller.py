"""
PyInstaller打包脚本 - 快速简单
30秒完成打包
"""
import subprocess
import sys
import os

def build_with_pyinstaller():
    """使用PyInstaller打包"""
    
    # PyInstaller打包参数
    pyinstaller_args = [
        sys.executable,
        "-m", "PyInstaller",
        
        # 基本配置
        "--onefile",  # 单文件模式
        "--windowed",  # 无控制台窗口
        "--name=花韵连萌",  # 输出文件名
        
        # 图标配置
        "--icon=resources/logo.ico",
        
        # 包含资源文件
        "--add-data=resources;resources",
        
        # 输出配置
        "--distpath=dist",
        "--workpath=build",
        "--specpath=.",
        
        # 清理旧文件
        "--clean",
        
        # 入口文件
        "main.py"
    ]
    
    print("=" * 60)
    print("🚀 PyInstaller打包模式")
    print("=" * 60)
    print("✅ 速度超快 (30秒)")
    print("✅ 单文件exe")
    print("✅ 简单易用")
    print("⚠️  可能被杀软误报(需要添加信任)")
    print("=" * 60)
    print("\n打包命令:")
    print(" ".join(pyinstaller_args))
    print("\n" + "=" * 60)
    
    try:
        # 执行打包
        result = subprocess.run(pyinstaller_args, check=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ 打包成功!")
            print("可执行文件位置: dist\\花韵连萌.exe")
            print("\n提示:")
            print("1. 如被杀软拦截,请添加到信任名单")
            print("2. 或关闭杀软后运行")
            print("=" * 60)
        else:
            print("\n❌ 打包失败")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包过程出错: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ 未找到PyInstaller，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("安装完成,请重新运行此脚本")
        sys.exit(1)

if __name__ == "__main__":
    build_with_pyinstaller()
