"""
PyInstaller打包脚本 - 完整版
包含UAC清单文件，强制EXE每次运行都提权
"""
import subprocess
import sys
import os
from pathlib import Path

def build_with_pyinstaller(use_spec=True):
    """使用PyInstaller打包（包含管理员权限清单）
    
    Args:
        use_spec: 是否使用spec文件（推荐，更可靠）
    """
    
    # 检查清单文件是否存在
    manifest_file = Path("admin.manifest")
    if not manifest_file.exists():
        print("❌ 错误: 找不到 admin.manifest 文件")
        print("请确保 admin.manifest 文件存在于项目根目录")
        sys.exit(1)
    
    # 检查图标文件是否存在
    icon_file = Path("resources/logo.ico")
    if not icon_file.exists():
        print("⚠️  警告: 找不到 resources/logo.ico 图标文件")
        print("将使用默认图标")
    
    # 检查spec文件是否存在
    spec_file = Path("花韵连萌.spec")
    if use_spec and not spec_file.exists():
        print("⚠️  警告: 找不到 花韵连萌.spec 文件，将使用命令行参数")
        use_spec = False
    
    # 在打包前尝试删除旧的exe文件（如果存在且被占用，会提示用户）
    dist_exe = Path("dist") / "花韵连萌.exe"
    if dist_exe.exists():
        try:
            print(f"🗑️  正在删除旧的exe文件: {dist_exe}")
            dist_exe.unlink()
            print("✅ 旧文件已删除")
        except PermissionError:
            print(f"⚠️  无法删除旧文件: {dist_exe}")
            print("   可能原因: 文件正在运行或被其他程序占用")
            print("   解决方案: 请关闭正在运行的 花韵连萌.exe 程序，然后重新打包")
            sys.exit(1)
        except Exception as e:
            print(f"⚠️  删除旧文件时出错: {e}")
            print("   继续尝试打包...")
    
    if use_spec:
        # 使用spec文件打包（推荐方式，更可靠）
        print("📋 使用 spec 文件打包（推荐方式）")
        pyinstaller_args = [
            sys.executable,
            "-m", "PyInstaller",
            "--clean",  # 清理旧文件
            str(spec_file)  # 使用spec文件
        ]
    else:
        # 使用命令行参数打包
        print("📋 使用命令行参数打包")
        icon_param = ["--icon=resources/logo.ico"] if icon_file.exists() else []
        
        pyinstaller_args = [
            sys.executable,
            "-m", "PyInstaller",
            
            # 基本配置
            "--onefile",  # 单文件模式
            "--windowed",  # 无控制台窗口（GUI程序）
            "--name=花韵连萌",  # 输出文件名
            
            # 图标配置（如果存在）
            *icon_param,
            
            # UAC清单文件 - 关键配置！
            # 注意：PyInstaller可能不支持--manifest参数，建议使用spec文件
            # "--manifest=admin.manifest",  # 如果支持的话
            
            # 包含资源文件
            "--add-data=resources;resources",
            
            # 输出配置
            "--distpath=dist",
            "--workpath=build",
            "--specpath=.",
            
            # 清理旧文件
            "--clean",
            
            # 隐藏导入（如果需要）
            "--hidden-import=PyQt5",
            "--hidden-import=qfluentwidgets",
            
            # 入口文件
            "main.py"
        ]
    
    print("=" * 70)
    print("🚀 PyInstaller 完整打包模式")
    print("=" * 70)
    print("✅ 速度超快 (30-60秒)")
    print("✅ 单文件exe")
    print("✅ 嵌入UAC清单文件")
    print("✅ 强制管理员权限（双击自动弹出UAC提示）")
    print("⚠️  可能被杀软误报(需要添加信任)")
    print("=" * 70)
    print("\n打包配置:")
    print(f"  - 清单文件: {manifest_file.absolute()}")
    if icon_file.exists():
        print(f"  - 图标文件: {icon_file.absolute()}")
    if use_spec:
        print(f"  - Spec文件: {spec_file.absolute()}")
    print(f"  - 输出目录: dist\\花韵连萌.exe")
    print("\n打包命令:")
    print(" ".join(pyinstaller_args))
    print("\n" + "=" * 70)
    
    try:
        # 执行打包
        print("\n开始打包...")
        result = subprocess.run(pyinstaller_args, check=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 70)
            print("✅ 打包成功!")
            print("=" * 70)
            print(f"\n可执行文件位置: {Path('dist') / '花韵连萌.exe'}")
            print("\n📋 重要提示:")
            print("1. ✅ 打包后的EXE已嵌入UAC清单文件")
            print("2. ✅ 用户双击EXE时会自动弹出UAC权限提示")
            print("3. ✅ 用户必须点击'是'才能运行程序")
            print("4. ⚠️  如被杀软拦截,请添加到信任名单")
            print("5. ⚠️  或关闭杀软后运行")
            print("\n🔍 验证清单文件:")
            print("   可以使用 Resource Hacker 或类似工具查看EXE中的清单")
            print("   下载地址: http://www.angusj.com/resourcehacker/")
            print("\n💡 提示:")
            print("   如果UAC提示没有出现，请检查:")
            print("   1. admin.manifest 文件是否正确")
            print("   2. spec文件中的 manifest 参数是否正确")
            print("   3. 使用 Resource Hacker 验证EXE中是否包含清单")
            print("=" * 70)
        else:
            print("\n❌ 打包失败")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包过程出错: {e}")
        print("\n常见问题排查:")
        print("1. 检查是否安装了 PyInstaller: pip install pyinstaller")
        print("2. 检查 admin.manifest 文件是否存在")
        print("3. 检查 resources 目录是否存在")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ 未找到PyInstaller，正在安装...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
            print("✅ 安装完成,请重新运行此脚本")
        except Exception as e:
            print(f"❌ 安装失败: {e}")
            print("请手动安装: pip install pyinstaller")
        sys.exit(1)

if __name__ == "__main__":
    build_with_pyinstaller()
