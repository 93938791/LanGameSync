"""
主程序入口 - Fluent Design 风格
"""
import sys
import os
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
