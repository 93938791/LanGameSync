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
from ui.components.dialogs import PeerManagerDialog
# TODO: PeerEditDialog, LogDialog 待实现
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
        
        self.title_bar = title_bar
        return title_bar
    
    def create_sidebar(self):
        """创建左侧边栏"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(70)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(0)
        
        # 网络管理按钮
        self.network_btn = QPushButton("🌐")
        self.network_btn.setObjectName("sidebarBtn")
        self.network_btn.setFixedSize(70, 70)
        self.network_btn.setToolTip("网络管理")
        self.network_btn.clicked.connect(lambda: self.switch_page("network"))
        self.network_btn.setStyleSheet("""
            QPushButton {
                background: #2e2e2e;
                color: #ffffff;
                border: none;
                border-left: 3px solid #07c160;
                font-size: 28px;
            }
            QPushButton:hover {
                background: #3e3e3e;
            }
        """)
        layout.addWidget(self.network_btn)
        
        # 游戏管理按钮
        self.game_btn = QPushButton("🎮")
        self.game_btn.setObjectName("sidebarBtnInactive")
        self.game_btn.setFixedSize(70, 70)
        self.game_btn.setToolTip("游戏管理")
        self.game_btn.clicked.connect(lambda: self.switch_page("game"))
        self.game_btn.setStyleSheet("""
            QPushButton {
                background: #2e2e2e;
                color: #888888;
                border: none;
                font-size: 28px;
            }
            QPushButton:hover {
                background: #3e3e3e;
                color: #aaaaaa;
            }
        """)
        layout.addWidget(self.game_btn)
        
        # 设置按钮
        settings_btn = QPushButton("⚙️")
        settings_btn.setObjectName("sidebarBtnInactive")
        settings_btn.setFixedSize(70, 70)
        settings_btn.setToolTip("设置")
        settings_btn.clicked.connect(lambda: MessageBox.show_info(self, "提示", "设置功能开发中..."))
        settings_btn.setStyleSheet("""
            QPushButton {
                background: #2e2e2e;
                color: #888888;
                border: none;
                font-size: 28px;
            }
            QPushButton:hover {
                background: #3e3e3e;
                color: #aaaaaa;
            }
        """)
        
        layout.addStretch()
        layout.addWidget(settings_btn)
        
        return sidebar
    
    def create_network_page(self):
        """创建网络管理页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(15)
        
        # 节点设置区域
        node_group = QGroupBox("节点设置")
        node_group.setObjectName("networkGroup")
        node_layout = QVBoxLayout()
        node_layout.setSpacing(12)
        node_layout.setContentsMargins(20, 20, 20, 20)
        
        # 节点选择
        node_select_layout = QHBoxLayout()
        node_label = QLabel("节点选择:")
        node_label.setMinimumWidth(80)
        node_select_layout.addWidget(node_label)
        
        from PyQt5.QtWidgets import QComboBox
        self.node_combo = QComboBox()
        self.node_combo.addItem("不使用节点")
        # 加载已保存的节点
        peer_list = self.config_data.get("peer_list", [])
        for peer in peer_list:
            self.node_combo.addItem(peer.get("name", "未命名节点"))
        self.node_combo.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                min-height: 20px;
            }
            QComboBox:hover {
                border: 1px solid #b0b0b0;
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
        node_select_layout.addWidget(self.node_combo)
        
        # 配置节点按钮
        config_node_btn = QPushButton("⚙ 配置节点")
        config_node_btn.clicked.connect(self.show_peer_manager)
        config_node_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e0e0e0;
                border: 1px solid #b0b0b0;
            }
        """)
        node_select_layout.addWidget(config_node_btn)
        node_layout.addLayout(node_select_layout)
        
        node_group.setLayout(node_layout)
        layout.addWidget(node_group)
        
        # 网络管理区域
        network_group = QGroupBox("网络管理")
        network_group.setObjectName("networkGroup")
        network_layout = QVBoxLayout()
        network_layout.setSpacing(12)
        network_layout.setContentsMargins(20, 20, 20, 20)
        
        # 房间号输入
        room_layout = QHBoxLayout()
        room_label = QLabel("房间号:")
        room_label.setMinimumWidth(80)
        room_layout.addWidget(room_label)
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("输入房间号")
        # 加载保存的房间号
        network_config = self.config_data.get("network", {})
        if network_config.get("room_name"):
            self.room_input.setText(network_config["room_name"])
        room_layout.addWidget(self.room_input)
        network_layout.addLayout(room_layout)
        
        # 密码输入
        pwd_layout = QHBoxLayout()
        pwd_label = QLabel("密码:")
        pwd_label.setMinimumWidth(80)
        pwd_layout.addWidget(pwd_label)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        # 加载保存的密码
        if network_config.get("password"):
            self.password_input.setText(network_config["password"])
        pwd_layout.addWidget(self.password_input)
        network_layout.addLayout(pwd_layout)
        
        # 连接按钮
        self.connect_btn = QPushButton("🌐 连接到网络")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setMinimumHeight(45)
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self.connect_to_network)
        network_layout.addWidget(self.connect_btn)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # 客户端信息
        clients_group = QGroupBox("📱 已连接的客户端")
        clients_group.setObjectName("clientsGroup")
        clients_layout = QVBoxLayout()
        clients_layout.setContentsMargins(15, 15, 15, 15)
        
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(2)
        self.clients_table.setHorizontalHeaderLabels(["设备名", "虚拟IP"])
        self.clients_table.horizontalHeader().setStretchLastSection(True)
        self.clients_table.verticalHeader().setVisible(False)
        self.clients_table.setAlternatingRowColors(True)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.clients_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: none;
                gridline-color: #f0f0f0;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background: #f8f8f8;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: bold;
                color: #333333;
                font-size: 14px;
            }
            QTableWidget::item:selected {
                background: #e8f5e9;
                color: #333333;
            }
        """)
        clients_layout.addWidget(self.clients_table)
        clients_group.setLayout(clients_layout)
        layout.addWidget(clients_group)
        
        # 状态栏
        self.status_label = QLabel("📡 状态: 未连接")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        return page
    
    def create_game_page(self):
        """创建游戏管理页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(15)
        
        # 标题和操作按钮
        header_layout = QHBoxLayout()
        title_label = QLabel("游戏列表")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333333;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        add_btn = QPushButton("+ 添加游戏")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        header_layout.addWidget(add_btn)
        layout.addLayout(header_layout)
        
        # 游戏列表
        self.game_list = QListWidget()
        self.game_list.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
            }
            QListWidget::item {
                padding: 15px;
                border-radius: 6px;
                margin: 4px;
                border: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f8f8f8;
                border: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background: #e8f5e9;
                border: 1px solid #07c160;
                color: #333333;
            }
        """)
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
            # 更新按钮样式
            self.network_btn.setStyleSheet("""
                QPushButton {
                    background: #2e2e2e;
                    color: #ffffff;
                    border: none;
                    border-left: 3px solid #07c160;
                    font-size: 28px;
                }
                QPushButton:hover {
                    background: #3e3e3e;
                }
            """)
            self.game_btn.setStyleSheet("""
                QPushButton {
                    background: #2e2e2e;
                    color: #888888;
                    border: none;
                    font-size: 28px;
                }
                QPushButton:hover {
                    background: #3e3e3e;
                    color: #aaaaaa;
                }
            """)
        elif page_name == "game":
            self.content_stack.setCurrentIndex(1)
            self.load_game_list()
            # 更新按钮样式
            self.network_btn.setStyleSheet("""
                QPushButton {
                    background: #2e2e2e;
                    color: #888888;
                    border: none;
                    font-size: 28px;
                }
                QPushButton:hover {
                    background: #3e3e3e;
                    color: #aaaaaa;
                }
            """)
            self.game_btn.setStyleSheet("""
                QPushButton {
                    background: #2e2e2e;
                    color: #ffffff;
                    border: none;
                    border-left: 3px solid #07c160;
                    font-size: 28px;
                }
                QPushButton:hover {
                    background: #3e3e3e;
                }
            """)
    
    def connect_to_network(self):
        """连接到网络"""
        room_name = self.room_input.text().strip()
        password = self.password_input.text().strip()
        
        if not room_name or not password:
            MessageBox.show_warning(self, "提示", "请输入房间号和密码")
            return
        
        # 获取选中的节点
        selected_peer = None
        if self.node_combo.currentIndex() > 0:
            peer_list = self.config_data.get("peer_list", [])
            peer_index = self.node_combo.currentIndex() - 1
            if peer_index < len(peer_list):
                selected_peer = peer_list[peer_index].get("peers", "")
        
        # 保存配置
        self.config_data["network"] = {
            "room_name": room_name,
            "password": password
        }
        ConfigCache.save(self.config_data)
        
        # 启动连接线程
        self.connect_thread = ConnectThread(self.controller, room_name, password, selected_peer)
        self.connect_thread.connected.connect(self.on_connected)
        self.connect_thread.progress.connect(self.on_connect_progress)
        self.connect_thread.start()
        
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("⏳ 正在连接...")
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
            # 连接成功后不弹框，按钮变为断开连接
            self.connect_btn.setText("❌ 断开连接")
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.disconnect_network)
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background: #fa5151;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 12px 24px;
                    min-height: 45px;
                }
                QPushButton:hover {
                    background: #e84545;
                }
                QPushButton:pressed {
                    background: #d63838;
                }
            """)
        else:
            self.is_connected = False
            self.status_label.setText("📡 状态: 连接失败")
            self.connect_btn.setText("🌐 连接到网络")
            MessageBox.show_error(self, "错误", f"连接失败\n\n{message}")
    
    def disconnect_network(self):
        """断开网络连接"""
        try:
            # 停止服务
            self.controller.stop()
            
            self.is_connected = False
            self.status_label.setText("📡 状态: 未连接")
            
            # 按钮恢复为连接状态
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.connect_to_network)
            self.connect_btn.setText("🌐 连接到网络")
            self.connect_btn.setObjectName("connectBtn")
            # 恢复原来的样式（通过全局样式表）
            self.connect_btn.setStyleSheet("")
            self.setStyleSheet(self.styleSheet())  # 重新应用全局样式
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
            MessageBox.show_error(self, "错误", f"断开连接失败\n\n{str(e)}")
        """加载游戏列表"""
        # TODO: 从 main_window_v2.py 迁移完整功能
        self.game_list.clear()
        game_list = self.config_data.get("game_list", [])
        
        for game in game_list:
            item = QListWidgetItem(game.get("name", "未命名"))
            self.game_list.addItem(item)
    
    def show_peer_manager(self):
        """显示节点管理对话框"""
        dialog = PeerManagerDialog(self, self.config_data)
        if dialog.exec_() == dialog.Accepted:
            # 重新加载节点列表
            self.node_combo.clear()
            self.node_combo.addItem("不使用节点")
            peer_list = self.config_data.get("peer_list", [])
            for peer in peer_list:
                self.node_combo.addItem(peer.get("name", "未命名节点"))
    
    def monitor_sync_state(self):
        """监控同步状态"""
        if not self.is_connected:
            return
        
        # TODO: 从 main_window_v2.py 迁移监控逻辑
        pass
    
    # ==================== 窗口事件 ====================
    
    def mousePressEvent(self, event):
        """鼠标按下（拖动窗口）"""
        if event.button() == Qt.LeftButton and event.pos().y() <= 50:
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
