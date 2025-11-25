"""
Nuitka快速打包脚本 - 适合开发测试
相比正式打包,速度提升3-5倍,但文件体积稍大
"""
import subprocess
import sys
import os

def build_with_nuitka_fast():
    """使用Nuitka快速编译打包(开发模式)"""
    
    # Nuitka编译参数 - 快速模式
    nuitka_args = [
        sys.executable,
        "-m", "nuitka",
        
        # 基本配置
        "--standalone",  # 独立可执行文件模式(不用onefile,快很多)
        "--windows-disable-console",  # 隐藏控制台窗口
        
        # 图标配置
        "--windows-icon-from-ico=resources\\logo.ico",
        
        # 输出配置
        "--output-dir=dist",
        
        # 包含资源文件
        "--include-data-dir=resources=resources",
        
        # PyQt5相关配置
        "--enable-plugin=pyqt5",
        
        # 快速编译优化 - 针对32线程CPU优化
        "--lto=no",  # 禁用LTO,大幅加速
        "--jobs=28",  # 28线程并行(预疙4线程给系统)
        
        # 排除不需要的大型库 - 关键加速点
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=test",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=distutils",
        
        # 快速模式 - 减少优化
        "--python-flag=no_asserts",  # 禁用断言
        
        # 避免误报
        "--assume-yes-for-downloads",
        "--mingw64",
        
        # 显示进度
        "--show-progress",
        
        # 入口文件
        "main.py"
    ]
    
    print("=" * 60)
    print("🚀 快速编译模式 - 适合开发测试")
    print("=" * 60)
    print("优势: 速度快3-5倍")
    print("劣势: 文件夹形式(非单exe), 体积稍大")
    print("=" * 60)
    print("\n编译命令:")
    print(" ".join(nuitka_args))
    print("\n" + "=" * 60)
    
    try:
        # 执行编译
        result = subprocess.run(nuitka_args, check=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ 快速编译成功!")
            print("可执行文件位置: dist\\main.dist\\main.exe")
            print("提示: 整个 dist\\main.dist 文件夹需要一起分发")
            print("=" * 60)
        else:
            print("\n❌ 编译失败")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 编译过程出错: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ 未找到Nuitka，请先安装:")
        print("   pip install nuitka")
        sys.exit(1)

if __name__ == "__main__":
    build_with_nuitka_fast()
