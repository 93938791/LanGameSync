"""
GUI主窗口 - 重构精简版
单个文件控制在1000行以内
"""
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QListWidget,
    QListWidgetItem, QStackedWidget, QFileDialog
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from config import Config
from managers.sync_controller import SyncController
from utils.logger import Logger
from utils.config_cache import ConfigCache
from ui.styles import MODERN_STYLE
from ui.components import MessageBox
from ui.components.dialogs import PeerManagerDialog, PeerEditDialog, LogDialog
from ui.minecraft import MinecraftLauncherHandler, MinecraftPathResolver
from ui.threads import ConnectThread, ScanThread

logger = Logger().get_logger("MainWindow")


class MainWindow(QMainWindow):
    """主窗口 - 精简版（<1000行）"""
    
    def __init__(self):
        super().__init__()
        self.controller = SyncController()
        self.connect_thread = None
        self.scan_thread = None
        self.log_dialog = None
        
        # 状态跟踪
        self.last_sync_state = None
        self.last_peer_ips = set()
        self.scan_count = 0
        self.is_connected = False
        
        # 当前页面
        self.current_page = "network"
        
        # 加载配置
        self.config_data = ConfigCache.load()
        
        # 更新 Minecraft 存档路径
        MinecraftPathResolver.update_minecraft_paths(self.config_data)
        
        self.init_ui()
        self.init_services()
        
        # 应用样式
        self.setStyleSheet(MODERN_STYLE)
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"{Config.APP_NAME} v{Config.APP_VERSION}")
        self.setMinimumSize(1000, 750)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建主容器
        main_container = QWidget()
        main_container.setObjectName("mainContainer")
        self.setCentralWidget(main_container)
        
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 自定义标题栏
        title_bar = self.create_title_bar()
        container_layout.addWidget(title_bar)
        
        # 主内容区域（左侧边栏 + 右侧内容）
        main_content = QWidget()
        main_content.setObjectName("mainContent")
        main_content_layout = QHBoxLayout(main_content)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        
        # 左侧边栏
        sidebar = self.create_sidebar()
        main_content_layout.addWidget(sidebar)
        
        # 右侧内容区域（使用 Stacked Widget 切换页面）
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentWidget")
        
        # 网络管理页面
        network_page = self.create_network_page()
        self.content_stack.addWidget(network_page)
        
        # 游戏管理页面
        game_page = self.create_game_page()
        self.content_stack.addWidget(game_page)
        
        main_content_layout.addWidget(self.content_stack)
        container_layout.addWidget(main_content)
        
        # 窗口拖动相关
        self.drag_position = None
    
    def init_services(self):
        """初始化后台服务"""
        logger.info("初始化后台服务...")
        
        # 定时器：同步状态监控
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_sync_state)
        self.monitor_timer.start(3000)
    
    # ==================== UI创建方法 ====================
    
    def create_title_bar(self):
        """创建自定义标题栏"""
        # TODO: 从 main_window_v2.py 迁移
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(50)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(15, 0, 10, 0)
        
        # 标题
        title_label = QLabel(f"{Config.APP_NAME}")
        title_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        layout.addStretch()
        
        # 最小化按钮
        min_btn = QPushButton("−")
        min_btn.setFixedSize(45, 50)
        min_btn.clicked.connect(self.showMinimized)
        min_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ffffff;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                background: #3e3e3e;
            }
        """)
        layout.addWidget(min_btn)
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(45, 50)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ffffff;
                border: none;
                font-size: 28px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e81123;
            }
        """)
        layout.addWidget(close_btn)
        
        return title_bar
    
    def create_sidebar(self):
        """创建左侧边栏"""
        # TODO: 从 main_window_v2.py 迁移
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(70)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(0)
        
        # 网络管理按钮
        self.network_btn = QPushButton("🌐")
        self.network_btn.setFixedSize(70, 70)
        self.network_btn.setToolTip("网络管理")
        self.network_btn.clicked.connect(lambda: self.switch_page("network"))
        layout.addWidget(self.network_btn)
        
        # 游戏管理按钮
        self.game_btn = QPushButton("🎮")
        self.game_btn.setFixedSize(70, 70)
        self.game_btn.setToolTip("游戏管理")
        self.game_btn.clicked.connect(lambda: self.switch_page("game"))
        layout.addWidget(self.game_btn)
        
        # 设置按钮
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(70, 70)
        settings_btn.setToolTip("设置")
        settings_btn.clicked.connect(self.show_log_dialog)
        
        layout.addStretch()
        layout.addWidget(settings_btn)
        
        return sidebar
    
    def create_network_page(self):
        """创建网络管理页面"""
        # TODO: 从 main_window_v2.py 迁移完整功能
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(15)
        
        # 网络管理区域
        network_group = QGroupBox("网络管理")
        network_layout = QVBoxLayout()
        
        # 房间号输入
        room_layout = QHBoxLayout()
        room_layout.addWidget(QLabel("房间号:"))
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("输入房间号")
        room_layout.addWidget(self.room_input)
        network_layout.addLayout(room_layout)
        
        # 密码输入
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(QLabel("密码:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        pwd_layout.addWidget(self.password_input)
        network_layout.addLayout(pwd_layout)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接到网络")
        self.connect_btn.clicked.connect(self.connect_to_network)
        network_layout.addWidget(self.connect_btn)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # 客户端信息
        clients_group = QGroupBox("已连接的客户端")
        clients_layout = QVBoxLayout()
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(2)
        self.clients_table.setHorizontalHeaderLabels(["设备名", "虚拟IP"])
        clients_layout.addWidget(self.clients_table)
        clients_group.setLayout(clients_layout)
        layout.addWidget(clients_group)
        
        # 状态栏
        self.status_label = QLabel("状态: 未连接")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        return page
    
    def create_game_page(self):
        """创建游戏管理页面"""
        # TODO: 从 main_window_v2.py 迁移完整功能
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 15, 20, 20)
        
        # 游戏列表
        self.game_list = QListWidget()
        layout.addWidget(self.game_list)
        
        # 加载游戏列表
        self.load_game_list()
        
        return page
    
    # ==================== 业务逻辑方法 ====================
    
    def switch_page(self, page_name):
        """切换页面"""
        self.current_page = page_name
        if page_name == "network":
            self.content_stack.setCurrentIndex(0)
        elif page_name == "game":
            self.content_stack.setCurrentIndex(1)
            self.load_game_list()
    
    def connect_to_network(self):
        """连接到网络"""
        # TODO: 从 main_window_v2.py 迁移完整功能
        room_name = self.room_input.text().strip()
        password = self.password_input.text().strip()
        
        if not room_name or not password:
            MessageBox.show_warning(self, "提示", "请输入房间号和密码")
            return
        
        # 保存配置
        self.config_data["network"] = {
            "room_name": room_name,
            "password": password
        }
        ConfigCache.save(self.config_data)
        
        # 启动连接线程
        self.connect_thread = ConnectThread(self.controller, room_name, password)
        self.connect_thread.connected.connect(self.on_connected)
        self.connect_thread.start()
        
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("正在连接...")
    
    def on_connected(self, success, message):
        """连接完成回调"""
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("连接到网络")
        
        if success:
            self.is_connected = True
            self.status_label.setText(f"状态: 已连接 | 虚拟IP: {message}")
            MessageBox.show_info(self, "成功", "网络连接成功！")
        else:
            self.status_label.setText("状态: 连接失败")
            MessageBox.show_error(self, "错误", f"连接失败: {message}")
    
    def load_game_list(self):
        """加载游戏列表"""
        # TODO: 从 main_window_v2.py 迁移完整功能
        self.game_list.clear()
        game_list = self.config_data.get("game_list", [])
        
        for game in game_list:
            item = QListWidgetItem(game.get("name", "未命名"))
            self.game_list.addItem(item)
    
    def show_log_dialog(self):
        """显示日志对话框"""
        if not self.log_dialog:
            self.log_dialog = LogDialog(self)
        self.log_dialog.show()
    
    def monitor_sync_state(self):
        """监控同步状态"""
        if not self.is_connected:
            return
        
        # TODO: 从 main_window_v2.py 迁移监控逻辑
        pass
    
    # ==================== 窗口事件 ====================
    
    def mousePressEvent(self, event):
        """鼠标按下（拖动窗口）"""
        if event.button() == Qt.LeftButton:
            if hasattr(self, 'title_bar') and self.title_bar.geometry().contains(event.pos()):
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if hasattr(self, 'drag_position'):
            del self.drag_position
    
    def closeEvent(self, event):
        """关闭窗口"""
        logger.info("正在关闭应用...")
        
        if self.connect_thread and self.connect_thread.isRunning():
            self.connect_thread.quit()
            self.connect_thread.wait()
        
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.quit()
            self.scan_thread.wait()
        
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
