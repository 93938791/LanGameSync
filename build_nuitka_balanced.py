"""
Nuitka平衡版打包脚本 - 推荐方案
速度快(5-8分钟) + 防误报 + 单文件exe
"""
import subprocess
import sys
import os

def build_with_nuitka_balanced():
    """使用Nuitka平衡模式编译打包"""
    
    # Nuitka编译参数 - 平衡模式
    nuitka_args = [
        sys.executable,
        "-m", "nuitka",
        
        # 基本配置
        "--standalone",  # 独立可执行文件模式
        "--onefile",  # 单文件模式
        "--windows-disable-console",  # 隐藏控制台窗口
        
        # 图标配置
        "--windows-icon-from-ico=resources\\logo.ico",
        
        # 输出配置
        "--output-dir=dist",
        "--output-filename=花韵连萌.exe",
        
        # 包含资源文件
        "--include-data-dir=resources=resources",
        
        # PyQt5相关配置
        "--enable-plugin=pyqt5",
        
        # 性能优化 - 平衡模式
        "--lto=no",  # 禁用LTO,大幅加速(牺牲5-10%性能,但仍比PyInstaller快)
        "--jobs=28",  # 28线程并行
        
        # 排除不需要的大型库 - 关键加速点
        "--nofollow-import-to=scipy",  # 排除scipy(科学计算库,项目未使用)
        "--nofollow-import-to=matplotlib",  # 排除matplotlib
        "--nofollow-import-to=pandas",  # 排除pandas
        "--nofollow-import-to=tkinter",  # 排除tkinter
        "--nofollow-import-to=test",  # 排除测试模块
        "--nofollow-import-to=unittest",  # 排除单元测试
        "--nofollow-import-to=distutils",  # 排除distutils
        
        # 避免误报的关键配置
        "--assume-yes-for-downloads",  # 自动下载依赖
        "--mingw64",  # 使用MinGW编译器(更干净的二进制)
        
        # 显示进度
        "--show-progress",
        "--show-memory",
        
        # 入口文件
        "main.py"
    ]
    
    print("=" * 60)
    print("🎯 平衡模式 - 推荐方案")
    print("=" * 60)
    print("✅ 单文件exe (便于分发)")
    print("✅ 防杀软误报 (Nuitka编译)")
    print("✅ 速度快 (5-8分钟, 排除scipy)")
    print("✅ 性能好 (仍比PyInstaller快)")
    print("=" * 60)
    print("\n编译命令:")
    print(" ".join(nuitka_args))
    print("\n" + "=" * 60)
    
    try:
        # 执行编译
        result = subprocess.run(nuitka_args, check=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ 编译成功!")
            print("可执行文件位置: dist\\花韵连萌.exe")
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
    build_with_nuitka_balanced()
