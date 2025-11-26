"""  
主程序入口 - Fluent Design 风格
"""
import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QEventLoop, QSize
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
        
        # 创建主窗口
        window = FluentMainWindow()
        
        # 创建启动页面
        splash = SplashScreen(logo_icon, window)
        splash.setIconSize(QSize(400, 400))
        
        # 显示主窗口
        window.show()
        
        # 显示启动页面并模拟加载过程
        def create_sub_interface():
            loop = QEventLoop(window)
            QTimer.singleShot(2500, loop.quit)  # 显示2.5秒
            loop.exec()
        
        create_sub_interface()
        
        # 隐藏启动页面
        splash.finish()
        
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"应用异常: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
