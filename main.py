"""  
主程序入口 - Fluent Design 风格
"""
import sys
import os
import ctypes
import traceback
from datetime import datetime

# 在导入其他模块前先设置异常处理
def early_excepthook(exc_type, exc_value, exc_traceback):
    """早期异常处理（在导入阶段）"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print("=" * 60)
    print("程序启动失败！")
    print("=" * 60)
    print(error_msg)
    print("=" * 60)
    
    # 尝试写入日志文件
    try:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"程序启动失败 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n")
            f.write(error_msg)
            f.write(f"{'='*50}\n")
        print(f"\n错误信息已保存到: {log_file}")
    except Exception as e:
        print(f"无法写入日志文件: {e}")
    
    input("\n按回车键退出...")
    sys.exit(1)

sys.excepthook = early_excepthook

# 检查是否有 -debug 参数，决定是否显示调试信息
DEBUG_MODE = '-debug' in sys.argv or '--debug' in sys.argv

# 现在导入其他模块，添加调试信息
if DEBUG_MODE:
    print("开始导入模块...")
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt, QTimer, QEventLoop, QSize, QPropertyAnimation, QEasingCurve, QPoint
    from PyQt5.QtGui import QIcon
    if DEBUG_MODE:
        print("✓ PyQt5 导入成功")
except Exception as e:
    if DEBUG_MODE:
        print(f"✗ PyQt5 导入失败: {e}")
    traceback.print_exc()
    raise

try:
    from qfluentwidgets import SplashScreen
    if DEBUG_MODE:
        print("✓ qfluentwidgets 导入成功")
except Exception as e:
    if DEBUG_MODE:
        print(f"✗ qfluentwidgets 导入失败: {e}")
    traceback.print_exc()
    raise

try:
    from config import Config
    if DEBUG_MODE:
        print("✓ config 导入成功")
except Exception as e:
    if DEBUG_MODE:
        print(f"✗ config 导入失败: {e}")
    traceback.print_exc()
    raise

try:
    from ui.fluent_main_window import FluentMainWindow
    if DEBUG_MODE:
        print("✓ FluentMainWindow 导入成功")
except Exception as e:
    if DEBUG_MODE:
        print(f"✗ FluentMainWindow 导入失败: {e}")
    traceback.print_exc()
    raise

try:
    from utils.logger import logger
    if DEBUG_MODE:
        print("✓ logger 导入成功")
except Exception as e:
    if DEBUG_MODE:
        print(f"✗ logger 导入失败: {e}")
    traceback.print_exc()
    raise

if DEBUG_MODE:
    print("所有模块导入完成！\n")

def show_console_window():
    """显示控制台窗口（用于调试）"""
    if sys.platform == 'win32':
        try:
            # 分配一个新的控制台
            kernel32 = ctypes.windll.kernel32
            kernel32.AllocConsole()
            # 重定向标准输出到控制台
            import os
            sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
            sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
            print("=" * 60)
            print("调试模式已启用 - 控制台窗口已显示")
            print("=" * 60)
        except Exception as e:
            # 如果显示失败，继续运行（不影响程序功能）
            pass

def hide_console_window():
    """隐藏控制台窗口（仅Windows GUI程序）"""
    if sys.platform == 'win32':
        try:
            # 获取控制台窗口句柄
            kernel32 = ctypes.windll.kernel32
            console_window = kernel32.GetConsoleWindow()
            if console_window:
                # 隐藏控制台窗口
                user32 = ctypes.windll.user32
                user32.ShowWindow(console_window, 0)  # SW_HIDE = 0
        except Exception:
            # 如果隐藏失败，继续运行（不影响程序功能）
            pass

# 检查是否有 -debug 参数
if '-debug' in sys.argv or '--debug' in sys.argv:
    # 如果有 -debug 参数，显示控制台窗口
    show_console_window()
else:
    # 正常启动时，如果已经有控制台窗口（打包时设置了console=True），则隐藏它
    # 注意：如果打包时设置了console=False，则不会有控制台窗口，无需隐藏
    pass

def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员权限重新运行程序"""
    if is_admin():
        return True
    
    try:
        if sys.platform == 'win32':
            # 获取当前脚本的完整路径
            script = sys.executable
            if script.endswith('.exe'):
                # 如果是打包后的exe，直接使用
                python_exe = script
            else:
                # 如果是.py文件，使用python.exe
                python_exe = sys.executable
            
            # 构建参数
            if script.endswith('.py'):
                # Python脚本：python.exe script.py [args...]
                params = ' '.join([f'"{script}"'] + [f'"{arg}"' if ' ' in arg else arg for arg in sys.argv[1:]])
            else:
                # 可执行文件：直接运行，参数已经在sys.argv中
                params = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in sys.argv[1:]])
            
            # 使用 ShellExecute 以管理员权限运行
            # SW_SHOWNORMAL = 1 - 正常显示窗口
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas",  # 以管理员身份运行
                python_exe,  # python.exe 或 .exe文件
                params,  # 脚本和参数
                None,
                1  # SW_SHOWNORMAL - 正常显示窗口
            )
            
            if ret > 32:  # 成功
                logger.info("已请求管理员权限，当前进程退出")
                sys.exit(0)
            else:
                error_codes = {
                    0: "内存不足",
                    2: "文件未找到",
                    3: "路径未找到",
                    5: "拒绝访问（用户取消了UAC提示）",
                    8: "内存不足",
                    11: "无效的可执行文件",
                    26: "共享冲突",
                    27: "关联不完整",
                    28: "DDE事务超时",
                    29: "DDE事务失败",
                    30: "DDE忙碌",
                    31: "没有文件关联",
                    32: "动态数据交换（DDE）失败"
                }
                error_msg = error_codes.get(ret, f"未知错误")
                logger.error(f"请求管理员权限失败，错误代码: {ret} ({error_msg})")
                return False
        return True
    except Exception as e:
        logger.error(f"请求管理员权限时出错: {e}")
        return False

def initialize_app():
    """初始化应用（在启动页面显示期间执行）
    
    权限检查说明：
    1. 如果程序已嵌入manifest（requireAdministrator），Windows会在启动时自动弹出UAC
    2. 如果已经是管理员权限，直接通过，不需要任何提示
    3. 只有在没有管理员权限时（通常是开发环境运行.py文件），才需要请求提权
    
    返回: (success, error_message)
    """
    try:
        print("正在初始化应用...")
        # 初始化配置目录
        Config.init_dirs()
        logger.info(f"=== {Config.APP_NAME} v{Config.APP_VERSION} 启动 ===")
        print("✓ 配置目录初始化成功")
        
        # 检查管理员权限（启动网络需要管理员权限）
        if sys.platform == 'win32':
            if is_admin():
                # 已经是管理员权限，直接通过，不需要任何提示
                # 这种情况发生在：
                # 1. 打包后的EXE，用户同意了UAC提示，程序以管理员权限运行
                # 2. 用户手动以管理员身份运行程序
                logger.info("✅ 当前以管理员权限运行，权限检查通过")
                print("✓ 管理员权限检查通过")
                return True, None
            else:
                # 没有管理员权限，需要请求提权
                # 这种情况通常发生在：
                # 1. 开发环境运行.py文件（没有manifest）
                # 2. 打包后的EXE但用户拒绝了UAC提示（理论上不会运行到这里）
                logger.warning("当前未以管理员权限运行，启动网络需要管理员权限")
                print("⚠ 未获取管理员权限")
                return False, "未获取管理员权限"
        
        # 非Windows平台，不需要管理员权限
        return True, None
        
    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
        print(f"✗ 初始化失败: {e}")
        traceback.print_exc()
        return False, str(e)

def main():
    """主函数"""
    try:
        print("=" * 60)
        print("程序启动中...")
        print("=" * 60)
        
        # 添加运行时异常处理
        def runtime_excepthook(exc_type, exc_value, exc_traceback):
            """运行时异常处理"""
            error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            print("=" * 60)
            print("运行时错误！")
            print("=" * 60)
            print(error_msg)
            print("=" * 60)
            try:
                logger.error(f"未捕获的异常:\n{error_msg}")
            except:
                pass
            # 尝试写入日志文件
            try:
                log_file = Config.LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*50}\n")
                    f.write(f"运行时异常 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n")
                    f.write(error_msg)
                    f.write(f"{'='*50}\n")
            except:
                pass
            # 显示错误对话框
            try:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(None, "程序错误", f"程序发生错误:\n\n{str(exc_value)}\n\n详细信息已写入日志文件")
            except:
                pass
            input("\n按回车键退出...")
            sys.exit(1)
        
        sys.excepthook = runtime_excepthook
        
        print("正在创建 QApplication...")
        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName(Config.APP_NAME)
        print("✓ QApplication 创建成功")
        
        # 设置应用图标（用于任务栏显示）
        icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'logo.ico')
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'logo.png')
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            print(f"✓ 应用图标设置成功: {icon_path}")
        else:
            print(f"⚠ 图标文件不存在: {icon_path}")
        
        # 加载启动logo
        logo_path = os.path.join(os.path.dirname(__file__), 'resources', 'icons', 'hysh.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(__file__), 'resources', 'logo.png')
        logo_icon = QIcon(logo_path) if os.path.exists(logo_path) else QIcon()
        if os.path.exists(logo_path):
            print(f"✓ 启动logo加载成功: {logo_path}")
        else:
            print(f"⚠ 启动logo不存在: {logo_path}")
        
        # 先创建启动页面（不依赖主窗口）
        print("正在创建启动页面...")
        splash = SplashScreen(logo_icon, None)  # 先不传入主窗口
        splash.setIconSize(QSize(400, 400))
        
        # 设置启动页面窗口标志（隐藏控制按钮，保持在最上层）
        splash.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 设置启动页面固定尺寸（与主窗口保持一致）
        splash_width = 1200
        splash_height = 700
        splash.setFixedSize(splash_width, splash_height)
        
        # 移动启动页面到屏幕中心
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        splash.move(w // 2 - splash_width // 2, h // 2 - splash_height // 2)
        
        # 显示启动页面（立即显示，让用户看到美观的启动画面）
        splash.show()
        splash.raise_()  # 确保在最上层
        splash.activateWindow()  # 激活窗口
        splash.repaint()  # 强制重绘
        print("✓ 启动页面显示成功")
        
        # 确保启动页面完全显示（处理所有待处理的事件，让UI完全渲染）
        import time
        for _ in range(20):
            app.processEvents()
        
        # 给一点时间让启动页面完全渲染（确保用户能看到）
        time.sleep(0.15)  # 150ms，确保启动页面完全显示
        for _ in range(10):
            app.processEvents()
        
        # 确保启动页面在创建主窗口前完全显示
        app.processEvents()
        
        # 现在才创建主窗口（在启动页面显示之后）
        # 主窗口创建时可能会触发一些初始化，但启动页面已经显示了
        if DEBUG_MODE:
            print("正在创建主窗口...")
        window = FluentMainWindow()
        if DEBUG_MODE:
            print("✓ 主窗口创建成功")
        window.hide()  # 确保主窗口不显示，直到初始化完成
        
        # 将主窗口关联到启动页面（用于淡出动画）
        splash.setParent(window)
        
        # 再次确保启动页面在最上层
        splash.raise_()
        splash.activateWindow()
        app.processEvents()
        
        # 在后台进行初始化（使用QTimer异步执行，避免阻塞UI）
        # 延迟一点时间，确保启动页面完全显示后再开始检查
        init_result = {'success': None, 'error': None}
        
        def do_initialization():
            """执行初始化（在启动页面显示后进行）"""
            init_result['success'], init_result['error'] = initialize_app()
        
        # 使用QTimer延迟执行初始化，确保启动页面先完全显示
        # 延迟300ms，让用户看到美观的启动画面
        QTimer.singleShot(300, do_initialization)
        
        # 等待初始化完成（使用事件循环，最多等待3秒）
        # 在等待期间，持续处理事件，确保启动页面保持显示
        start_time = time.time()
        timeout = 3.0
        
        while time.time() - start_time < timeout:
            app.processEvents()  # 处理事件，保持UI响应
            # 确保启动页面始终在最上层并可见
            if not splash.isVisible():
                splash.show()  # 如果被隐藏了，重新显示
            splash.raise_()  # 始终保持在最上层
            if init_result['success'] is not None:  # 初始化完成（无论成功或失败）
                break
            time.sleep(0.01)  # 短暂休眠，避免CPU占用过高
        
        # 如果超时仍未完成，使用默认值
        if init_result['success'] is None:
            logger.warning("初始化超时，使用默认值")
            init_result['success'] = False
            init_result['error'] = "初始化超时"
        
        # 检查初始化结果
        if not init_result['success']:
            # 初始化失败，关闭启动页面
            splash.finish()
            
            # 显示错误提示
            from PyQt5.QtWidgets import QMessageBox
            if init_result['error'] == "未获取管理员权限":
                # 如果是权限问题，提示用户
                reply = QMessageBox.question(
                    None,
                    "需要管理员权限",
                    "启动网络功能需要管理员权限。\n\n是否以管理员身份重新运行？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    # 尝试以管理员权限重新运行
                    if run_as_admin():
                        sys.exit(0)
                    else:
                        QMessageBox.warning(None, "提示", "无法以管理员权限运行。\n程序将以受限模式运行。")
                else:
                    QMessageBox.information(None, "提示", "程序将以受限模式运行。\n某些功能可能无法使用。")
            else:
                # 其他错误
                QMessageBox.critical(None, "初始化失败", f"程序初始化失败:\n\n{init_result['error']}\n\n请查看日志文件获取详细信息。")
            
            # 即使初始化失败，也显示主窗口（受限模式）
            window.show()
            window.raise_()
            window.activateWindow()
            sys.exit(app.exec_())
        
        # 初始化成功，显示主窗口
        print("✓ 初始化成功，显示主窗口")
        window.show()
        window.raise_()
        window.activateWindow()
        
        # 启动页面淡出动画 + 主窗口淡入动画
        # 创建淡出动画（从1到0）
        splash_animation = QPropertyAnimation(splash, b"windowOpacity")
        splash_animation.setDuration(600)  # 600毫秒
        splash_animation.setStartValue(1.0)
        splash_animation.setEndValue(0.0)
        splash_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # 主窗口淡入动画（从0到1）
        window_animation = QPropertyAnimation(window, b"windowOpacity")
        window_animation.setDuration(600)  # 与启动页面同步
        window_animation.setStartValue(0.0)
        window_animation.setEndValue(1.0)
        window_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # 动画结束后的处理
        def on_animation_finished():
            splash.finish()  # 关闭启动页面
            window.setWindowOpacity(1.0)  # 确保主窗口完全不透明
        
        splash_animation.finished.connect(on_animation_finished)
        
        # 同时启动两个动画
        splash_animation.start()
        window_animation.start()
        
        print("=" * 60)
        print("程序启动完成！")
        print("=" * 60)
        
        # 运行应用
        sys.exit(app.exec_())
        
    except Exception as e:
        error_msg = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        print("=" * 60)
        print("主函数异常！")
        print("=" * 60)
        print(error_msg)
        print("=" * 60)
        try:
            logger.error(f"主函数异常: {e}", exc_info=True)
        except:
            pass
        try:
            log_file = Config.LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"主函数异常 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n")
                f.write(error_msg)
                f.write(f"{'='*50}\n")
        except:
            pass
        input("\n按回车键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main()
