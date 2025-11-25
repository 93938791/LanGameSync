"""
GUI主窗口 - 重构精简版
单个文件控制在1000行以内
"""
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QListWidget,
    QListWidgetItem, QStackedWidget, QFileDialog, QDialog, QScrollArea
)
from PyQt5.QtCore import QTimer, Qt, QUrl, QPropertyAnimation, QEasingCurve, QPoint, QMetaObject, Q_ARG, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
import os
from config import Config
from managers.sync_controller import SyncController
from utils.logger import Logger
from utils.config_cache import ConfigCache
from ui.styles import MODERN_STYLE
from ui.components import MessageBox
from ui.components.dialogs import PeerManagerDialog
# TODO: PeerEditDialog, LogDialog 待实现
from ui.minecraft import MinecraftLauncherHandler, MinecraftPathResolver
from ui.threads import ConnectThread, ScanThread

logger = Logger().get_logger("MainWindow")


class MainWindow(QMainWindow):
    """主窗口 - 精简版（<1000行）"""
    
    # 定义信号（用于线程安全的UI更新）
    update_button_signal = pyqtSignal(bool, str)  # (enabled, text)
    
    def __init__(self):
        super().__init__()
        self.controller = SyncController()
        self.connect_thread = None
        self.scan_thread = None
        self.log_dialog = None
        
        # 状态跟踪
        self.last_sync_state = None
        self.last_peer_ips = set()
        self.last_peer_count = 0  # 记录上次的设备数量
        self.scan_count = 0
        self.is_connected = False
        
        # MQTT和游戏启动器
        self.mqtt_manager = None
        self.game_launcher = None
        self.server_info = None  # 当前服务器信息
        
        # 当前页面
        self.current_page = "network"
        
        # 加载配置
        self.config_data = ConfigCache.load()
        
        # 更新 Minecraft 存档路径
        MinecraftPathResolver.update_minecraft_paths(self.config_data)
        
        self.init_ui()
        self.init_services()
        
        # 连接信号
        self.update_button_signal.connect(self._update_button_slot)
        
        # 应用样式
        self.setStyleSheet(MODERN_STYLE)
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"{Config.APP_NAME} v{Config.APP_VERSION}")
        self.setFixedSize(1200, 800)  # 固定窗口大小，不可调整
        
        # 设置窗口图标（用于任务栏）
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'logo.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
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
        
        # 设置页面
        settings_page = self.create_settings_page()
        self.content_stack.addWidget(settings_page)
        
        main_content_layout.addWidget(self.content_stack)
        container_layout.addWidget(main_content)
        
        # 窗口拖动相关
        self.drag_position = None
    
    def init_services(self):
        """初始化后台服务"""
        logger.info("初始化后台服务...")
        
        # 删除定时器：改用UDP广播机制通知设备变化
        # self.monitor_timer = QTimer()
        # self.monitor_timer.timeout.connect(self.monitor_sync_state)
        # self.monitor_timer.start(3000)
    
    # ==================== UI创建方法 ====================
    
    def create_title_bar(self):
        """创建自定义标题栏"""
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(40)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(15, 0, 10, 0)
        
        # Logo图标
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'logo.png')
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setFixedSize(28, 28)
        layout.addWidget(logo_label)
        
        # 标题
        self.title_label = QLabel(f"{Config.APP_NAME}")
        self.title_label.setStyleSheet("color: #000000; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # 当前页面名称
        self.page_name_label = QLabel(" - 联机设置")
        self.page_name_label.setStyleSheet("color: #666666; font-size: 13px; font-weight: normal;")
        layout.addWidget(self.page_name_label)
        
        # 添加固定空间而不是弹性空间
        spacer = QWidget()
        spacer.setFixedWidth(800)  # 固定宽度的空白区域
        layout.addWidget(spacer)
        
        # 获取图标路径
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icons')
        
        # 最小化按钮
        min_btn = QPushButton()
        min_btn.setFixedSize(40, 40)
        min_btn.clicked.connect(self.showMinimized)
        minimize_icon = os.path.join(icon_dir, 'minimize.png')
        if os.path.exists(minimize_icon):
            min_btn.setIcon(QIcon(minimize_icon))
            min_btn.setIconSize(min_btn.size() * 0.5)
        else:
            min_btn.setText("−")
        min_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #000000;
                border: none;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        layout.addWidget(min_btn)
        
        # 关闭按钮
        close_btn = QPushButton()
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.close)
        close_icon = os.path.join(icon_dir, 'close.png')
        if os.path.exists(close_icon):
            close_btn.setIcon(QIcon(close_icon))
            close_btn.setIconSize(close_btn.size() * 0.5)
        else:
            close_btn.setText("×")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #000000;
                border: none;
                font-size: 22px;
                font-weight: normal;
            }
            QPushButton:hover {
                background: #e81123;
                color: #ffffff;
            }
        """)
        layout.addWidget(close_btn)
        
        self.title_bar = title_bar
        return title_bar
    
    def create_sidebar(self):
        """创建左侧边栏"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(60)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(0)
        
        # 获取图标路径
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icons')
        
        # 网络管理按钮
        self.network_btn = QPushButton()
        self.network_btn.setObjectName("sidebarBtn")
        self.network_btn.setFixedSize(60, 60)
        self.network_btn.setToolTip("联机设置")
        self.network_btn.clicked.connect(lambda: self.switch_page("network"))
        network_icon = os.path.join(icon_dir, 'network.png')
        if os.path.exists(network_icon):
            self.network_btn.setIcon(QIcon(network_icon))
            self.network_btn.setIconSize(self.network_btn.size() * 0.5)
        else:
            self.network_btn.setText("🌐")
        self.network_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-left: 3px solid #06ae56;
                font-size: 24px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        layout.addWidget(self.network_btn)
        
        # 游戏管理按钮
        self.game_btn = QPushButton()
        self.game_btn.setObjectName("sidebarBtnInactive")
        self.game_btn.setFixedSize(60, 60)
        self.game_btn.setToolTip("游戏管理")
        self.game_btn.clicked.connect(lambda: self.switch_page("game"))
        game_icon = os.path.join(icon_dir, 'game.png')
        if os.path.exists(game_icon):
            self.game_btn.setIcon(QIcon(game_icon))
            self.game_btn.setIconSize(self.game_btn.size() * 0.5)
        else:
            self.game_btn.setText("🎮")
        self.game_btn.setStyleSheet("""
            QPushButton {
                background: #ededed;
                color: #666666;
                border: none;
                font-size: 24px;
            }
            QPushButton:hover {
                background: #07c160;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.game_btn)
        
        # 设置按钮
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("sidebarBtnInactive")
        self.settings_btn.setFixedSize(60, 60)
        self.settings_btn.setToolTip("设置")
        self.settings_btn.clicked.connect(lambda: self.switch_page("settings"))
        settings_icon = os.path.join(icon_dir, 'settings.png')
        if os.path.exists(settings_icon):
            self.settings_btn.setIcon(QIcon(settings_icon))
            self.settings_btn.setIconSize(self.settings_btn.size() * 0.5)
        else:
            self.settings_btn.setText("⚙️")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: #ededed;
                color: #666666;
                border: none;
                font-size: 24px;
            }
            QPushButton:hover {
                background: #07c160;
                color: #ffffff;
            }
        """)
        
        layout.addStretch()
        layout.addWidget(self.settings_btn)
        
        return sidebar
    
    def create_network_page(self):
        """创建网络管理页面"""
        # 不使用滚动区域，直接使用固定布局
        page = QWidget()
        page.setObjectName("networkPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)  # 减小上下边距
        layout.setSpacing(0)  # 移除所有间距
        
        # 节点设置区域
        node_group = QGroupBox()
        node_group.setObjectName("networkGroup")
        node_group.setStyleSheet("""
            QGroupBox {
                border: none;
                background: transparent;
            }
        """)
        node_layout = QVBoxLayout()
        node_layout.setSpacing(10)
        node_layout.setContentsMargins(15, 15, 15, 15)  # 减小内边距
        
        # 自定义标题
        title_layout = QHBoxLayout()
        title_icon = QLabel()
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icons')
        node_icon_path = os.path.join(icon_dir, 'node.png')
        if os.path.exists(node_icon_path):
            pixmap = QPixmap(node_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            title_icon.setPixmap(pixmap)
        else:
            title_icon.setText("🌐")
            title_icon.setStyleSheet("font-size: 20px;")
        title_layout.addWidget(title_icon)
        
        title_label = QLabel("节点设置")
        title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #2c2c2c; margin-left: 5px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        node_layout.addLayout(title_layout)
        
        # 节点选择行
        node_select_layout = QHBoxLayout()
        node_select_layout.setSpacing(12)
        
        node_label = QLabel("节点选择")
        node_label.setStyleSheet("font-size: 13px; color: #4a4a4a; font-weight: 500;")
        node_label.setMinimumWidth(65)
        node_select_layout.addWidget(node_label)
        
        from PyQt5.QtWidgets import QComboBox
        self.node_combo = QComboBox()
        
        # 只添加官方节点
        self.node_combo.addItem("官方节点（推荐）")
        
        # 设置为只读，不可更改
        self.node_combo.setEnabled(False)
        self.node_combo.setStyleSheet("""
            QComboBox {
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                min-height: 18px;
            }
            QComboBox:hover {
                background: #f5f5f5;
                border: 1px solid #07c160;
            }
            QComboBox:focus {
                border: 1px solid #07c160;
                background: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #666666;
                margin-right: 10px;
            }
        """)
        node_select_layout.addWidget(self.node_combo, 1)
        
        # 配置节点按钮
        config_node_btn = QPushButton("⚙️ 配置节点")
        config_node_btn.clicked.connect(self.show_peer_manager)
        config_node_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                color: #4a4a4a;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                min-width: 90px;
            }
            QPushButton:hover {
                background: #f5f5f5;
                border: 1px solid #07c160;
                color: #07c160;
            }
            QPushButton:pressed {
                background: #eeeeee;
            }
        """)
        node_select_layout.addWidget(config_node_btn)
        node_layout.addLayout(node_select_layout)
        
        node_group.setLayout(node_layout)
        layout.addWidget(node_group)
        
        # 网络管理区域
        network_group = QGroupBox()
        network_group.setObjectName("networkGroup")
        network_group.setStyleSheet("""
            QGroupBox {
                border: none;
                background: transparent;
            }
        """)
        network_layout = QVBoxLayout()
        network_layout.setSpacing(10)
        network_layout.setContentsMargins(15, 15, 15, 15)  # 减小内边距
        
        # 自定义标题
        net_title_layout = QHBoxLayout()
        net_title_icon = QLabel()
        network_manage_icon_path = os.path.join(icon_dir, 'network_manage.png')
        if os.path.exists(network_manage_icon_path):
            pixmap = QPixmap(network_manage_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            net_title_icon.setPixmap(pixmap)
        else:
            net_title_icon.setText("🔗")
            net_title_icon.setStyleSheet("font-size: 20px;")
        net_title_layout.addWidget(net_title_icon)
        
        net_title_label = QLabel("网络管理")
        net_title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #2c2c2c; margin-left: 5px;")
        net_title_layout.addWidget(net_title_label)
        net_title_layout.addStretch()
        network_layout.addLayout(net_title_layout)
        
        # 房间号输入
        room_layout = QHBoxLayout()
        room_layout.setSpacing(12)
        room_label = QLabel("房间号")
        room_label.setStyleSheet("font-size: 13px; color: #4a4a4a; font-weight: 500;")
        room_label.setMinimumWidth(65)
        room_layout.addWidget(room_label)
        
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("输入房间号...")
        self.room_input.setMaximumWidth(600)  # 限制最大宽度
        self.room_input.setStyleSheet("""
            QLineEdit {
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                color: #2c2c2c;
                min-height: 18px;
            }
            QLineEdit:focus {
                border: 1px solid #07c160;
                background: #ffffff;
            }
            QLineEdit:hover {
                background: #f5f5f5;
            }
        """)
        # 加载保存的房间号
        network_config = self.config_data.get("network", {})
        if network_config.get("room_name"):
            self.room_input.setText(network_config["room_name"])
        room_layout.addWidget(self.room_input, 1)
        room_layout.addStretch()  # 添加弹性空间
        network_layout.addLayout(room_layout)
        
        # 密码输入
        pwd_layout = QHBoxLayout()
        pwd_layout.setSpacing(12)
        pwd_label = QLabel("密码")
        pwd_label.setStyleSheet("font-size: 13px; color: #4a4a4a; font-weight: 500;")
        pwd_label.setMinimumWidth(65)
        pwd_layout.addWidget(pwd_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("输入密码...")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMaximumWidth(600)  # 限制最大宽度
        self.password_input.setStyleSheet("""
            QLineEdit {
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                color: #2c2c2c;
                min-height: 18px;
            }
            QLineEdit:focus {
                border: 1px solid #07c160;
                background: #ffffff;
            }
            QLineEdit:hover {
                background: #f5f5f5;
            }
        """)
        # 加载保存的密码
        if network_config.get("password"):
            self.password_input.setText(network_config["password"])
        pwd_layout.addWidget(self.password_input, 1)
        pwd_layout.addStretch()  # 添加弹性空间
        network_layout.addLayout(pwd_layout)
        
        # 添加间距
        network_layout.addSpacing(5)
        
        # 连接按钮
        self.connect_btn = QPushButton("🚀 连接到网络")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self.connect_to_network)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #09d168, stop:1 #07c160);
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #0ae174, stop:1 #09d168);
            }
            QPushButton:pressed {
                background: #06ae56;
            }
            QPushButton:disabled {
                background: #b8e6cc;
                color: #ffffff;
            }
        """)
        network_layout.addWidget(self.connect_btn)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # 客户端信息
        clients_group = QGroupBox()
        clients_group.setObjectName("clientsGroup")
        clients_group.setStyleSheet("""
            QGroupBox {
                border: none;
                background: transparent;
            }
        """)
        clients_layout = QVBoxLayout()
        clients_layout.setContentsMargins(15, 15, 15, 15)  # 减小内边距
        clients_layout.setSpacing(10)
        
        # 自定义标题
        clients_title_layout = QHBoxLayout()
        clients_title_icon = QLabel()
        devices_icon_path = os.path.join(icon_dir, 'devices.png')
        if os.path.exists(devices_icon_path):
            pixmap = QPixmap(devices_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            clients_title_icon.setPixmap(pixmap)
        else:
            clients_title_icon.setText("💻")
            clients_title_icon.setStyleSheet("font-size: 20px;")
        clients_title_layout.addWidget(clients_title_icon)
        
        clients_title_label = QLabel("已连接的设备")
        clients_title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #2c2c2c; margin-left: 5px; border: none;")
        clients_title_layout.addWidget(clients_title_label)
        
        # 设备计数标签
        self.device_count_label = QLabel("(0)")
        self.device_count_label.setStyleSheet("font-size: 13px; color: #888888; margin-left: 5px; border: none;")
        clients_title_layout.addWidget(self.device_count_label)
        
        clients_title_layout.addStretch()
        
        # 查看全部按钮
        self.view_all_btn = QPushButton("查看全部")
        self.view_all_btn.setCursor(Qt.PointingHandCursor)
        self.view_all_btn.clicked.connect(self.show_all_devices)
        self.view_all_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #07c160;
                border: none;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                color: #06ae56;
                text-decoration: underline;
            }
        """)
        self.view_all_btn.hide()  # 初始隐藏
        clients_title_layout.addWidget(self.view_all_btn)
        
        clients_layout.addLayout(clients_title_layout)
        
        # 设备列表容器
        devices_container = QWidget()
        devices_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        devices_container_layout = QVBoxLayout(devices_container)
        devices_container_layout.setContentsMargins(0, 0, 0, 0)
        devices_container_layout.setSpacing(0)
        
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(3)
        self.clients_table.setHorizontalHeaderLabels(["设备名", "IP地址", "延迟"])
        self.clients_table.horizontalHeader().setStretchLastSection(True)
        self.clients_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.clients_table.setColumnWidth(1, 150)
        self.clients_table.setColumnWidth(2, 80)
        self.clients_table.verticalHeader().setVisible(False)
        self.clients_table.setAlternatingRowColors(False)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.clients_table.setShowGrid(False)
        self.clients_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.clients_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 设置初始高度（只显示2行 + 表头）
        row_height = 50
        header_height = 35
        self.collapsed_height = header_height + row_height * 2
        self.clients_table.setFixedHeight(self.collapsed_height)
        self.clients_table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: none;
                font-size: 13px;
                outline: none;
            }
            QTableWidget::item {
                padding: 15px 12px;
                border-bottom: 1px solid #efefef;
                color: #2c2c2c;
            }
            QTableWidget::item:last {
                border-bottom: none;
            }
            QHeaderView::section {
                background: #f5f5f5;
                padding: 12px;
                border: none;
                border-bottom: 1px solid #e5e5e5;
                font-weight: 600;
                color: #4a4a4a;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QTableWidget::item:selected {
                background: #e7f4ed;
                color: #07c160;
            }
            QTableWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        
        devices_container_layout.addWidget(self.clients_table)
        clients_layout.addWidget(devices_container)
        
        # 空状态提示
        self.empty_devices_hint = QLabel("暂无设备连接")
        self.empty_devices_hint.setAlignment(Qt.AlignCenter)
        self.empty_devices_hint.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 13px;
                padding: 40px;
                background: transparent;
                border: none;
            }
        """)
        self.empty_devices_hint.hide()  # 初始隐藏
        clients_layout.addWidget(self.empty_devices_hint)
        
        clients_group.setLayout(clients_layout)
        layout.addWidget(clients_group)
        
        # 状态栏
        self.status_label = QLabel("📡 状态: 未连接")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(40)  # 固定高度
        self.status_label.setStyleSheet("""
            QLabel {
                background: #f5f5f5;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
                color: #4a4a4a;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.status_label)
        
        return page
    
    def create_settings_page(self):
        """创建设置页面"""
        page = QWidget()
        page.setObjectName("settingsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        
        # Syncthing同步配置区域
        sync_group = QGroupBox()
        sync_group.setObjectName("settingsGroup")
        sync_group.setStyleSheet("""
            QGroupBox {
                border: none;
                background: transparent;
            }
        """)
        sync_layout = QVBoxLayout()
        sync_layout.setSpacing(15)
        sync_layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title_layout = QHBoxLayout()
        title_icon = QLabel()
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icons')
        sync_icon_path = os.path.join(icon_dir, 'sync.png')
        if os.path.exists(sync_icon_path):
            pixmap = QPixmap(sync_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            title_icon.setPixmap(pixmap)
        else:
            title_icon.setText("🔄")
            title_icon.setStyleSheet("font-size: 20px;")
        title_layout.addWidget(title_icon)
        
        title_label = QLabel("Syncthing 同步目录")
        title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #2c2c2c; margin-left: 5px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        sync_layout.addLayout(title_layout)
        
        # 同步目录表格
        self.sync_folders_table = QTableWidget()
        self.sync_folders_table.setColumnCount(4)
        self.sync_folders_table.setHorizontalHeaderLabels(["文件夹ID", "路径", "状态", "设备数"])
        self.sync_folders_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.sync_folders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sync_folders_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.sync_folders_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.sync_folders_table.verticalHeader().setVisible(False)
        self.sync_folders_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sync_folders_table.setSelectionMode(QTableWidget.SingleSelection)
        self.sync_folders_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sync_folders_table.setMaximumHeight(300)
        self.sync_folders_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
                color: #4a4a4a;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background: #e7f4ed;
                color: #07c160;
            }
            QTableWidget::item:hover {
                background: #f7f7f7;
            }
            QHeaderView::section {
                background: #fafafa;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: 600;
                color: #2c2c2c;
                font-size: 13px;
            }
        """)
        sync_layout.addWidget(self.sync_folders_table)
        
        # 刷新按钮
        refresh_btn_layout = QHBoxLayout()
        refresh_btn_layout.addStretch()
        
        # 暂停所有按钮
        self.pause_all_btn = QPushButton("⏸️ 暂停所有")
        self.pause_all_btn.setCursor(Qt.PointingHandCursor)
        self.pause_all_btn.clicked.connect(self.pause_all_sync_folders)
        self.pause_all_btn.setStyleSheet("""
            QPushButton {
                background: #fa5151;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #e84545;
            }
            QPushButton:pressed {
                background: #d63838;
            }
        """)
        refresh_btn_layout.addWidget(self.pause_all_btn)
        
        self.refresh_sync_btn = QPushButton("🔄 刷新")
        self.refresh_sync_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_sync_btn.clicked.connect(self.refresh_sync_folders)
        self.refresh_sync_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #06ae56;
            }
            QPushButton:pressed {
                background: #059048;
            }
        """)
        refresh_btn_layout.addWidget(self.refresh_sync_btn)
        sync_layout.addLayout(refresh_btn_layout)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
        layout.addStretch()
        return page
    
    def refresh_sync_folders(self):
        """刷新同步目录列表"""
        try:
            if not hasattr(self, 'syncthing_manager') or not self.syncthing_manager:
                MessageBox.show_warning(self, "提示", "请先连接到网络!")
                return
            
            config = self.syncthing_manager.get_config()
            if not config:
                MessageBox.show_error(self, "错误", "无法获取Syncthing配置")
                return
            
            folders = config.get('folders', [])
            
            # 清空表格
            self.sync_folders_table.setRowCount(0)
            
            # 填充数据
            for folder in folders:
                row = self.sync_folders_table.rowCount()
                self.sync_folders_table.insertRow(row)
                
                # 文件夹ID
                folder_id = folder.get('id', '')
                id_item = QTableWidgetItem(folder_id)
                id_item.setFont(QFont("Consolas", 11))
                self.sync_folders_table.setItem(row, 0, id_item)
                
                # 路径
                path_item = QTableWidgetItem(folder.get('path', ''))
                path_item.setFont(QFont("Consolas", 11))
                self.sync_folders_table.setItem(row, 1, path_item)
                
                # 状态
                paused = folder.get('paused', False)
                status_text = "⏸️ 已暂停" if paused else "▶️ 同步中"
                status_item = QTableWidgetItem(status_text)
                if paused:
                    status_item.setForeground(QColor("#fa5151"))
                else:
                    status_item.setForeground(QColor("#07c160"))
                self.sync_folders_table.setItem(row, 2, status_item)
                
                # 设备数
                device_count = len(folder.get('devices', []))
                device_item = QTableWidgetItem(str(device_count))
                device_item.setTextAlignment(Qt.AlignCenter)
                self.sync_folders_table.setItem(row, 3, device_item)
            
            logger.info(f"已刷新同步目录列表: {len(folders)} 个文件夹")
            
        except Exception as e:
            logger.error(f"刷新同步目录失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            MessageBox.show_error(self, "错误", f"刷新失败\n\n{str(e)}")
    
    def _pause_all_folders_on_connect(self):
        """连接成功后自动暂停所有文件夹（防止自动同步）"""
        try:
            if not hasattr(self, 'syncthing_manager') or not self.syncthing_manager:
                return
            
            config = self.syncthing_manager.get_config()
            if not config:
                return
            
            folders = config.get('folders', [])
            paused_count = 0
            
            for folder in folders:
                if not folder.get('paused', False):
                    folder['paused'] = True
                    paused_count += 1
            
            if paused_count > 0:
                self.syncthing_manager.set_config(config)
                logger.info(f"连接成功后自动暂停了 {paused_count} 个文件夹，防止自动同步")
            
        except Exception as e:
            logger.error(f"自动暂停文件夹失败: {e}")
    
    def pause_all_sync_folders(self):
        """暂停所有同步文件夹"""
        try:
            if not hasattr(self, 'syncthing_manager') or not self.syncthing_manager:
                MessageBox.show_warning(self, "提示", "请先连接到网络!")
                return
            
            config = self.syncthing_manager.get_config()
            if not config:
                MessageBox.show_error(self, "错误", "无法获取Syncthing配置")
                return
            
            folders = config.get('folders', [])
            paused_count = 0
            
            for folder in folders:
                if not folder.get('paused', False):
                    folder['paused'] = True
                    paused_count += 1
            
            if paused_count > 0:
                self.syncthing_manager.set_config(config)
                MessageBox.show_info(self, "成功", f"已暂停 {paused_count} 个同步文件夹")
                logger.info(f"手动暂停了 {paused_count} 个文件夹")
                # 刷新表格
                self.refresh_sync_folders()
            else:
                MessageBox.show_info(self, "提示", "所有文件夹已处于暂停状态")
            
        except Exception as e:
            logger.error(f"暂停所有文件夹失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            MessageBox.show_error(self, "错误", f"暂停失败\n\n{str(e)}")
    
    def create_game_page(self):
        """创建游戏管理页面 - 三栏布局(左:游戏列表 | 中:存档列表 | 右:存档详情)"""
        page = QWidget()
        page.setObjectName("gamePage")
        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== 左侧游戏列表 =====
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_panel.setStyleSheet("""
            QWidget {
                background: #f7f7f7;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 游戏列表标题
        game_list_header = QWidget()
        game_list_header.setFixedHeight(50)
        game_list_header.setStyleSheet("background: #ededed; border-bottom: 1px solid #d6d6d6;")
        header_layout = QHBoxLayout(game_list_header)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        game_title = QLabel("游戏列表")
        game_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #2c2c2c;")
        game_title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(game_title)
        
        left_layout.addWidget(game_list_header)
        
        # 游戏列表
        self.game_list_widget = QListWidget()
        self.game_list_widget.setStyleSheet("""
            QListWidget {
                background: #f7f7f7;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #ececec;
                color: #2c2c2c;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background: #e7e7e7;
            }
            QListWidget::item:selected {
                background: #d9d9d9;
                color: #000000;
            }
        """)
        self.game_list_widget.itemClicked.connect(self.on_game_selected)
        left_layout.addWidget(self.game_list_widget)
        
        # 添加游戏按钮
        add_game_btn = QPushButton()
        add_game_btn.setFixedHeight(50)
        add_game_btn.setCursor(Qt.PointingHandCursor)
        add_game_btn.clicked.connect(self.add_game)
        
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icons')
        add_icon_path = os.path.join(icon_dir, 'add.png')
        if os.path.exists(add_icon_path):
            add_game_btn.setIcon(QIcon(add_icon_path))
            add_game_btn.setIconSize(QPixmap(20, 20).size())
            add_game_btn.setText(" 添加游戏")
        else:
            add_game_btn.setText("+ 添加游戏")
        
        add_game_btn.setStyleSheet("""
            QPushButton {
                background: #ededed;
                border: none;
                border-top: 1px solid #d6d6d6;
                color: #07c160;
                font-size: 14px;
                font-weight: 500;
                text-align: center;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
            QPushButton:pressed {
                background: #d6d6d6;
            }
        """)
        left_layout.addWidget(add_game_btn)
        
        main_layout.addWidget(left_panel)
        
        # ===== 中间存档列表 =====
        middle_panel = QWidget()
        middle_panel.setFixedWidth(280)
        middle_panel.setStyleSheet("""
            #middlePanel {
                background: #ffffff;
                border-left: 1px solid #e0e0e0;
                border-right: 1px solid #e0e0e0;
            }
        """)
        middle_panel.setObjectName("middlePanel")
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # 存档列表标题
        save_list_header = QWidget()
        save_list_header.setFixedHeight(50)
        save_list_header.setStyleSheet("background: #fafafa; border-bottom: 1px solid #e0e0e0;")
        save_header_layout = QHBoxLayout(save_list_header)
        save_header_layout.setContentsMargins(15, 0, 15, 0)
        
        self.save_list_title = QLabel("存档列表")
        self.save_list_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #2c2c2c;")
        save_header_layout.addWidget(self.save_list_title)
        save_header_layout.addStretch()
        
        middle_layout.addWidget(save_list_header)
        
        # 存档列表
        self.save_list_widget = QListWidget()
        self.save_list_widget.setFrameShape(QFrame.NoFrame)  # 移除框架
        self.save_list_widget.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 15px;
                border: none;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f7f7f7;
                border: none;
            }
            QListWidget::item:selected {
                background: #e7f4ed;
                border: none;
            }
        """)
        self.save_list_widget.itemClicked.connect(self.on_save_selected)
        middle_layout.addWidget(self.save_list_widget, 1)  # 添加弹性伸缩参数
        
        # 底部删除游戏按钮（与添加游戏对齐）
        self.delete_game_btn = QPushButton()
        self.delete_game_btn.setFixedHeight(50)
        self.delete_game_btn.setCursor(Qt.PointingHandCursor)
        self.delete_game_btn.clicked.connect(self.delete_current_game)
        self.delete_game_btn.setText("🗑️ 删除游戏")
        self.delete_game_btn.setStyleSheet("""
            QPushButton {
                background: #ededed;
                border: none;
                border-top: 1px solid #d6d6d6;
                color: #fa5151;
                font-size: 14px;
                font-weight: 500;
                text-align: center;
            }
            QPushButton:hover {
                background: #fff0f0;
            }
            QPushButton:pressed {
                background: #ffd6d6;
            }
        """)
        self.delete_game_btn.setVisible(False)  # 默认隐藏，选择游戏后显示
        middle_layout.addWidget(self.delete_game_btn)
        
        main_layout.addWidget(middle_panel)
        
        # ===== 右侧存档详情 =====
        right_panel = QWidget()
        right_panel.setStyleSheet("background: #ffffff;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 详情标题
        detail_header = QWidget()
        detail_header.setFixedHeight(50)
        detail_header.setStyleSheet("background: #fafafa; border-bottom: 1px solid #e0e0e0;")
        detail_header_layout = QHBoxLayout(detail_header)
        detail_header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.detail_title_label = QLabel("存档详情")
        self.detail_title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #2c2c2c;")
        detail_header_layout.addWidget(self.detail_title_label)
        
        # 同步状态标签（显示在标题旁边）
        self.sync_status_label = QLabel("")
        self.sync_status_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #07c160;
                margin-left: 15px;
                padding: 4px 12px;
                background: #f0f9ff;
                border-radius: 4px;
                border: 1px solid #91d5ff;
            }
        """)
        self.sync_status_label.setVisible(False)
        detail_header_layout.addWidget(self.sync_status_label)
        
        detail_header_layout.addStretch()
        
        right_layout.addWidget(detail_header)
        
        # 详情内容区域（可滚动）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")
        
        detail_content = QWidget()
        self.detail_content_layout = QVBoxLayout(detail_content)
        self.detail_content_layout.setContentsMargins(25, 25, 25, 25)
        self.detail_content_layout.setSpacing(20)
        
        # 空状态提示
        self.empty_detail_widget = QWidget()
        empty_detail_layout = QVBoxLayout(self.empty_detail_widget)
        empty_detail_layout.setAlignment(Qt.AlignCenter)
        
        empty_icon = QLabel("💾")
        empty_icon.setStyleSheet("font-size: 48px;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_detail_layout.addWidget(empty_icon)
        
        empty_hint = QLabel("请从中间选择存档查看详情")
        empty_hint.setStyleSheet("font-size: 14px; color: #999999; margin-top: 10px;")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_detail_layout.addWidget(empty_hint)
        
        self.detail_content_layout.addWidget(self.empty_detail_widget)
        
        # 存档信息卡片（初始隐藏）
        self.save_info_card = self.create_save_info_card()
        self.save_info_card.setVisible(False)
        self.detail_content_layout.addWidget(self.save_info_card)
        
        # 玩家信息卡片（初始隐藏）
        self.player_info_card = self.create_player_info_card()
        self.player_info_card.setVisible(False)
        self.detail_content_layout.addWidget(self.player_info_card)
        
        self.detail_content_layout.addStretch()
        
        scroll_area.setWidget(detail_content)
        right_layout.addWidget(scroll_area, 1)  # 添加弹性伸缩参数
        
        # 底部按钮区域
        bottom_btn_container = QWidget()
        bottom_btn_container.setFixedHeight(50)
        bottom_btn_container.setStyleSheet("background: #fafafa; border-top: 1px solid #e0e0e0;")
        bottom_btn_layout = QHBoxLayout(bottom_btn_container)
        bottom_btn_layout.setContentsMargins(20, 0, 20, 0)
        bottom_btn_layout.setSpacing(10)
        
        # 添加弹性空间，使按钮右对齐
        bottom_btn_layout.addStretch()
        
        # 选择用户按钮
        self.select_user_btn = QPushButton("👤 选择用户")
        self.select_user_btn.setCursor(Qt.PointingHandCursor)
        self.select_user_btn.clicked.connect(self.select_user_account)
        self.select_user_btn.setStyleSheet("""
            QPushButton {
                background: #52c41a;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #73d13d;
            }
            QPushButton:disabled {
                background: #d0d0d0;
                color: #999999;
            }
        """)
        bottom_btn_layout.addWidget(self.select_user_btn)
        
        # 启动游戏按钮
        self.launch_game_btn = QPushButton("🎮 启动游戏")
        self.launch_game_btn.setCursor(Qt.PointingHandCursor)
        self.launch_game_btn.clicked.connect(self.launch_game)
        self.launch_game_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
            QPushButton:disabled {
                background: #d0d0d0;
                color: #999999;
            }
        """)
        bottom_btn_layout.addWidget(self.launch_game_btn)
        
        # 启动同步按钮
        self.start_sync_btn = QPushButton("🚀 启动同步")
        self.start_sync_btn.setCursor(Qt.PointingHandCursor)
        self.start_sync_btn.clicked.connect(self.start_save_sync)
        self.start_sync_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #06ae56;
            }
            QPushButton:disabled {
                background: #d0d0d0;
                color: #999999;
            }
        """)
        bottom_btn_layout.addWidget(self.start_sync_btn)
        
        # 默认隐藏这三个按钮，只有选中存档时才显示
        self.select_user_btn.setVisible(False)
        self.launch_game_btn.setVisible(False)
        self.start_sync_btn.setVisible(False)
        
        right_layout.addWidget(bottom_btn_container)
        
        main_layout.addWidget(right_panel)
        
        return page
        self.game_launcher_label.setStyleSheet("font-size: 12px; color: #666666;")
        game_info_layout.addWidget(self.game_launcher_label)
        
        self.game_update_label = QLabel("最后更新：-")
        self.game_update_label.setStyleSheet("font-size: 11px; color: #999999;")
        game_info_layout.addWidget(self.game_update_label)
        
        self.game_path_label = QLabel("游戏路径：-")
        self.game_path_label.setStyleSheet("font-size: 11px; color: #999999;")
        self.game_path_label.setWordWrap(True)
        game_info_layout.addWidget(self.game_path_label)
        
        save_detail_layout.addWidget(game_info_card)
        
        # 存档文件列表
        save_list_label = QLabel("存档文件")
        save_list_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #2c2c2c; margin-top: 10px;")
        save_detail_layout.addWidget(save_list_label)
        
        self.save_list_widget = QListWidget()
        self.save_list_widget.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f7f7f7;
            }
            QListWidget::item:selected {
                background: #e7f4ed;
                color: #07c160;
            }
        """)
        # 连接双击事件
        self.save_list_widget.itemDoubleClicked.connect(self.on_save_item_double_clicked)
        save_detail_layout.addWidget(self.save_list_widget)  # 移除弹性布局参数
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.sync_btn = QPushButton("✅ 启用同步")
        self.sync_btn.clicked.connect(self.toggle_sync)
        self.sync_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        btn_layout.addWidget(self.sync_btn)
        
        delete_btn = QPushButton("🗑️ 删除游戏")
        delete_btn.clicked.connect(self.delete_current_game)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                color: #fa5151;
                border: 1px solid #fa5151;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #fff0f0;
            }
        """)
        btn_layout.addWidget(delete_btn)
        
        save_detail_layout.addLayout(btn_layout)
        
        self.save_content_stack.addWidget(save_detail_page)
        
        right_layout.addWidget(self.save_content_stack)
        
        main_layout.addWidget(right_panel)  # 移除弹性布局参数
        
        return page
    
    # ==================== 业务逻辑方法 ====================
    
    def switch_page(self, page_name):
        """切换页面"""
        self.current_page = page_name
        if page_name == "network":
            self.content_stack.setCurrentIndex(0)
            self.page_name_label.setText(" - 联机设置")
            # 更新按钮样式
            self.network_btn.setStyleSheet("""
                QPushButton {
                    background: #07c160;
                    color: #ffffff;
                    border: none;
                    border-left: 3px solid #06ae56;
                    font-size: 24px;
                }
                QPushButton:hover {
                    background: #06ae56;
                }
            """)
            self.game_btn.setStyleSheet("""
                QPushButton {
                    background: #ededed;
                    color: #666666;
                    border: none;
                    font-size: 24px;
                }
                QPushButton:hover {
                    background: #07c160;
                    color: #ffffff;
                }
            """)
        elif page_name == "game":
            self.content_stack.setCurrentIndex(1)
            self.page_name_label.setText(" - 游戏管理")
            self.load_game_list()
            # 更新按钮样式
            self.network_btn.setStyleSheet("""
                QPushButton {
                    background: #ededed;
                    color: #666666;
                    border: none;
                    font-size: 24px;
                }
                QPushButton:hover {
                    background: #07c160;
                    color: #ffffff;
                }
            """)
            self.game_btn.setStyleSheet("""
                QPushButton {
                    background: #07c160;
                    color: #ffffff;
                    border: none;
                    border-left: 3px solid #06ae56;
                    font-size: 24px;
                }
                QPushButton:hover {
                    background: #06ae56;
                }
            """)
            self.settings_btn.setStyleSheet("""
                QPushButton {
                    background: #ededed;
                    color: #666666;
                    border: none;
                    font-size: 24px;
                }
                QPushButton:hover {
                    background: #07c160;
                    color: #ffffff;
                }
            """)
        elif page_name == "settings":
            self.content_stack.setCurrentIndex(2)
            self.page_name_label.setText(" - 设置")
            # 刷新同步目录
            self.refresh_sync_folders()
            # 更新按钮样式
            self.network_btn.setStyleSheet("""
                QPushButton {
                    background: #ededed;
                    color: #666666;
                    border: none;
                    font-size: 24px;
                }
                QPushButton:hover {
                    background: #07c160;
                    color: #ffffff;
                }
            """)
            self.game_btn.setStyleSheet("""
                QPushButton {
                    background: #ededed;
                    color: #666666;
                    border: none;
                    font-size: 24px;
                }
                QPushButton:hover {
                    background: #07c160;
                    color: #ffffff;
                }
            """)
            self.settings_btn.setStyleSheet("""
                QPushButton {
                    background: #07c160;
                    color: #ffffff;
                    border: none;
                    border-left: 3px solid #06ae56;
                    font-size: 24px;
                }
                QPushButton:hover {
                    background: #06ae56;
                }
            """)
    
    def connect_to_network(self):
        """连接到网络"""
        room_name = self.room_input.text().strip()
        password = self.password_input.text().strip()
        
        if not room_name or not password:
            MessageBox.show_warning(self, "提示", "请输入房间号和密码")
            return
        
        # 固定使用官方节点
        selected_peer = None
        use_peer = True
        
        # 保存配置
        self.config_data["network"] = {
            "room_name": room_name,
            "password": password
        }
        ConfigCache.save(self.config_data)
        
        # 启动连接线程（固定使用官方节点）
        self.connect_thread = ConnectThread(self.controller, room_name, password, None, True)
        self.connect_thread.connected.connect(self.on_connected)
        self.connect_thread.progress.connect(self.on_connect_progress)
        self.connect_thread.start()
        
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("正在连接...")
        self.status_label.setText("📡 状态: 正在连接...")
    
    def on_connect_progress(self, message):
        """连接进度回调"""
        self.status_label.setText(f"📡 {message}")
    
    def on_connected(self, success, message):
        """连接完成回调"""
        self.connect_btn.setEnabled(True)
        
        if success:
            self.is_connected = True
            self.status_label.setText(f"📡 状态: 已连接 | 虚拟IP: {message}")
            
            # 将Syncthing管理器暴露给主窗口使用
            self.syncthing_manager = self.controller.syncthing
            logger.info("Syncthing管理器已准备好")
            
            # 注册Syncthing事件回调
            self.syncthing_manager.register_event_callback(self.on_syncthing_event)
            logger.info("已注册Syncthing事件监听")
            
            # 自动暂停所有同步文件夹（防止自动同步）
            self._pause_all_folders_on_connect()
            
            # 初始化UDP广播
            from managers.mqtt_manager import MQTTManager
            self.mqtt_manager = MQTTManager()
            # UDP广播,无需Broker
            self.mqtt_manager.connect(broker_port=9999)
            self.mqtt_manager.register_callback(self.on_mqtt_message)
            logger.info("UDP广播已启动")
            
            # 广播设备上线消息，通知其他客户端刷新列表
            self.mqtt_manager.publish("device/online", {
                "device_id": self.syncthing_manager.device_id,
                "virtual_ip": message,  # 虚拟IP
                "hostname": Config.HOSTNAME
            })
            logger.info("已广播设备上线消息")
            
            # 连接成功后不弹框，按钮变为断开连接
            self.connect_btn.setText("断开连接")
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.disconnect_network)
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background: #fa5151;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 14px;
                    font-weight: normal;
                    padding: 10px 24px;
                }
                QPushButton:hover {
                    background: #e84545;
                }
                QPushButton:pressed {
                    background: #d63838;
                }
                QPushButton:disabled {
                    background: #faa;
                    color: #ffffff;
                }
            """)
            # 开启客户端监控
            self.last_peer_ips = set()  # 重置状态
            self.last_peer_count = 0
            self.update_clients_list()
        else:
            self.is_connected = False
            self.status_label.setText("📡 状态: 连接失败")
            self.connect_btn.setText("连接到网络")
            
            # 构建错误提示信息
            error_msg = f"连接失败\n\n{message}\n\n"
            error_msg += "💡 建议：\n"
            error_msg += "• 请切换节点重试\n"
            error_msg += "• 检查网络连接是否正常\n"
            error_msg += "• 稍后再试或联系管理员"
            
            MessageBox.show_error(self, "连接失败", error_msg)
    
    def disconnect_network(self):
        """断开网络连接"""
        try:
            # 停止服务
            self.controller.cleanup()
            
            self.is_connected = False
            self.syncthing_manager = None  # 清理Syncthing管理器引用
            self.status_label.setText("📡 状态: 未连接")
            
            # 清空客户端列表
            self.clients_table.setRowCount(0)
            
            # 按钮恢复为连接状态
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.connect_to_network)
            self.connect_btn.setText("连接到网络")
            self.connect_btn.setObjectName("connectBtn")
            # 恢复原来的样式（通过全局样式表）
            self.connect_btn.setStyleSheet("")
            self.setStyleSheet(self.styleSheet())  # 重新应用全局样式
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
            MessageBox.show_error(self, "错误", f"断开连接失败\n\n{str(e)}")
    
    def update_clients_list(self):
        """更新客户端列表"""
        if not self.is_connected:
            return
        
        try:
            # 获取对等设备列表
            peers = self.controller.easytier.discover_peers(timeout=3)
            
            # 清空表格
            self.clients_table.setRowCount(0)
            
            # 添加本机
            row = 0
            self.clients_table.insertRow(row)
            
            # 设备名 - 添加徽章
            device_name_item = QTableWidgetItem("💻 本机")
            device_name_item.setFont(QFont("Microsoft YaHei", 13))
            self.clients_table.setItem(row, 0, device_name_item)
            
            # IP地址
            ip_item = QTableWidgetItem(self.controller.easytier.virtual_ip or "unknown")
            ip_item.setFont(QFont("Consolas", 12))
            self.clients_table.setItem(row, 1, ip_item)
            
            # 延迟
            latency_item = QTableWidgetItem("-")
            self.clients_table.setItem(row, 2, latency_item)
            
            # 添加其他设备（去除重复）
            seen_ips = set([self.controller.easytier.virtual_ip])  # 记录已显示的IP
            
            for peer in peers:
                ipv4 = peer.get('ipv4', '')
                # 跳过本机IP和重复IP
                if ipv4 and ipv4 not in seen_ips:
                    # 尝试获取远程设备的Syncthing ID
                    device_id = self._get_remote_syncthing_id(ipv4)
                    if device_id and device_id != self.syncthing_manager.device_id:
                        # 添加到Syncthing设备列表
                        hostname = peer.get('hostname', 'Unknown')
                        self.syncthing_manager.add_device(device_id, hostname)
                        logger.info(f"已添加设备到Syncthing: {hostname} ({device_id[:7]}...)")
                        
                        # 如果正在同步，将新设备添加到同步文件夹
                        if hasattr(self, 'syncing_folder_id'):
                            self.syncthing_manager.add_device_to_folder(self.syncing_folder_id, device_id)
                            logger.info(f"已将设备 {hostname} 添加到同步文件夹: {self.syncing_folder_id}")
                    
                    row += 1
                    self.clients_table.insertRow(row)
                    
                    hostname = peer.get('hostname', 'Unknown')
                    latency = peer.get('latency', '-')
                    
                    # 设备名
                    device_item = QTableWidgetItem(f"🖥️ {hostname}")
                    device_item.setFont(QFont("Microsoft YaHei", 13))
                    self.clients_table.setItem(row, 0, device_item)
                    
                    # IP地址
                    ip_item = QTableWidgetItem(ipv4)
                    ip_item.setFont(QFont("Consolas", 12))
                    self.clients_table.setItem(row, 1, ip_item)
                    
                    # 延迟 - 添加颜色区分
                    latency_item = QTableWidgetItem(latency)
                    if latency != '-':
                        try:
                            lat_ms = float(latency.replace('ms', '').strip())
                            if lat_ms < 50:
                                latency_item.setForeground(Qt.green)
                            elif lat_ms < 100:
                                latency_item.setForeground(QColor("#07c160"))
                            else:
                                latency_item.setForeground(QColor("#fa5151"))
                        except:
                            pass
                    self.clients_table.setItem(row, 2, latency_item)
                    
                    seen_ips.add(ipv4)  # 标记已显示
            
            # 更新设备计数
            total_devices = row + 1
            self.device_count_label.setText(f"({total_devices})")
            
            # 显示/隐藏查看全部按钮（临时：1台以上就显示）
            if total_devices > 1:
                self.view_all_btn.show()
            else:
                self.view_all_btn.hide()
            
            # 显示/隐藏空状态
            if total_devices == 0:
                self.clients_table.hide()
                self.empty_devices_hint.show()
            else:
                self.clients_table.show()
                self.empty_devices_hint.hide()
            
            logger.info(f"更新客户端列表: 总计 {total_devices} 台设备")
            
        except Exception as e:
            logger.error(f"更新客户端列表失败: {e}")
    
    def _get_remote_syncthing_id(self, peer_ip):
        """获取远程设备的Syncthing ID"""
        try:
            import requests
            from config import Config
            
            # 通过SOCKS5代理访问远程 Syncthing API
            proxies = {
                'http': f'socks5h://127.0.0.1:{Config.EASYTIER_SOCKS5_PORT}',
                'https': f'socks5h://127.0.0.1:{Config.EASYTIER_SOCKS5_PORT}'
            }
            
            url = f"http://{peer_ip}:{Config.SYNCTHING_API_PORT}/rest/system/status"
            headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
            
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=3)
            resp.raise_for_status()
            
            device_id = resp.json()["myID"]
            logger.debug(f"从 {peer_ip} 获取到设备ID: {device_id[:7]}...")
            return device_id
        except Exception as e:
            logger.debug(f"无法从 {peer_ip} 获取Syncthing ID: {e}")
            return None
    
    def load_game_list(self):
        """加载游戏列表"""
        # 重新加载配置
        self.config_data = ConfigCache.load()
        
        self.game_list_widget.clear()
        game_list = self.config_data.get("game_list", [])
        
        for game in game_list:
            # 获取同步状态
            is_syncing = game.get('is_syncing', False)
            # 使用PNG图标 - 使用绝对路径
            import os
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'assets')
            icon_path = os.path.join(assets_dir, 'sync.png' if is_syncing else 'unsync.png')
            
            # 如果图标不存在,使用默认图标
            if os.path.exists(icon_path):
                item = QListWidgetItem(QIcon(icon_path), f" 🎮 {game.get('name', '未命名')}")
            else:
                status_icon = "🟢" if is_syncing else "⚪"
                item = QListWidgetItem(f"{status_icon} 🎮 {game.get('name', '未命名')}")
            
            item.setData(Qt.UserRole, game)  # 存储完整游戏信息
            self.game_list_widget.addItem(item)
        
        # 取消默认选中
        self.game_list_widget.setCurrentItem(None)
    
    def on_game_selected(self, item):
        """游戏选中事件 - 加载该游戏的存档列表"""
        game_data = item.data(Qt.UserRole)
        if game_data:
            # 保存当前选中的游戏
            self.current_game_data = game_data
            
            # 更新中间存档列表标题
            game_name = game_data.get('name', '未命名')
            self.save_list_title.setText(f"💾 {game_name}")
            
            # 加载存档列表
            self.load_game_saves(game_data)
            
            # 清空右侧详情(显示空状态)
            self.show_empty_detail()
            
            # 显示删除游戏按钮和同步按钮
            self.delete_game_btn.setVisible(True)
            self.start_sync_btn.setVisible(True)
            
            # 隐藏启动游戏和选择用户按钮（需要选择存档后才显示）
            self.select_user_btn.setVisible(False)
            self.launch_game_btn.setVisible(False)
    
    def load_player_list(self, game_data):
        """加载玩家列表 - 漂浮头像"""
        # 清除旧的漂浮头像
        if hasattr(self, 'floating_avatars'):
            for avatar in self.floating_avatars:
                avatar.deleteLater()
            self.floating_avatars = []
        
        # 对于MC游戏,扫描玩家
        if game_data.get('type') == 'minecraft':
            try:
                from ui.minecraft.version_scanner import MinecraftVersionScanner
                import os
                
                save_path = game_data.get('save_path', '')
                if not save_path or not os.path.exists(save_path):
                    return
                
                scanner = MinecraftVersionScanner("")
                players = scanner.get_save_players(save_path)
                
                if players:
                    # 获取右侧面板
                    right_panel = self.save_content_stack.currentWidget()
                    if not right_panel:
                        return
                    
                    self.floating_avatars = []
                    
                    for player in players:
                        avatar_widget = self.create_floating_avatar(player, right_panel)
                        self.floating_avatars.append(avatar_widget)
            
            except Exception as e:
                logger.error(f"加载玩家列表失败: {e}")
    
    def create_floating_avatar(self, player, parent_widget):
        """创建漂浮的玩家头像"""
        import random
        
        avatar_widget = QLabel(parent_widget)
        avatar_widget.setFixedSize(60, 60)
        avatar_widget.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 200);
                border-radius: 4px;
            }
        """)
        avatar_widget.setAlignment(Qt.AlignCenter)
        avatar_widget.setScaledContents(True)
        
        uuid = player.get('uuid', '')
        player_name = player.get('name', '未知')
        
        logger.info(f"创建漂浮头像 - UUID: {uuid}, 玩家: {player_name}")
        
        # 设置提示信息(玩家名)
        avatar_widget.setToolTip(player_name if player_name else uuid[:8])
        
        # 使用Minotar API获取玩家头像(无连字符UUID)
        avatar_url = f"https://minotar.net/avatar/{uuid}/64.png"
        
        # 初始隐藏,等头像加载成功后再显示
        avatar_widget.hide()
        
        # 随机初始位置
        parent_size = parent_widget.size()
        random_x = random.randint(50, max(100, parent_size.width() - 100))
        random_y = random.randint(50, max(100, parent_size.height() - 100))
        avatar_widget.move(random_x, random_y)
        
        # 异步加载头像,加载成功后显示并启动动画
        self.load_player_avatar(avatar_widget, avatar_url, uuid, parent_widget)
        
        return avatar_widget
    
    def add_full_area_float_animation(self, widget, parent_widget):
        """全区域随机漂浮动画"""
        import random
        
        def create_next_animation():
            try:
                # 检查widget是否还存在
                if not widget or not hasattr(widget, 'pos'):
                    return
                
                # 创建位置动画
                animation = QPropertyAnimation(widget, b"pos")
                animation.setDuration(random.randint(3000, 6000))  # 3-6秒
                animation.setEasingCurve(QEasingCurve.InOutQuad)
                
                # 当前位置
                current_pos = widget.pos()
                
                # 随机目标位置(在父组件范围内)
                parent_size = parent_widget.size()
                target_x = random.randint(20, max(50, parent_size.width() - 80))
                target_y = random.randint(20, max(50, parent_size.height() - 80))
                
                animation.setStartValue(current_pos)
                animation.setEndValue(QPoint(target_x, target_y))
                
                # 动画结束后创建下一个动画
                animation.finished.connect(create_next_animation)
                
                # 保存动画引用
                if not hasattr(self, 'float_animations'):
                    self.float_animations = []
                self.float_animations.append(animation)
                
                animation.start()
            except RuntimeError as e:
                # widget已被删除,停止动画
                logger.warning(f"漂浮动画组件已删除: {e}")
                return
        
        # 延迟启动
        delay = random.randint(0, 1000)
        QTimer.singleShot(delay, create_next_animation)
    
    def load_player_avatar(self, label, url, uuid, parent_widget=None):
        """异步加载玩家头像(带缓存)"""
        try:
            import os
            from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
            from PyQt5.QtCore import QUrl
            
            # 检查缓存
            cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache', 'avatars')
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"{uuid}.png")
            
            # 如果缓存存在,直接加载
            if os.path.exists(cache_file):
                pixmap = QPixmap(cache_file)
                if not pixmap.isNull():
                    logger.info(f"从缓存加载头像: {uuid}")
                    label.setPixmap(pixmap)
                    label.show()
                    label.raise_()
                    if parent_widget:
                        self.add_full_area_float_animation(label, parent_widget)
                    return
            
            if not hasattr(self, 'network_managers'):
                self.network_managers = []
            
            manager = QNetworkAccessManager()
            self.network_managers.append(manager)
            
            logger.info(f"下载头像: {url}")
            
            request = QNetworkRequest(QUrl(url))
            # 设置自动跟随重定向
            request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
            reply = manager.get(request)
            
            def on_finished():
                try:
                    # 检查label是否还有效
                    if not label or not hasattr(label, 'setPixmap'):
                        reply.deleteLater()
                        return
                    
                    if reply.error() == reply.NoError:
                        data = reply.readAll()
                        logger.info(f"头像数据大小: {len(data)} bytes")
                        
                        pixmap = QPixmap()
                        if pixmap.loadFromData(data):
                            logger.info(f"头像下载成功: {pixmap.width()}x{pixmap.height()}")
                            
                            # 保存到缓存
                            try:
                                pixmap.save(cache_file, 'PNG')
                                logger.info(f"头像已缓存: {cache_file}")
                            except Exception as e:
                                logger.warning(f"缓存头像失败: {e}")
                            
                            label.setPixmap(pixmap)
                            
                            # 头像加载成功,显示并启动动画
                            label.show()
                            label.raise_()
                            if parent_widget:
                                self.add_full_area_float_animation(label, parent_widget)
                        else:
                            logger.error("头像数据解析失败")
                            label.setText("👤")
                            label.setStyleSheet(label.styleSheet() + "font-size: 20px;")
                    else:
                        # 加载失败,显示默认图标
                        error_string = reply.errorString()
                        logger.error(f"头像请求失败: {error_string}")
                        label.setText("👤")
                        label.setStyleSheet(label.styleSheet() + "font-size: 20px;")
                except RuntimeError as e:
                    # 对象已被删除,忽略
                    logger.warning(f"头像组件已删除: {e}")
                finally:
                    reply.deleteLater()
            
            reply.finished.connect(on_finished)
            
        except Exception as e:
            logger.error(f"加载头像异常: {e}")
            label.setText("👤")
            label.setStyleSheet(label.styleSheet() + "font-size: 20px;")
    
    def load_player_name(self, label, uuid):
        """异步获取玩家名称"""
        try:
            from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
            from PyQt5.QtCore import QUrl
            import json
            
            if not hasattr(self, 'name_managers'):
                self.name_managers = []
            
            manager = QNetworkAccessManager()
            self.name_managers.append(manager)
            
            # UUID已经是无连字符格式,直接使用
            url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
            
            request = QNetworkRequest(QUrl(url))
            reply = manager.get(request)
            
            def on_finished():
                if reply.error() == reply.NoError:
                    data = reply.readAll()
                    try:
                        profile = json.loads(bytes(data).decode('utf-8'))
                        name = profile.get('name', uuid[:8])
                        label.setText(name)
                    except:
                        label.setText(uuid[:8])
                else:
                    # 请求失败,显示UUID
                    label.setText(uuid[:8])
                reply.deleteLater()
            
            reply.finished.connect(on_finished)
            
        except Exception as e:
            logger.error(f"获取玩家名称失败: {e}")
            label.setText(uuid[:8])
    
    def load_save_list(self, game_data):
        """加载存档文件列表"""
        self.save_list_widget.clear()
        
        # 对于MC游戏,列出存档内的所有文件和目录
        if game_data.get('type') == 'minecraft':
            try:
                import os
                from datetime import datetime
                
                # 获取存档路径
                save_path = game_data.get('save_path', '')
                if not save_path:
                    item = QListWidgetItem("无法获取存档路径")
                    item.setFlags(Qt.NoItemFlags)
                    self.save_list_widget.addItem(item)
                    return
                
                # 保存当前浏览路径
                if not hasattr(self, 'current_save_path'):
                    self.current_save_path = save_path
                    self.root_save_path = save_path  # 保存根目录
                
                # 如果不是根目录,添加返回上级目录的选项
                if self.current_save_path != self.root_save_path:
                    parent_item = QListWidgetItem("🔙 ..") 
                    from PyQt5.QtGui import QFont
                    font = QFont("Consolas", 10)
                    parent_item.setFont(font)
                    parent_item.setData(Qt.UserRole, {
                        'name': '..',
                        'path': os.path.dirname(self.current_save_path),
                        'is_dir': True,
                        'is_parent': True
                    })
                    self.save_list_widget.addItem(parent_item)
                
                if not os.path.exists(self.current_save_path):
                    item = QListWidgetItem("存档文件夹不存在")
                    item.setFlags(Qt.NoItemFlags)
                    self.save_list_widget.addItem(item)
                    return
                
                # 获取所有文件和目录
                items = []
                for item_name in os.listdir(self.current_save_path):
                    item_path = os.path.join(self.current_save_path, item_name)
                    
                    # 获取修改时间
                    mtime = os.path.getmtime(item_path)
                    
                    # 判断类型
                    is_dir = os.path.isdir(item_path)
                    icon = "📁" if is_dir else "📄"
                    
                    items.append({
                        'name': item_name,
                        'path': item_path,
                        'is_dir': is_dir,
                        'mtime': mtime,
                        'icon': icon
                    })
                
                if not items:
                    item = QListWidgetItem("存档为空")
                    item.setFlags(Qt.NoItemFlags)
                    self.save_list_widget.addItem(item)
                    return
                
                # 排序:文件夹在前,然后按名称排序
                items.sort(key=lambda x: (not x['is_dir'], x['name']))
                
                # 显示所有文件和目录
                for file_item in items:
                    # 格式化同步时间
                    sync_time = datetime.fromtimestamp(file_item['mtime']).strftime("%Y-%m-%d %H:%M")
                    
                    # 创建显示文本:左侧文件名,右侧同步时间(右对齐)
                    name_text = f"{file_item['icon']} {file_item['name']}"
                    # 使用空格填充到固定宽度,实现右对齐效果
                    info_text = f"{name_text:<60}{sync_time:>16}"
                    
                    list_item = QListWidgetItem(info_text)
                    # 使用等宽字体确保对齐
                    from PyQt5.QtGui import QFont
                    font = QFont("Consolas", 10)
                    list_item.setFont(font)
                    # 保存文件信息到item的UserRole
                    list_item.setData(Qt.UserRole, file_item)
                    self.save_list_widget.addItem(list_item)
            
            except Exception as e:
                logger.error(f"加载存档信息失败: {e}")
                item = QListWidgetItem(f"加载失败: {str(e)}")
                item.setFlags(Qt.NoItemFlags)
                self.save_list_widget.addItem(item)
        else:
            # 其他游戏
            saves = game_data.get('saves', [])
            if not saves:
                item = QListWidgetItem("暂无存档")
                item.setFlags(Qt.NoItemFlags)
                self.save_list_widget.addItem(item)
            else:
                for save in saves:
                    item = QListWidgetItem(f"💾 {save.get('name', '未命名存档')}")
                    self.save_list_widget.addItem(item)
    
    def on_save_item_double_clicked(self, item):
        """存档文件列表项双击事件"""
        file_data = item.data(Qt.UserRole)
        if not file_data:
            return
        
        # 如果是目录,进入该目录
        if file_data.get('is_dir'):
            self.current_save_path = file_data['path']
            # 重新加载当前游戏的存档列表
            current_item = self.game_list_widget.currentItem()
            if current_item:
                game_data = current_item.data(Qt.UserRole)
                if game_data:
                    self.load_save_list(game_data)
    
    def toggle_sync(self):
        """切换同步状态"""
        current_item = self.game_list_widget.currentItem()
        if not current_item:
            MessageBox.show_warning(self, "提示", "请先选择游戏")
            return
        
        game_data = current_item.data(Qt.UserRole)
        if not game_data:
            return
        
        # 获取当前同步状态
        is_syncing = game_data.get('is_syncing', False)
        
        if is_syncing:
            # 停止同步
            self.stop_sync(game_data)
        else:
            # 启用同步
            self.start_sync(game_data)
    
    def start_sync(self, game_data):
        """启用同步"""
        try:
            from managers.syncthing_manager import SyncthingManager
            
            # 检查是否已连接网络
            if not self.is_connected:
                MessageBox.show_warning(self, "提示", "请先连接到网络！")
                return
            
            # 检查Syncthing是否启动
            if not hasattr(self, 'syncthing_manager') or not self.syncthing_manager:
                MessageBox.show_warning(self, "提示", "Syncthing服务未启动，请先连接网络！")
                return
            
            game_name = game_data.get('name')
            save_path = game_data.get('save_path')
            
            if not save_path:
                MessageBox.show_error(self, "错误", "无法获取存档路径")
                return
            
            logger.info(f"启用同步: {game_name}, 路径: {save_path}")
            
            # 生成文件夹ID（使用游戏名和版本）
            folder_id = f"game-{game_data.get('type', 'unknown')}-{game_data.get('version', 'default')}".replace(' ', '-').replace('.', '-')
            folder_label = f"{game_name} - 存档同步"
            
            # 获取已连接的设备列表
            connections = self.syncthing_manager.get_connections()
            if not connections or not connections.get('connections'):
                MessageBox.show_warning(self, "提示", "没有检测到其他设备，请确保其他玩家已连接到同一房间")
                # 仍然添加文件夹，但不共享给任何设备
                device_ids = []
            else:
                # 获取所有已连接设备的ID
                device_ids = [dev_id for dev_id in connections['connections'].keys()]
                logger.info(f"检测到 {len(device_ids)} 个设备")
            
            # 添加同步文件夹
            success = self.syncthing_manager.add_folder(
                folder_path=save_path,
                folder_id=folder_id,
                folder_label=folder_label,
                devices=device_ids
            )
            
            if not success:
                MessageBox.show_error(self, "错误", "添加同步文件夹失败")
                return
            
            # 更新状态
            game_data['is_syncing'] = True
            game_data['sync_folder_id'] = folder_id
            
            # 保存配置
            game_list = self.config_data.get("game_list", [])
            for game in game_list:
                if game.get('name') == game_data.get('name'):
                    game['is_syncing'] = True
                    game['sync_folder_id'] = folder_id
                    break
            ConfigCache.save(self.config_data)
            
            # 更新按钮样式
            self.sync_btn.setText("⏸️ 停止同步")
            self.sync_btn.setStyleSheet("""
                QPushButton {
                    background: #fa5151;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 20px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #e84545;
                }
            """)
            
            MessageBox.show_info(self, "成功", f"已启用「{game_data.get('name')}」的存档同步")
            
            # 刷新游戏列表显示状态
            self.load_game_list()
            # 重新选中当前游戏
            for i in range(self.game_list_widget.count()):
                item = self.game_list_widget.item(i)
                if item.data(Qt.UserRole).get('name') == game_data.get('name'):
                    self.game_list_widget.setCurrentItem(item)
                    break
            
        except Exception as e:
            logger.error(f"启用同步失败: {e}")
            MessageBox.show_error(self, "错误", f"启用同步失败: {str(e)}")
    
    def stop_sync(self, game_data):
        """停止同步"""
        try:
            # TODO: 实际停止同步需要从 Syncthing 配置中移除文件夹
            # 或者暂停文件夹同步
            logger.info(f"停止同步: {game_data.get('name')}")
            
            folder_id = game_data.get('sync_folder_id')
            if folder_id and hasattr(self, 'syncthing_manager') and self.syncthing_manager:
                # 暂停文件夹同步（通过修改配置）
                config = self.syncthing_manager.get_config()
                if config:
                    for folder in config.get('folders', []):
                        if folder['id'] == folder_id:
                            folder['paused'] = True
                            self.syncthing_manager.set_config(config)
                            logger.info(f"已暂停文件夹: {folder_id}")
                            break
            
            # 更新状态
            game_data['is_syncing'] = False
            
            # 保存配置
            game_list = self.config_data.get("game_list", [])
            for game in game_list:
                if game.get('name') == game_data.get('name'):
                    game['is_syncing'] = False
                    break
            ConfigCache.save(self.config_data)
            
            # 更新按钮样式
            self.sync_btn.setText("✅ 启用同步")
            self.sync_btn.setStyleSheet("""
                QPushButton {
                    background: #07c160;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 20px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #06ae56;
                }
            """)
            
            MessageBox.show_info(self, "成功", f"已停止「{game_data.get('name')}」的存档同步")
            
            # 刷新游戏列表显示状态
            self.load_game_list()
            # 重新选中当前游戏
            for i in range(self.game_list_widget.count()):
                item = self.game_list_widget.item(i)
                if item.data(Qt.UserRole).get('name') == game_data.get('name'):
                    self.game_list_widget.setCurrentItem(item)
                    break
            
        except Exception as e:
            logger.error(f"停止同步失败: {e}")
            MessageBox.show_error(self, "错误", f"停止同步失败: {str(e)}")
    
    def edit_game_name(self):
        """编辑游戏名称"""
        current_item = self.game_list_widget.currentItem()
        if not current_item:
            MessageBox.show_warning(self, "提示", "请先选择要编辑的游戏")
            return
        
        game_data = current_item.data(Qt.UserRole)
        old_name = game_data.get('name', '未命名')
        
        # 使用自定义对话框
        from ui.components.dialogs.edit_name_dialog import EditNameDialog
        dialog = EditNameDialog(self, "编辑游戏名称", old_name)
        
        if dialog.exec_() == QDialog.Accepted and dialog.new_name:
            new_name = dialog.new_name
            
            # 更新配置
            game_list = self.config_data.get("game_list", [])
            for game in game_list:
                if game.get('name') == old_name:
                    game['name'] = new_name
                    break
            
            ConfigCache.save(self.config_data)
            
            # 更新界面
            self.load_game_list()
            
            # 重新选中该游戏
            for i in range(self.game_list_widget.count()):
                item = self.game_list_widget.item(i)
                if item.data(Qt.UserRole).get('name') == new_name:
                    self.game_list_widget.setCurrentItem(item)
                    self.on_game_selected(item)
                    break
    
    def delete_current_game(self):
        """删除当前选中的游戏"""
        current_item = self.game_list_widget.currentItem()
        if not current_item:
            MessageBox.show_warning(self, "提示", "请先选择要删除的游戏")
            return
        
        game_data = current_item.data(Qt.UserRole)
        game_name = game_data.get('name', '未命名')
        
        # 确认删除
        reply = MessageBox.show_question(
            self,
            "确认删除",
            f"确定要删除游戏 '{game_name}' 吗？\n\n注意：这不会删除游戏文件，只会从列表中移除。"
        )
        
        if reply:
            # 从配置中删除
            game_list = self.config_data.get("game_list", [])
            self.config_data["game_list"] = [
                g for g in game_list if g.get('name') != game_name
            ]
            ConfigCache.save(self.config_data)
            
            # 重新加载游戏列表
            self.load_game_list()
            
            # 清空当前选中的游戏
            if hasattr(self, 'current_game_data'):
                del self.current_game_data
            
            # 清空中间存档列表
            self.save_list_widget.clear()
            self.save_list_title.setText("存档列表")
            
            # 清空右侧详情
            self.show_empty_detail()
    
    def add_game(self):
        """添加游戏"""
        from ui.components.dialogs.add_game_dialog import AddGameDialog
        from ui.components.dialogs.launcher_selector import LauncherSelectorDialog
        
        # 显示游戏类型选择对话框
        dialog = AddGameDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.game_type == 'minecraft':
                # 我的世界 - 显示启动器选择对话框
                launcher_dialog = LauncherSelectorDialog(self)
                if launcher_dialog.exec_() == QDialog.Accepted:
                    # 重新加载游戏列表
                    self.load_game_list()
            elif dialog.game_type == 'other':
                # 其他游戏 - 直接选择游戏目录
                game_dir = QFileDialog.getExistingDirectory(
                    self,
                    "选择游戏目录",
                    "",
                    QFileDialog.ShowDirsOnly
                )
                if game_dir:
                    # 获取游戏名称（使用目录名）
                    game_name = os.path.basename(game_dir)
                    
                    # 添加到配置
                    if "game_list" not in self.config_data:
                        self.config_data["game_list"] = []
                    
                    self.config_data["game_list"].append({
                        "name": game_name,
                        "type": "other",
                        "path": game_dir,
                        "saves": []
                    })
                    
                    ConfigCache.save(self.config_data)
                    
                    # 重新加载游戏列表
                    self.load_game_list()
                    
                    MessageBox.show_info(self, "成功", f"游戏 '{game_name}' 已添加")
    
    def show_all_devices(self):
        """显示所有设备列表的弹窗"""
        from ui.components.dialogs.device_list_dialog import DeviceListDialog
        dialog = DeviceListDialog(self, self.controller)
        dialog.exec_()
    
    def show_peer_manager(self):
        """显示节点管理对话框"""
        dialog = PeerManagerDialog(self, self.config_data)
        dialog.exec_()
    
    def monitor_sync_state(self):
        """监控同步状态 - 只在peer列表变化时更新"""
        if not self.is_connected:
            return
        
        try:
            # 获取当前peer列表
            peers = self.controller.easytier.discover_peers(timeout=3)
            
            # 提取IP地址集合
            current_peer_ips = set()
            for peer in peers:
                ipv4 = peer.get('ipv4', '')
                if ipv4 and ipv4 != self.controller.easytier.virtual_ip:
                    current_peer_ips.add(ipv4)
            
            # 计算总设备数（包括本机）
            current_count = len(current_peer_ips) + 1
            
            # 检查是否有变化
            if current_peer_ips != self.last_peer_ips or current_count != self.last_peer_count:
                # 有新设备连接或设备断开
                logger.info(f"检测到peer列表变化: {self.last_peer_count} -> {current_count} 台设备")
                self.last_peer_ips = current_peer_ips
                self.last_peer_count = current_count
                # 更新客户端列表
                self.update_clients_list()
        except Exception as e:
            logger.debug(f"监控peer列表失败: {e}")
    
    def on_syncthing_event(self, event_type, event_data):
        """
Syncthing事件回调(收到同步事件时自动调用)
        
        Args:
            event_type: 事件类型 (ItemFinished, FolderSummary, DownloadProgress)
            event_data: 事件数据
        """
        try:
            # 只有在游戏管理页面且选中了游戏时才处理
            if self.current_page != "game" or not hasattr(self, 'current_game_data'):
                return
            
            # 更新同步状态
            if event_type == 'DownloadProgress':
                # 下载进度事件
                folder = event_data.get('folder', '')
                if hasattr(self, 'syncing_folder_id') and folder == self.syncing_folder_id:
                    self.update_sync_status(syncing=True)
            elif event_type == 'ItemFinished':
                # 文件下载完成
                item = event_data.get('item', '')
                logger.info(f"Syncthing文件下载完成: {item}")
                # 检查是否有新存档
                self.check_and_refresh_saves()
                # 更新状态为空闲
                self.update_sync_status(syncing=False)
            elif event_type == 'FolderSummary':
                # 文件夹总结事件
                folder = event_data.get('folder', '')
                summary = event_data.get('summary', {})
                if hasattr(self, 'syncing_folder_id') and folder == self.syncing_folder_id:
                    # 检查是否在同步
                    state = summary.get('state', '')
                    if state == 'syncing':
                        self.update_sync_status(syncing=True)
                    else:
                        self.update_sync_status(syncing=False)
                        # 刷新存档列表
                        self.check_and_refresh_saves()
                
        except Exception as e:
            logger.debug(f"Syncthing事件处理失败: {e}")
    
    def check_and_refresh_saves(self):
        """检查并刷新存档列表"""
        try:
            import os
            from ui.minecraft.version_scanner import MinecraftVersionScanner
            
            saves_dir = self.current_game_data.get('save_path', '')
            if not saves_dir or not os.path.exists(saves_dir):
                return
            
            # 扫描当前存档
            scanner = MinecraftVersionScanner("")
            current_saves = scanner._scan_saves(saves_dir)
            current_save_names = set([s['name'] for s in current_saves])
            
            # 获取已显示的存档
            displayed_saves = set()
            for i in range(self.save_list_widget.count()):
                item = self.save_list_widget.item(i)
                save_data = item.data(Qt.UserRole)
                if save_data:
                    displayed_saves.add(save_data.get('name', ''))
            
            # 检查是否有新存档
            new_saves = current_save_names - displayed_saves
            if new_saves:
                logger.info(f"检测到新同步的存档: {new_saves}, 刷新列表")
                # 重新加载存档列表
                self.load_game_saves(self.current_game_data)
        except Exception as e:
            logger.debug(f"检查存档失败: {e}")
    
    def update_sync_status(self, syncing=False):
        """更新同步状态显示"""
        try:
            if not hasattr(self, 'sync_status_label'):
                return
            
            if not hasattr(self, 'syncing_folder_id'):
                # 没有在同步
                self.sync_status_label.setVisible(False)
                return
            
            if syncing:
                # 正在同步（蓝色）
                self.sync_status_label.setText("🔄 正在同步...")
                self.sync_status_label.setStyleSheet("""
                    QLabel {
                        font-size: 13px;
                        color: #1890ff;
                        margin-left: 15px;
                        padding: 4px 12px;
                        background: #e6f7ff;
                        border-radius: 4px;
                        border: 1px solid #91d5ff;
                    }
                """)
                self.sync_status_label.setVisible(True)
            else:
                # 空闲状态,检查同步进度
                if hasattr(self, 'syncthing_manager') and self.syncthing_manager:
                    try:
                        # 获取文件夹状态
                        config = self.syncthing_manager.get_config()
                        if config:
                            for folder in config.get('folders', []):
                                if folder['id'] == self.syncing_folder_id:
                                    # 获取文件夹的同步进度
                                    status_resp = self.syncthing_manager.api_request(
                                        f"/rest/db/status?folder={self.syncing_folder_id}"
                                    )
                                    if status_resp:
                                        state = status_resp.get('state', 'unknown')
                                        global_bytes = status_resp.get('globalBytes', 0)
                                        in_sync_bytes = status_resp.get('inSyncBytes', 0)
                                        
                                        if state == 'idle' and global_bytes == in_sync_bytes:
                                            # 完全同步（绿色，无边框）
                                            self.sync_status_label.setText("✅ 同步完成")
                                            self.sync_status_label.setStyleSheet("""
                                                QLabel {
                                                    font-size: 13px;
                                                    color: #07c160;
                                                    margin-left: 15px;
                                                    padding: 4px 12px;
                                                    background: transparent;
                                                    border-radius: 0px;
                                                }
                                            """)
                                            self.sync_status_label.setVisible(True)
                                        elif global_bytes > 0:
                                            # 显示进度（蓝色）
                                            progress = (in_sync_bytes / global_bytes) * 100
                                            # 计算文件大小
                                            def format_bytes(bytes_val):
                                                if bytes_val < 1024:
                                                    return f"{bytes_val}B"
                                                elif bytes_val < 1024*1024:
                                                    return f"{bytes_val/1024:.1f}KB"
                                                elif bytes_val < 1024*1024*1024:
                                                    return f"{bytes_val/(1024*1024):.1f}MB"
                                                else:
                                                    return f"{bytes_val/(1024*1024*1024):.1f}GB"
                                            
                                            size_text = f"{format_bytes(in_sync_bytes)}/{format_bytes(global_bytes)}"
                                            self.sync_status_label.setText(f"🔄 同步中 {progress:.1f}% ({size_text})")
                                            self.sync_status_label.setStyleSheet("""
                                                QLabel {
                                                    font-size: 13px;
                                                    color: #1890ff;
                                                    margin-left: 15px;
                                                    padding: 4px 12px;
                                                    background: #e6f7ff;
                                                    border-radius: 4px;
                                                    border: 1px solid #91d5ff;
                                                }
                                            """)
                                            self.sync_status_label.setVisible(True)
                                        else:
                                            self.sync_status_label.setVisible(False)
                                    break
                    except Exception as e:
                        logger.debug(f"获取同步状态失败: {e}")
                        self.sync_status_label.setVisible(False)
                else:
                    self.sync_status_label.setVisible(False)
        except Exception as e:
            logger.debug(f"更新同步状态失败: {e}")
    
    def _monitor_sync_status(self):
        """监听同步状态并刷新存档列表"""
        try:
            if not hasattr(self, 'syncing_folder_id'):
                # 没有在同步，停止定时器
                if hasattr(self, 'sync_monitor_timer') and self.sync_monitor_timer.isActive():
                    self.sync_monitor_timer.stop()
                return
            
            # 更新同步状态显示
            self.update_sync_status(syncing=False)
            
            # 删除定时刷新，改用Syncthing事件触发
            # if hasattr(self, 'current_game_data'):
            #     logger.debug("定时刷新存档列表...")
            #     self.load_game_saves(self.current_game_data)
                
        except Exception as e:
            logger.debug(f"监听同步状态失败: {e}")
    
    def auto_refresh_saves(self):
        """自动刷新存档列表(检测新同步的存档)"""
        # 只有在游戏管理页面且选中了游戏时才刷新
        if self.current_page != "game" or not hasattr(self, 'current_game_data'):
            return
        
        try:
            import os
            from ui.minecraft.version_scanner import MinecraftVersionScanner
            
            saves_dir = self.current_game_data.get('save_path', '')
            if not saves_dir or not os.path.exists(saves_dir):
                logger.debug(f"存档目录不存在或未设置: {saves_dir}")
                return
            
            # 扫描当前存档
            scanner = MinecraftVersionScanner("")
            current_saves = scanner._scan_saves(saves_dir)
            current_save_names = set([s['name'] for s in current_saves])
            
            logger.debug(f"当前扫描到的存档: {current_save_names}")
            
            # 获取已显示的存档（跳过提示信息）
            displayed_saves = set()
            for i in range(self.save_list_widget.count()):
                item = self.save_list_widget.item(i)
                save_data = item.data(Qt.UserRole)
                if save_data and save_data.get('name'):
                    displayed_saves.add(save_data.get('name'))
            
            logger.debug(f"已显示的存档: {displayed_saves}")
            
            # 检查是否有新存档或显示的是空状态
            new_saves = current_save_names - displayed_saves
            has_empty_hint = self.save_list_widget.count() > 0 and \
                           self.save_list_widget.item(0).text() == "💬 暂无存档"
            
            if new_saves or (has_empty_hint and current_save_names):
                logger.info(f"检测到新存档: {new_saves} 或空状态需要刷新，重新加载列表")
                # 重新加载存档列表
                self.load_game_saves(self.current_game_data)
        except Exception as e:
            logger.error(f"自动刷新存档失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # ==================== 窗口事件 ====================
    
    def mousePressEvent(self, event):
        """鼠标按下（拖动窗口）"""
        if event.button() == Qt.LeftButton and event.pos().y() <= 40:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动"""
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        self.drag_position = None
    
    def closeEvent(self, event):
        """关闭窗口 - 立即关闭窗口，后台线程处理清理工作"""
        logger.info("正在关闭应用...")
        
        # 先隐藏窗口（给用户立即响应的感觉）
        self.hide()
        
        # 在非daemon线程中处理清理工作，确保完成后才退出
        import threading
        cleanup_thread = threading.Thread(target=self._cleanup_resources_and_quit, daemon=False)
        cleanup_thread.start()
        
        # 忽略关闭事件，等待清理完成后再真正退出
        event.ignore()
    
    def _cleanup_resources(self):
        """后台清理资源"""
        try:
            # 如果是主机，广播下线消息
            try:
                if hasattr(self, 'game_launcher') and self.game_launcher and hasattr(self.game_launcher, 'game_process'):
                    if self.game_launcher.game_process and self.game_launcher.game_process.poll() is None:
                        # 游戏还在运行，广播下线
                        if hasattr(self, 'mqtt_manager') and self.mqtt_manager and self.mqtt_manager.connected:
                            self.mqtt_manager.publish("host_offline", {
                                "player": "Host",
                                "reason": "application_closed"
                            })
                            logger.info("已广播主机下线消息")
            except Exception as e:
                logger.error(f"广播下线消息失败: {e}")
            
            # 停止所有正在同步的游戏
            try:
                if hasattr(self, 'config_data'):
                    game_list = self.config_data.get("game_list", [])
                    stopped_count = 0
                    
                    for game in game_list:
                        if game.get('is_syncing', False):
                            folder_id = game.get('sync_folder_id')
                            if folder_id and hasattr(self, 'syncthing_manager') and self.syncthing_manager:
                                # 暂停文件夹同步
                                config = self.syncthing_manager.get_config()
                                if config:
                                    for folder in config.get('folders', []):
                                        if folder['id'] == folder_id:
                                            folder['paused'] = True
                                            stopped_count += 1
                                            break
                                    if stopped_count > 0:
                                        self.syncthing_manager.set_config(config)
                            
                            # 更新配置中的状态
                            game['is_syncing'] = False
                    
                    # 保存配置
                    if stopped_count > 0:
                        from config import ConfigCache
                        ConfigCache.save(self.config_data)
                        logger.info(f"已停止 {stopped_count} 个游戏的同步")
            except Exception as e:
                logger.error(f"停止同步失败: {e}")
            
            # 停止线程
            try:
                if hasattr(self, 'connect_thread') and self.connect_thread and self.connect_thread.isRunning():
                    self.connect_thread.quit()
                    self.connect_thread.wait(timeout=2000)  # 最多等待2秒
                
                if hasattr(self, 'scan_thread') and self.scan_thread and self.scan_thread.isRunning():
                    self.scan_thread.quit()
                    self.scan_thread.wait(timeout=2000)
            except Exception as e:
                logger.error(f"停止线程失败: {e}")
            
            # 清理资源
            try:
                if hasattr(self, 'controller'):
                    self.controller.cleanup()
            except Exception as e:
                logger.error(f"清理资源失败: {e}")
            
            logger.info("后台清理完成")
            
        except Exception as e:
            logger.error(f"后台清理异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _cleanup_resources_and_quit(self):
        """清理资源并退出应用"""
        try:
            # 执行清理
            self._cleanup_resources()
            
            # 清理完成后，真正退出应用
            from PyQt5.QtWidgets import QApplication
            logger.info("清理完成，正在退出应用...")
            QApplication.quit()
            
        except Exception as e:
            logger.error(f"清理并退出失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 即使失败也要退出
            from PyQt5.QtWidgets import QApplication
            QApplication.quit()
    
    def create_save_info_card(self):
        """创建存档信息卡片"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: #f7f7f7;
                border-radius: 6px;
                padding: 15px 20px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        
        title = QLabel("💾 存档信息")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #2c2c2c;")
        layout.addWidget(title)
        
        self.save_name_label = QLabel("存档名称: -")
        self.save_name_label.setStyleSheet("font-size: 13px; color: #2c2c2c;")
        layout.addWidget(self.save_name_label)
        
        self.save_mode_label = QLabel("游戏模式: -")
        self.save_mode_label.setStyleSheet("font-size: 12px; color: #666666;")
        layout.addWidget(self.save_mode_label)
        
        self.save_difficulty_label = QLabel("难度: -")
        self.save_difficulty_label.setStyleSheet("font-size: 12px; color: #666666;")
        layout.addWidget(self.save_difficulty_label)
        
        self.save_days_label = QLabel("游戏天数: -")
        self.save_days_label.setStyleSheet("font-size: 12px; color: #666666;")
        layout.addWidget(self.save_days_label)
        
        return card
    
    def create_player_info_card(self):
        """创建玩家信息卡片"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: #f7f7f7;
                border-radius: 6px;
                padding: 15px 20px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        
        title = QLabel("👥 玩家列表")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #2c2c2c;")
        layout.addWidget(title)
        
        self.player_list_widget = QListWidget()
        self.player_list_widget.setFixedHeight(150)
        self.player_list_widget.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #f5f5f5;
            }
        """)
        layout.addWidget(self.player_list_widget)
        
        return card
    
    def on_save_selected(self):
        """点击存档时显示详情"""
        current_item = self.save_list_widget.currentItem()
        if not current_item:
            return
        
        save_data = current_item.data(Qt.UserRole)
        if not save_data:
            return
        
        # 显示存档详情卡片
        self.empty_detail_widget.setVisible(False)
        self.save_info_card.setVisible(True)
        self.player_info_card.setVisible(True)
        
        # 更新详情标题
        save_name = save_data.get('name', '未知')
        self.detail_title_label.setText(f"💾 {save_name}")
        
        # 更新存档信息
        self.save_name_label.setText(f"存档名称: {save_name}")
        
        save_info = save_data.get('info', {})
        game_mode = save_info.get('game_mode', '-')
        difficulty = save_info.get('difficulty', '-')
        days = save_info.get('day_time', 0)
        
        self.save_mode_label.setText(f"游戏模式: {game_mode}")
        self.save_difficulty_label.setText(f"难度: {difficulty}")
        self.save_days_label.setText(f"游戏天数: {days}天")
        
        # 加载玩家列表
        self.load_save_players(save_data)
        
        # 显示底部操作按钮（仅显示选择用户和启动游戏）
        self.select_user_btn.setVisible(True)
        self.launch_game_btn.setVisible(True)
        # 启动游戏按钮默认禁用，需要选择用户后才启用
        self.launch_game_btn.setEnabled(False)
        # 同步按钮已经在选择游戏时显示，这里不再重复设置
    
    def load_game_saves(self, game_data):
        """加载游戏的存档列表"""
        # 保存当前选中的存档名
        selected_save_name = None
        current_item = self.save_list_widget.currentItem()
        if current_item:
            save_data = current_item.data(Qt.UserRole)
            if save_data:
                selected_save_name = save_data.get('name')
        
        self.save_list_widget.clear()
        
        if game_data.get('type') != 'minecraft':
            return
        
        try:
            from ui.minecraft.version_scanner import MinecraftVersionScanner
            import os
            
            saves_dir = game_data.get('save_path', '')
            if not saves_dir or not os.path.exists(saves_dir):
                logger.warning(f"存档目录不存在: {saves_dir}")
                return
            
            # 扫描存档
            scanner = MinecraftVersionScanner("")
            saves = scanner._scan_saves(saves_dir)
            
            # 如果没有存档,显示提示
            if not saves:
                item = QListWidgetItem("💬 暂无存档")
                item.setForeground(QColor("#999999"))
                item.setFlags(Qt.ItemIsEnabled)  # 不可选中
                self.save_list_widget.addItem(item)
                
                hint_item = QListWidgetItem("点击「启动同步」")
                hint_item.setForeground(QColor("#666666"))
                hint_item.setFlags(Qt.ItemIsEnabled)
                self.save_list_widget.addItem(hint_item)
                
                hint_item2 = QListWidgetItem("同步其他玩家的存档")
                hint_item2.setForeground(QColor("#666666"))
                hint_item2.setFlags(Qt.ItemIsEnabled)
                self.save_list_widget.addItem(hint_item2)
                logger.info("暂无存档,显示提示信息")
                return
            
            # 显示所有存档(默认全部解锁)
            for save in saves:
                save_name = save['name']
                item = QListWidgetItem()
                item.setText(f"💾 {save_name}")
                item.setForeground(QColor("#2c2c2c"))
                item.setBackground(QColor(255, 255, 255, 0))  # 透明背景
                item.setData(Qt.UserRole, save)
                self.save_list_widget.addItem(item)
            
            logger.info(f"加载了 {len(saves)} 个存档")
            
            # 恢复之前选中的存档
            if selected_save_name:
                for i in range(self.save_list_widget.count()):
                    item = self.save_list_widget.item(i)
                    save_data = item.data(Qt.UserRole)
                    if save_data and save_data.get('name') == selected_save_name:
                        self.save_list_widget.setCurrentItem(item)
                        logger.debug(f"恢复选中的存档: {selected_save_name}")
                        break
            
        except Exception as e:
            logger.error(f"加载存档列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def show_empty_detail(self):
        """显示空状态详情"""
        self.empty_detail_widget.setVisible(True)
        self.save_info_card.setVisible(False)
        self.player_info_card.setVisible(False)
        self.detail_title_label.setText("存档详情")
        
        # 清空详情时隐藏启动游戏和选择用户按钮
        self.select_user_btn.setVisible(False)
        self.launch_game_btn.setVisible(False)
    
    def load_save_players(self, save_data):
        """加载存档的玩家列表"""
        self.player_list_widget.clear()
        
        try:
            from ui.minecraft.version_scanner import MinecraftVersionScanner
            import os
            
            save_path = save_data.get('path', '')
            if not save_path or not os.path.exists(save_path):
                return
            
            scanner = MinecraftVersionScanner("")
            players = scanner.get_save_players(save_path)
            
            for player in players:
                player_name = player.get('name', player.get('uuid', '未知')[:8])
                item = QListWidgetItem(f"👤 {player_name}")
                self.player_list_widget.addItem(item)
            
            if not players:
                item = QListWidgetItem("⚠️ 暂无玩家数据")
                item.setForeground(QColor("#999999"))
                self.player_list_widget.addItem(item)
                
        except Exception as e:
            logger.error(f"加载玩家列表失败: {e}")
    
    def save_game_config(self):
        """保存游戏配置"""
        try:
            config_data = ConfigCache.load()
            if 'game_list' in config_data:
                for i, game in enumerate(config_data['game_list']):
                    if game.get('name') == self.current_game_data.get('name'):
                        config_data['game_list'][i] = self.current_game_data
                        break
                ConfigCache.save(config_data)
                logger.info("配置已保存")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def start_save_sync(self):
        """启动/结束存档同步"""
        if not hasattr(self, 'current_game_data'):
            MessageBox.show_warning(self, "提示", "请先选择游戏!")
            return
        
        if not self.is_connected:
            MessageBox.show_warning(self, "提示", "请先连接到网络!")
            return
        
        # 检查是否正在同步
        is_syncing = hasattr(self, 'syncing_game_name') and self.syncing_game_name == self.current_game_data.get('name')
        
        if is_syncing:
            # 结束同步
            self.stop_save_sync()
        else:
            # 启动同步
            self.do_start_sync()
    
    def do_start_sync(self):
        """执行同步启动逻辑"""
        try:
            game_name = self.current_game_data.get('name')
            game_type = self.current_game_data.get('type')
            version = self.current_game_data.get('version')
            save_path = self.current_game_data.get('save_path')
            
            if not save_path:
                MessageBox.show_error(self, "错误", "无法获取存档路径")
                return
            
            logger.info(f"启动同步: 游戏={game_name}, 版本={version}, 路径={save_path}")
            
            # 生成文件夹ID
            folder_id = f"game-{game_type}-{version}".replace(' ', '-').replace('.', '-')
            folder_label = f"{game_name} - 存档同步"
            
            # 配置同步文件夹(使用懒同步,30秒延迟,默认暂停)
            if not self.syncthing_manager.setup_sync_folder(
                folder_id=folder_id,
                folder_path=save_path,
                folder_label=folder_label,
                watcher_delay=30  # 文件静默30秒后才同步
            ):
                MessageBox.show_error(self, "错误", "配置同步文件夹失败")
                return
            
            # 获取已连接的设备列表
            connections = self.syncthing_manager.get_connections()
            device_ids = []
            
            if connections and connections.get('connections'):
                for dev_id, conn_info in connections['connections'].items():
                    if conn_info.get('connected') and dev_id != self.syncthing_manager.device_id:
                        device_ids.append(dev_id)
            
            # 添加设备到文件夹
            if device_ids:
                for dev_id in device_ids:
                    self.syncthing_manager.add_device_to_folder(folder_id, dev_id)
                logger.info(f"已添加 {len(device_ids)} 个设备到同步文件夹")
            else:
                logger.info("当前没有其他设备连接，等待设备加入后将自动添加到此文件夹")
            
            # 恢复文件夹同步（启动同步）
            if not self.syncthing_manager.resume_folder(folder_id):
                MessageBox.show_error(self, "错误", "启动同步失败")
                return
            
            # 标记为正在同步
            self.syncing_game_name = game_name
            self.syncing_folder_id = folder_id
            
            # 显示同步状态
            self.update_sync_status(syncing=False)  # 初始化为空闲状态
            
            # 启动定时器监听同步状态并刷新存档列表
            if not hasattr(self, 'sync_monitor_timer'):
                self.sync_monitor_timer = QTimer()
                self.sync_monitor_timer.timeout.connect(self._monitor_sync_status)
            
            self.sync_monitor_timer.start(3000)  # 每3秒检查一次
            logger.info("已启动同步状态监听")
            
            # 更新按钮状态
            self.start_sync_btn.setText("⏸️ 结束同步")
            self.start_sync_btn.setStyleSheet("""
                QPushButton {
                    background: #fa5151;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #e84545;
                }
            """)
            
            # 显示成功提示
            MessageBox.show_info(self, "成功", "已开始同步所有存档!")
            logger.info("已开始同步所有存档")
            
        except Exception as e:
            logger.error(f"启动同步失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            MessageBox.show_error(self, "错误", f"启动同步失败\n\n{str(e)}")
    
    def stop_save_sync(self):
        """结束存档同步"""
        try:
            # 停止同步状态监听定时器
            if hasattr(self, 'sync_monitor_timer') and self.sync_monitor_timer.isActive():
                self.sync_monitor_timer.stop()
                logger.info("已停止同步状态监听")
            
            if hasattr(self, 'syncing_folder_id'):
                # 暂停文件夹同步（不移除，保留配置）
                self.syncthing_manager.pause_folder(self.syncing_folder_id)
                logger.info(f"已暂停同步文件夹: {self.syncing_folder_id}")
                
                del self.syncing_folder_id
            
            if hasattr(self, 'syncing_game_name'):
                del self.syncing_game_name
            
            # 隐藏同步状态
            if hasattr(self, 'sync_status_label'):
                self.sync_status_label.setVisible(False)
            
            # 恢复按钮状态
            self.start_sync_btn.setText("🚀 启动同步")
            self.start_sync_btn.setStyleSheet("""
                QPushButton {
                    background: #07c160;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #06ae56;
                }
                QPushButton:disabled {
                    background: #d0d0d0;
                    color: #999999;
                }
            """)
            
            MessageBox.show_info(self, "成功", "已暂停同步")
            
        except Exception as e:
            logger.error(f"结束同步失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # ==================== 游戏启动功能 ====================
    
    def select_user_account(self):
        """选择用户账号"""
        if not hasattr(self, 'current_game_data'):
            MessageBox.show_warning(self, "提示", "请先选择游戏!")
            return
        
        try:
            # 获取启动器路径
            launcher_path = self.current_game_data.get('launcher_path')
            
            # 如果没有launcher_path，尝试从存档路径推断
            if not launcher_path:
                save_path = self.current_game_data.get('save_path', '')
                if save_path:
                    launcher_path = self._detect_launcher_from_save_path(save_path)
                    if launcher_path:
                        # 保存到配置中
                        self.current_game_data['launcher_path'] = launcher_path
                        self.save_game_config()
                        logger.info(f"自动检测并保存启动器路径: {launcher_path}")
            
            if not launcher_path:
                MessageBox.show_warning(self, "提示", "未找到启动器路径，无法读取账号信息")
                return
            
            # 打开账号选择对话框
            from ui.components.dialogs.account_selector import AccountSelectorDialog
            dialog = AccountSelectorDialog(launcher_path, self)
            
            if dialog.exec_() == QDialog.Accepted:
                selected_account = dialog.get_selected_account()
                if selected_account:
                    # 保存选中的账号
                    self.selected_user_account = selected_account
                    
                    # 显示选中的账号
                    player_name = selected_account.get('player_name', 'Unknown')
                    account_type = selected_account.get('account_type', 'offline')
                    type_text = {
                        'offline': '离线',
                        'microsoft': 'Microsoft',
                        'mojang': 'Mojang',
                        'authlib': 'AuthLib'
                    }.get(account_type, '未知')
                    
                    # 更新按钮文字
                    self.select_user_btn.setText(f"👤 {player_name} ({type_text})")
                    
                    # 启用启动游戏按钮
                    self.launch_game_btn.setEnabled(True)
                    
                    # 如果当前有服务器信息（加入游戏模式），也启用按钮
                    if hasattr(self, 'server_info') and self.server_info:
                        self.launch_game_btn.setEnabled(True)
                    
                    MessageBox.show_info(self, "成功", f"已选择账号: {player_name} ({type_text})")
                    logger.info(f"用户选择账号: {player_name} ({account_type})")
        
        except Exception as e:
            logger.error(f"选择用户失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            MessageBox.show_error(self, "错误", f"选择用户失败\n\n{str(e)}")
    
    def launch_game(self):
        """启动游戏并自动开启局域网"""
        if not hasattr(self, 'current_game_data'):
            MessageBox.show_warning(self, "提示", "请先选择游戏!")
            return
        
        if not self.is_connected:
            MessageBox.show_warning(self, "提示", "请先连接到网络!")
            return
        
        # 按钮变灰
        self.launch_game_btn.setEnabled(False)
        self.launch_game_btn.setText("🕒 启动中...")
        
        # 在主线程中获取world_name（避免子线程访问UI）
        world_name = None
        current_item = self.save_list_widget.currentItem()
        if current_item:
            save_data = current_item.data(Qt.UserRole)
            if save_data:
                world_name = save_data.get('name')
                logger.info(f"将自动进入世界: {world_name}")
        else:
            logger.warning("未选中存档，不自动进入世界")
        
        # 在子线程中启动游戏，避免阻塞主线程
        import threading
        threading.Thread(target=self._launch_game_thread, args=(world_name,), daemon=True).start()
    
    def _launch_game_thread(self, world_name=None):
        """子线程中启动游戏
        
        Args:
            world_name: 世界名称（从主线程传递）
        """
        try:
            from managers.game_launcher import GameLauncher
            
            game_name = self.current_game_data.get('name')
            version = self.current_game_data.get('version')
            save_path = self.current_game_data.get('save_path', '')
            
            # 从存档路径推断 Minecraft 目录
            minecraft_dir = self._get_minecraft_dir_from_save_path(save_path)
            
            if not minecraft_dir:
                # 使用线程安全的方式更新UI
                QMetaObject.invokeMethod(self.launch_game_btn, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
                QMetaObject.invokeMethod(self.launch_game_btn, "setText", Qt.QueuedConnection, Q_ARG("QString", "🎮 启动游戏"))
                QMetaObject.invokeMethod(self, "_show_error_safe", Qt.QueuedConnection, Q_ARG("QString", "未找到 Minecraft 目录！"))
                return
            
            logger.info(f"Minecraft 目录: {minecraft_dir}")
            logger.info(f"游戏版本: {version}")
            
            # 创建游戏启动器
            self.game_launcher = GameLauncher(minecraft_dir, version)
            
            # 1. 广播游戏启动中
            if self.mqtt_manager and self.mqtt_manager.connected:
                self.mqtt_manager.publish("game_starting", {
                    "game_name": game_name,
                    "version": version,
                    "player": "Host"
                })
            
            # 2. 直接启动游戏（不依赖启动器）
            logger.info(f"启动游戏: {game_name}, 版本: {version}")
            
            # world_name已从主线程传递，不再从UI获取
            if world_name:
                logger.info(f"将自动进入世界: {world_name}")
            
            # 检查是否选择了用户账号
            if hasattr(self, 'selected_user_account') and self.selected_user_account:
                # 使用选中的账号启动
                account = self.selected_user_account
                player_name = account.get('player_name')
                uuid = account.get('uuid')
                access_token = account.get('access_token')
                account_type = account.get('account_type', 'offline')
                use_offline = (account_type == 'offline')
                
                logger.info(f"使用选中的账号: {player_name} ({account_type})")
                logger.info(f"UUID: {uuid}")
                logger.info(f"User Type: {'offline' if use_offline else account_type}")
                
                success = self.game_launcher.launch_minecraft(
                    player_name=player_name,
                    use_offline=use_offline,
                    mojang_uuid=uuid,
                    mojang_token=access_token,
                    world_name=world_name
                )
            else:
                # 使用默认账号（从启动器自动读取）
                launcher_path = self.current_game_data.get('launcher_path')
                logger.info(f"使用启动器路径: {launcher_path}")
                success = self.game_launcher.launch_minecraft(
                    launcher_path=launcher_path,
                    world_name=world_name
                )
            
            if not success:
                # 使用线程安全的方式更新UI
                QMetaObject.invokeMethod(self.launch_game_btn, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
                QMetaObject.invokeMethod(self.launch_game_btn, "setText", Qt.QueuedConnection, Q_ARG("QString", "🎮 启动游戏"))
                QMetaObject.invokeMethod(self, "_show_error_safe", Qt.QueuedConnection, Q_ARG("QString", "游戏启动失败"))
                return
            
            # 3. 直接启动自动开启局域网线程（不需要窗口检测）
            logger.info("游戏进程已启动，开始自动开启局域网线程")
            import threading
            threading.Thread(target=self._auto_open_lan_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"启动游戏失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 使用线程安全的方式更新UI
            QMetaObject.invokeMethod(self.launch_game_btn, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
            QMetaObject.invokeMethod(self.launch_game_btn, "setText", Qt.QueuedConnection, Q_ARG("QString", "🎮 启动游戏"))
            QMetaObject.invokeMethod(self, "_show_error_safe", Qt.QueuedConnection, Q_ARG("QString", f"启动游戏失败\n\n{str(e)}"))
    
    def _get_minecraft_dir_from_save_path(self, save_path):
        """
        从存档路径推断 Minecraft 根目录
        
        Args:
            save_path: 存档路径
            
        Returns:
            str: .minecraft 根目录,找不到返回None
        """
        try:
            from pathlib import Path
            save_path = Path(save_path)
            
            # 存档路径格式 (版本隔离):
            # xxx/HMCL/.minecraft/versions/<版本>/saves
            
            # 向上查找 .minecraft 目录
            current = save_path
            
            for i in range(8):
                current = current.parent
                logger.debug(f"查找第{i+1}层: {current}")
                
                # 检查是否是 .minecraft 目录
                if current.name == '.minecraft':
                    logger.info(f"找到 .minecraft 目录: {current}")
                    return str(current)
                
                # 或者检查子目录中是否有 .minecraft
                minecraft_dir = current / '.minecraft'
                if minecraft_dir.exists() and minecraft_dir.is_dir():
                    logger.info(f"找到 .minecraft 目录: {minecraft_dir}")
                    return str(minecraft_dir)
            
            logger.warning(f"未找到 .minecraft 目录: {save_path}")
            return None
            
        except Exception as e:
            logger.error(f"推断 Minecraft 目录失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _detect_launcher_from_save_path(self, save_path):
        """
        从存档路径反推启动器路径
        
        Args:
            save_path: 存档路径
            
        Returns:
            str: 启动器路径,找不到返回None
        """
        try:
            from pathlib import Path
            save_path = Path(save_path)
            
            # 存档路径格式:
            # PCL2: xxx/PCL2/.minecraft/versions/<版本>/saves  或  xxx/PCL2/.minecraft/saves
            # HMCL: xxx/HMCL/.minecraft/versions/<版本>/saves  或  xxx/HMCL/.minecraft/saves
            
            # 向上查找目录
            current = save_path
            
            # 最多向上找8层(增加容错)
            for i in range(8):
                current = current.parent
                logger.info(f"查找第{i+1}层: {current}")
                
                # 查找PCL2.exe
                pcl2_path = current / 'PCL2.exe'
                if pcl2_path.exists():
                    logger.info(f"检测到PCL2启动器: {pcl2_path}")
                    return str(pcl2_path)
                
                # 查找HMCL.exe
                hmcl_exe_path = current / 'HMCL.exe'
                if hmcl_exe_path.exists():
                    logger.info(f"检测到HMCL启动器(exe): {hmcl_exe_path}")
                    return str(hmcl_exe_path)
                
                # 查找HMCL*.exe
                hmcl_exe_files = list(current.glob('HMCL*.exe'))
                if hmcl_exe_files:
                    logger.info(f"检测到HMCL启动器(exe): {hmcl_exe_files[0]}")
                    return str(hmcl_exe_files[0])
                
                # 查找HMCL*.jar
                hmcl_files = list(current.glob('HMCL*.jar'))
                if hmcl_files:
                    logger.info(f"检测到HMCL启动器(jar): {hmcl_files[0]}")
                    return str(hmcl_files[0])
                
                # 查找所有jar/exe文件,检查是否包含hmcl
                jar_files = list(current.glob('*.jar'))
                exe_files = list(current.glob('*.exe'))
                all_files = jar_files + exe_files
                logger.info(f"找到{len(all_files)}个jar/exe文件: {[f.name for f in all_files]}")
                
                for file in all_files:
                    if 'hmcl' in file.name.lower():
                        logger.info(f"检测到HMCL启动器: {file}")
                        return str(file)
            
            logger.warning(f"未找到启动器: {save_path}")
            return None
            
        except Exception as e:
            logger.error(f"检测启动器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _auto_open_lan_thread(self):
        """自动开启局域网线程: 监听游戏日志等待进入世界后立即执行"""
        try:
            import time
            logger.info("自动开启局域网线程: 监听游戏日志等待进入世界...")
            
            # 检查游戏进程是否还在运行
            if not hasattr(self, 'game_launcher') or not self.game_launcher:
                logger.error("游戏启动器不存在")
                return
            
            if not hasattr(self.game_launcher, 'game_process') or not self.game_launcher.game_process:
                logger.error("游戏进程不存在")
                return
            
            # 监听日志，等待进入世界
            if not self.game_launcher.wait_for_world_loaded(timeout=60):
                # 检查游戏是否崩溃
                if self.game_launcher.game_process.poll() is not None:
                    logger.error(f"游戏进程已退出，退出码: {self.game_launcher.game_process.poll()}")
                    self.update_button_signal.emit(True, "❌ 游戏启动失败")
                    return
                
                logger.warning("未检测到进入世界，跳过自动开启局域网")
                self.update_button_signal.emit(True, "⚠️ 请手动开启局域网")
                return
            
            logger.info("自动开启局域网线程: 检测到进入世界，开始查找游戏窗口")
            
            # 通过PID查找游戏窗口（10秒足够）
            if not self.game_launcher.wait_for_game_window(timeout=10):
                logger.warning("未找到游戏窗口，跳过自动开启局域网")
                self.update_button_signal.emit(True, "⚠️ 请手动开启局域网")
                return
            
            logger.info("自动开启局域网线程: 找到游戏窗口，等待1秒后发送指令")
            
            # 等待2秒确保游戏界面完全加载，可以接收键盘输入
            time.sleep(2)
            
            # 自动开启局域网（已包含端口检测）
            logger.info("自动开启局域网线程: 尝试自动开启局域网...")
            success = self.game_launcher.auto_open_lan()
            
            if success and self.game_launcher.lan_port:
                port = self.game_launcher.lan_port
                logger.info(f"局域网已成功开启，端口: {port}")
                # 获取本机IP
                virtual_ip = self.controller.easytier.virtual_ip
                
                # 广播服务器就绪
                if self.mqtt_manager and self.mqtt_manager.connected:
                    game_name = self.current_game_data.get('name')
                    version = self.current_game_data.get('version')
                    
                    self.mqtt_manager.publish("server_ready", {
                        "game_name": game_name,
                        "version": version,
                        "server_ip": virtual_ip,
                        "server_port": port,
                        "player": "Host"
                    })
                    
                    logger.info(f"已广播服务器信息: {virtual_ip}:{port}")
                
                # 更新按钮为“服务器运行中”
                self.update_button_signal.emit(False, f"✅ 服务器: {virtual_ip}:{port}")
            else:
                logger.warning("未获取到端口,可能需要手动开启局域网")
                self.update_button_signal.emit(True, "⚠️ 请手动开启局域网")
                
        except Exception as e:
            logger.error(f"自动开启局域网失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _show_error_safe(self, message):
        """线程安全的错误提示"""
        MessageBox.show_error(self, "错误", message)
    
    def _update_button_slot(self, enabled, text):
        """更新按钮状态（槽函数，在主线程中执行）"""
        self.launch_game_btn.setEnabled(enabled)
        self.launch_game_btn.setText(text)
    
    def on_mqtt_message(self, message_type, data):
        """
        MQTT消息回调
        
        Args:
            message_type: 消息类型
            data: 消息数据
        """
        try:
            logger.info(f"收到MQTT消息: {message_type}")
            
            if message_type == "device/online":
                # 收到设备上线消息，刷新客户端列表
                device_id = data.get('device_id', '')
                virtual_ip = data.get('virtual_ip', '')
                hostname = data.get('hostname', '')
                logger.info(f"设备上线: {hostname} ({virtual_ip})")
                
                # 刷新客户端列表
                if self.is_connected:
                    self.update_clients_list()
                    logger.info("已刷新客户端列表")
                
            elif message_type == "game_starting":
                # 有人开始启动游戏
                game_name = data.get('game_name', 'Unknown')
                player = data.get('player', 'Unknown')
                logger.info(f"{player} 正在启动 {game_name}")
                
                # 禁用启动按钮，显示等待状态
                self.launch_game_btn.setEnabled(False)
                self.launch_game_btn.setText(f"⏳ {player}正在启动...")
                self.launch_game_btn.setStyleSheet("""
                    QPushButton {
                        background: #d9d9d9;
                        color: #8c8c8c;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 16px;
                        font-size: 13px;
                        font-weight: 500;
                        margin-right: 10px;
                    }
                """)
                
            elif message_type == "server_ready":
                # 服务器就绪
                self.server_info = data
                game_name = data.get('game_name', 'Unknown')
                server_ip = data.get('server_ip', '')
                server_port = data.get('server_port', 0)
                player = data.get('player', 'Unknown')
                
                logger.info(f"{player} 的服务器已就绪: {server_ip}:{server_port}")
                
                # 将启动游戏按钮变为加入游戏
                # 只有选择了用户后才启用按钮
                if hasattr(self, 'selected_user_account') and self.selected_user_account:
                    self.launch_game_btn.setEnabled(True)
                else:
                    self.launch_game_btn.setEnabled(False)
                
                self.launch_game_btn.setText(f"🚀 加入游戏")
                self.launch_game_btn.setStyleSheet("""
                    QPushButton {
                        background: #52c41a;
                        color: #ffffff;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 16px;
                        font-size: 13px;
                        font-weight: 500;
                        margin-right: 10px;
                    }
                    QPushButton:hover {
                        background: #73d13d;
                    }
                    QPushButton:disabled {
                        background: #d9d9d9;
                        color: #8c8c8c;
                    }
                """)
                # 更改点击事件
                self.launch_game_btn.clicked.disconnect()
                self.launch_game_btn.clicked.connect(self.join_server)
            
            elif message_type == "host_offline":
                # 主机掉线
                player = data.get('player', 'Unknown')
                logger.info(f"{player} 已下线")
                
                # 恢复按钮为启动游戏状态
                self.server_info = None
                # 恢复为禁用状态，需要选择用户后才启用
                if hasattr(self, 'selected_user_account') and self.selected_user_account:
                    self.launch_game_btn.setEnabled(True)
                else:
                    self.launch_game_btn.setEnabled(False)
                
                self.launch_game_btn.setText("🎮 启动游戏")
                self.launch_game_btn.setStyleSheet("""
                    QPushButton {
                        background: #1890ff;
                        color: #ffffff;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 16px;
                        font-size: 13px;
                        font-weight: 500;
                        margin-right: 10px;
                    }
                    QPushButton:hover {
                        background: #40a9ff;
                    }
                    QPushButton:disabled {
                        background: #d9d9d9;
                        color: #8c8c8c;
                    }
                """)
                # 恢复点击事件
                try:
                    self.launch_game_btn.clicked.disconnect()
                except:
                    pass
                self.launch_game_btn.clicked.connect(self.launch_game)
                
        except Exception as e:
            logger.error(f"MQTT消息处理失败: {e}")
    
    def join_server(self):
        """加入服务器"""
        if not self.server_info:
            MessageBox.show_warning(self, "提示", "没有可用的服务器!")
            return
        
        try:
            server_ip = self.server_info.get('server_ip', '')
            server_port = self.server_info.get('server_port', 0)
            game_name = self.server_info.get('game_name', 'Unknown')
            
            logger.info(f"=========== 开始加入服务器 ===========")
            logger.info(f"服务器信息: {self.server_info}")
            logger.info(f"目标服务器: {server_ip}:{server_port}")
            logger.info(f"游戏名称: {game_name}")
            logger.info(f"======================================")
            
            # 启动游戏并自动连接
            from managers.game_launcher import GameLauncher
            
            save_path = self.current_game_data.get('save_path', '')
            version = self.current_game_data.get('version')
            
            # 从存档路径推断 Minecraft 目录
            minecraft_dir = self._get_minecraft_dir_from_save_path(save_path)
            
            if not minecraft_dir:
                MessageBox.show_error(self, "错误", "未找到 Minecraft 目录！")
                return
            
            # 创建游戏启动器
            launcher = GameLauncher(minecraft_dir, version)
            
            # 使用选中的账号
            if hasattr(self, 'selected_user_account') and self.selected_user_account:
                account = self.selected_user_account
                player_name = account.get('player_name')
                uuid = account.get('uuid')
                access_token = account.get('access_token')
                account_type = account.get('account_type', 'offline')
                use_offline = (account_type == 'offline')
                
                success = launcher.launch_minecraft(
                    player_name=player_name,
                    use_offline=use_offline,
                    mojang_uuid=uuid,
                    mojang_token=access_token,
                    server_ip=server_ip,
                    server_port=server_port
                )
            else:
                # 使用默认账号
                launcher_path = self.current_game_data.get('launcher_path')
                success = launcher.launch_minecraft(
                    launcher_path=launcher_path,
                    server_ip=server_ip,
                    server_port=server_port
                )
            
            if success:
                MessageBox.show_info(self, "成功", f"游戏已启动，正在连接到 {game_name}...")
            else:
                MessageBox.show_error(self, "错误", "启动游戏失败")
            
        except Exception as e:
            logger.error(f"加入服务器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            MessageBox.show_error(self, "错误", f"加入服务器失败\n\n{str(e)}")

def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
