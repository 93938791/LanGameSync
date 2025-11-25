"""
Fluent Design 风格启动文件
"""
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QEventLoop, QSize
from PyQt5.QtGui import QIcon
from qfluentwidgets import SplashScreen
from ui.fluent_main_window import FluentMainWindow

# 启用高DPI支持
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("局域网渨戏同步工具")
    
    # 加载启动logo
    logo_path = os.path.join(os.path.dirname(__file__), 'resources', 'icons', 'hysh.png')
    logo_icon = QIcon(logo_path) if os.path.exists(logo_path) else QIcon()
    
    # 创建主窗口
    window = FluentMainWindow()
    
    # 1. 创建启动页面（传入logo和父窗口）
    splash = SplashScreen(logo_icon, window)
    splash.setIconSize(QSize(400, 400))  # 设置图标大小为400x400
    
    # 2. 先显示主窗口（但被启动页面遮挡）
    window.show()
    
    # 3. 显示启动页面，并模拟加载过程
    def create_sub_interface():
        """模拟创建子界面的过程"""
        loop = QEventLoop(window)
        QTimer.singleShot(2500, loop.quit)  # 显示2.5秒
        loop.exec()
    
    create_sub_interface()
    
    # 4. 隐藏启动页面
    splash.finish()
    
    sys.exit(app.exec_())
