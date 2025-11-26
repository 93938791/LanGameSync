"""  
主程序入口 - Fluent Design 风格
"""
import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QEventLoop, QSize, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QIcon
from qfluentwidgets import SplashScreen
from config import Config
from ui.fluent_main_window import FluentMainWindow
from utils.logger import logger

# 启用高DPI支持
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """请求管理员权限重新启动程序"""
    try:
        if sys.platform == 'win32':
            # 获取当前脚本路径
            script = os.path.abspath(sys.argv[0])
            
            # 如果是 .py 文件，使用 pythonw.exe（无窗口）
            if script.endswith('.py'):
                python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_exe = sys.executable
            else:
                python_exe = sys.executable
            
            params = ' '.join([script] + sys.argv[1:])
            
            # 使用 ShellExecute 以管理员权限运行
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas",  # 以管理员身份运行
                python_exe,  # pythonw.exe 或 python.exe
                params,  # 脚本和参数
                None,
                0  # SW_HIDE - 隐藏窗口
            )
            
            if ret > 32:  # 成功
                logger.info("已请求管理员权限，当前进程退出")
                sys.exit(0)
            else:
                logger.error(f"请求管理员权限失败，错误代码: {ret}")
                return False
        return True
    except Exception as e:
        logger.error(f"请求管理员权限时出错: {e}")
        return False

def main():
    """主函数"""
    try:
        # 初始化配置目录
        Config.init_dirs()
        
        logger.info(f"=== {Config.APP_NAME} v{Config.APP_VERSION} 启动 ===")
        
        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName(Config.APP_NAME)
        
        # 加载启动logo
        logo_path = os.path.join(os.path.dirname(__file__), 'resources', 'icons', 'hysh.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(__file__), 'resources', 'logo.png')
        logo_icon = QIcon(logo_path) if os.path.exists(logo_path) else QIcon()
        
        # 创建主窗口（但先不显示）
        window = FluentMainWindow()
        
        # 创建启动页面
        splash = SplashScreen(logo_icon, window)
        splash.setIconSize(QSize(400, 400))
        
        # 设置启动页面窗口标志（隐藏控制按钮）
        splash.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        
        # 设置启动页面固定尺寸（与主窗口保持一致）
        # 主窗口尺寸在 FluentMainWindow.init_window() 中设置为 1120x700
        splash_width = 1120
        splash_height = 700
        splash.setFixedSize(splash_width, splash_height)
        
        # 移动启动页面到屏幕中心（使用与主窗口完全相同的计算方式）
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        splash.move(w // 2 - splash_width // 2, h // 2 - splash_height // 2)
        
        # 显示启动页面（在主窗口显示之前）
        splash.show()
        
        # 模拟加载过程
        def create_sub_interface():
            loop = QEventLoop(window)
            QTimer.singleShot(2500, loop.quit)  # 显示5秒
            loop.exec()
        
        create_sub_interface()
        
        # 创建从下到上的退出动画
        def animate_splash_exit():
            """启动页面从下到上退出动画"""
            # 获取当前位置
            start_pos = splash.pos()
            # 目标位置：向下移动窗口高度（从屏幕底部退出）
            end_pos = QPoint(start_pos.x(), desktop.height())
            
            # 创建位置动画
            animation = QPropertyAnimation(splash, b"pos")
            animation.setDuration(600)  # 动画时长600毫秒
            animation.setStartValue(start_pos)
            animation.setEndValue(end_pos)
            animation.setEasingCurve(QEasingCurve.InOutCubic)  # 使用平滑的缓动曲线
            
            # 动画结束后的处理
            def on_animation_finished():
                splash.finish()  # 关闭启动页面
                window.show()    # 显示主窗口
            
            animation.finished.connect(on_animation_finished)
            animation.start()
            
            # 等待动画完成
            loop = QEventLoop()
            animation.finished.connect(loop.quit)
            loop.exec()
        
        # 执行退出动画
        animate_splash_exit()
        
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"应用异常: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
