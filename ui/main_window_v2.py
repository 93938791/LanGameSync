"""
GUI主窗�?- 美化�?v2.0
毛玻璃简洁风格，完全重构

需求实现：
1. 配置缓存功能
2. 毛玻璃简洁风�?+ 动画
3. 主页：网络管理（连接网络、查看客户信息、自定义昵称�?
4. 样式库引�?
5. 运行日志按钮�?
6. 异步连接避免阻塞
"""
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QLineEdit,
    QMenuBar, QMenu, QAction, QDialog, QTextEdit, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QFrame, QComboBox, QListWidget,
    QListWidgetItem, QStackedWidget, QFileDialog, QInputDialog
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve, QSize, QRect
from PyQt5.QtGui import QFont, QColor
from config import Config
from managers.sync_controller import SyncController
from utils.logger import Logger
from utils.config_cache import ConfigCache
from ui.styles import MODERN_STYLE
from ui.components import MessageBox
from ui.minecraft import MinecraftLauncherHandler, MinecraftPathResolver
from ui.threads import ConnectThread, ScanThread

logger = Logger().get_logger("MainWindow")




class PeerManagerDialog(QDialog):
    """节点管理对话�?""
    def __init__(self, parent=None, config_data=None):
        super().__init__(parent)
        self.config_data = config_data
        self.setWindowTitle("节点管理")
        self.setModal(True)
        self.resize(700, 500)
        
        # 设置无边框窗�?
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 主容�?
        main_container = QWidget()
        main_container.setObjectName("dialogContainer")
        main_container.setStyleSheet("""
            #dialogContainer {
                background: #ffffff;
                border-radius: 8px;
                border: 1px solid #d0d0d0;
            }
        """)
        
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 标题�?
        title_bar = QWidget()
        title_bar.setObjectName("dialogTitleBar")
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("""
            #dialogTitleBar {
                background: #2e2e2e;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        
        title_label = QLabel("🌐 节点管理")
        title_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(45, 50)
        close_btn.clicked.connect(self.reject)
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
        title_layout.addWidget(close_btn)
        
        container_layout.addWidget(title_bar)
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        # 说明文本
        info_label = QLabel("💡 管理公共节点，用于跨网络 NAT 穿透连�?)
        info_label.setStyleSheet("""
            color: #666666;
            font-size: 13px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
        """)
        content_layout.addWidget(info_label)
        
        # 节点列表
        self.peer_list = QListWidget()
        self.peer_list.setStyleSheet("""
            QListWidget {
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background: #e8f5e9;
                color: #333333;
            }
            QListWidget::item:hover {
                background: #f0f0f0;
            }
        """)
        self.load_peers()
        content_layout.addWidget(self.peer_list)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("新增节点")
        add_btn.setFixedHeight(40)
        add_btn.setMinimumWidth(120)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_peer)
        add_btn.setObjectName("primaryBtn")
        add_btn.setStyleSheet("""
            QPushButton#primaryBtn {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 24px;
            }
            QPushButton#primaryBtn:hover {
                background: #06ae56;
            }
        """)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedHeight(40)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.clicked.connect(self.edit_peer)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: #e0e0e0;
                border-color: #d0d0d0;
            }
        """)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setFixedHeight(40)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(self.delete_peer)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #fa5151;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: #fa5151;
                color: #ffffff;
                border-color: #fa5151;
            }
        """)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        close_bottom_btn = QPushButton("完成")
        close_bottom_btn.setFixedHeight(40)
        close_bottom_btn.setCursor(Qt.PointingHandCursor)
        close_bottom_btn.clicked.connect(self.accept)
        close_bottom_btn.setStyleSheet("""
            QPushButton {
                background: #ededed;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 30px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        btn_layout.addWidget(close_bottom_btn)
        
        content_layout.addLayout(btn_layout)
        
        container_layout.addWidget(content_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_container)
        
        self.drag_position = None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= 50:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.drag_position = None
    
    def load_peers(self):
        """加载节点列表"""
        self.peer_list.clear()
        peer_list = self.config_data.get("peer_list", [])
        
        for peer in peer_list:
            item_text = f"{peer['name']}\n{peer['peers'] if peer['peers'] else '（不使用节点�?}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, peer)
            self.peer_list.addItem(item)
    
    def add_peer(self):
        """新增节点"""
        dialog = PeerEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, peers = dialog.get_data()
            peer_list = self.config_data.get("peer_list", [])
            peer_list.append({"name": name, "peers": peers})
            self.config_data["peer_list"] = peer_list
            ConfigCache.save(self.config_data)
            self.load_peers()
    
    def edit_peer(self):
        """编辑节点"""
        current_item = self.peer_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请选择要编辑的节点")
            return
        
        peer = current_item.data(Qt.UserRole)
        dialog = PeerEditDialog(self, peer["name"], peer["peers"])
        if dialog.exec_() == QDialog.Accepted:
            name, peers = dialog.get_data()
            peer["name"] = name
            peer["peers"] = peers
            ConfigCache.save(self.config_data)
            self.load_peers()
    
    def delete_peer(self):
        """删除节点"""
        current_item = self.peer_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请选择要删除的节点")
            return
        
        row = self.peer_list.row(current_item)
        peer_list = self.config_data.get("peer_list", [])
        peer_list.pop(row)
        self.config_data["peer_list"] = peer_list
        ConfigCache.save(self.config_data)
        self.load_peers()


class PeerEditDialog(QDialog):
    """节点编辑对话�?""
    def __init__(self, parent=None, name="", peers=""):
        super().__init__(parent)
        self.setWindowTitle("编辑节点")
        self.setModal(True)
        self.resize(500, 250)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 名称输入
        name_layout = QHBoxLayout()
        name_label = QLabel("节点名称:")
        name_label.setFixedWidth(80)
        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText("例如: 官方节点")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # 地址输入
        peers_layout = QVBoxLayout()
        peers_label = QLabel("节点地址:")
        peers_layout.addWidget(peers_label)
        
        self.peers_input = QTextEdit()
        self.peers_input.setPlainText(peers)
        self.peers_input.setPlaceholderText("输入节点地址，多个用逗号分隔\n例如: tcp://public.easytier.cn:11010,udp://public.easytier.cn:11010")
        self.peers_input.setMaximumHeight(80)
        peers_layout.addWidget(self.peers_input)
        layout.addLayout(peers_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setFixedSize(80, 35)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setFixedSize(80, 35)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def get_data(self):
        """获取输入数据"""
        return self.name_input.text().strip(), self.peers_input.toPlainText().strip()


class LogDialog(QDialog):
    """运行日志对话�?- 微信风格"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("运行日志")
        self.setModal(False)
        self.resize(900, 650)
        
        # 设置无边框窗�?
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 主容�?
        main_container = QWidget()
        main_container.setObjectName("dialogContainer")
        main_container.setStyleSheet("""
            #dialogContainer {
                background: #ffffff;
                border-radius: 8px;
                border: 1px solid #d0d0d0;
            }
        """)
        
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 自定义标题栏
        title_bar = QWidget()
        title_bar.setObjectName("dialogTitleBar")
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("""
            #dialogTitleBar {
                background: #2e2e2e;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        
        title_label = QLabel("📝 运行日志")
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
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
        title_layout.addWidget(close_btn)
        
        container_layout.addWidget(title_bar)
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        # 日志文本�?
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        content_layout.addWidget(self.log_text)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新日志")
        refresh_btn.setFixedHeight(40)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.load_log)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        btn_layout.addWidget(refresh_btn)
        
        # 清空按钮
        clear_btn = QPushButton("🗑�?清空日志")
        clear_btn.setFixedHeight(40)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_log)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #fa5151;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: #e04444;
            }
        """)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        
        # 关闭按钮
        close_bottom_btn = QPushButton("关闭")
        close_bottom_btn.setFixedHeight(40)
        close_bottom_btn.setCursor(Qt.PointingHandCursor)
        close_bottom_btn.clicked.connect(self.close)
        close_bottom_btn.setStyleSheet("""
            QPushButton {
                background: #ededed;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 30px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        btn_layout.addWidget(close_bottom_btn)
        
        content_layout.addLayout(btn_layout)
        
        container_layout.addWidget(content_widget)
        
        # 设置布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_container)
        
        # 窗口拖动相关
        self.drag_position = None
        
        self.load_log()
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            # 只在标题栏区域允许拖�?
            if event.pos().y() <= 50:
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.drag_position = None
    
    def load_log(self):
        """加载日志文件"""
        try:
            from datetime import datetime
            # 使用当前日期的日志文�?
            log_file = Config.LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
            
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 只显示最�?000�?
                    lines = content.split('\n')
                    if len(lines) > 1000:
                        lines = lines[-1000:]
                        content = '\n'.join(lines)
                    self.log_text.setPlainText(content)
                    # 滚动到底�?
                    self.log_text.verticalScrollBar().setValue(
                        self.log_text.verticalScrollBar().maximum()
                    )
            else:
                self.log_text.setPlainText(f"日志文件不存�? {log_file}\n\n请先进行一些操作以生成日志�?)
        except Exception as e:
            self.log_text.setPlainText(f"加载日志失败: {e}")
    
    def clear_log(self):
        """清空日志文件"""
        try:
            from datetime import datetime
            log_file = Config.LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
            
            if log_file.exists():
                # 清空文件内容
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write('')
                self.log_text.setPlainText("日志已清�?)
            else:
                self.log_text.setPlainText("日志文件不存�?)
        except Exception as e:
            self.log_text.setPlainText(f"清空日志失败: {e}")


class MainWindow(QMainWindow):
    """主窗�?- 美化�?""
    
    def __init__(self):
        super().__init__()
        self.controller = SyncController()
        self.connect_thread = None
        self.scan_thread = None
        self.log_dialog = None
        
        # 状态跟�?
        self.last_sync_state = None
        self.last_peer_ips = set()
        self.scan_count = 0
        self.is_connected = False
        
        # 当前页面
        self.current_page = "network"  # network �?game
        
        # 加载配置
        self.config_data = ConfigCache.load()
        
        # 更新 Minecraft 存档路径（根�?relative_path 重新计算本地路径�?
        MinecraftPathResolver.update_minecraft_paths(self.config_data)
        
        self.init_ui()
        self.init_services()
        
        # 应用样式
        self.setStyleSheet(MODERN_STYLE)
    
    def init_ui(self):
        """初始化UI - 微信风格"""
        self.setWindowTitle("LanGameSync")
        self.setMinimumSize(1000, 750)
        
        # 设置无边框窗�?
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建主容器（带圆角和阴影�?
        main_container = QWidget()
        main_container.setObjectName("mainContainer")
        self.setCentralWidget(main_container)
        
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 自定义标题栏
        title_bar = self.create_title_bar()
        container_layout.addWidget(title_bar)
        
        # 主内容区域（左侧边栏 + 右侧内容�?
        main_content = QWidget()
        main_content.setObjectName("mainContent")
        main_content_layout = QHBoxLayout(main_content)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        
        # 左侧边栏
        sidebar = self.create_sidebar()
        main_content_layout.addWidget(sidebar)
        
        # 右侧内容区域（使�?Stacked Widget 切换页面�?
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentWidget")
        
        # 网络管理页面
        network_page = QWidget()
        network_layout = QVBoxLayout(network_page)
        network_layout.setSpacing(15)
        network_layout.setContentsMargins(20, 15, 20, 20)
        
        # 网络管理区域
        network_group = self.create_network_group()
        network_layout.addWidget(network_group)
        
        # 客户端信息表�?
        clients_group = self.create_clients_group()
        network_layout.addWidget(clients_group)
        
        # 状态栏
        self.status_label = QLabel("状�? 未连�?)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        network_layout.addWidget(self.status_label)
        
        self.content_stack.addWidget(network_page)
        
        # 游戏管理页面
        game_page = self.create_game_page()
        self.content_stack.addWidget(game_page)
        
        main_content_layout.addWidget(self.content_stack)
        
        container_layout.addWidget(main_content)
        
        # 窗口拖动相关
        self.drag_position = None
    
    def create_sidebar(self):
        """创建左侧边栏 - 微信风格"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(70)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(0)
        
        # 网络管理按钮
        self.network_btn = QPushButton()
        self.network_btn.setObjectName("sidebarBtn")
        self.network_btn.setFixedSize(70, 70)
        self.network_btn.setText("🌐")
        self.network_btn.setToolTip("网络管理")
        self.network_btn.clicked.connect(lambda: self.switch_page("network"))
        self.network_btn.setStyleSheet("""
            QPushButton#sidebarBtn {
                background: #2e2e2e;
                color: #ffffff;
                border: none;
                border-left: 3px solid #07c160;
                font-size: 28px;
            }
            QPushButton#sidebarBtn:hover {
                background: #3e3e3e;
            }
        """)
        layout.addWidget(self.network_btn)
        
        # 游戏管理按钮
        self.game_btn = QPushButton()
        self.game_btn.setObjectName("sidebarBtnInactive")
        self.game_btn.setFixedSize(70, 70)
        self.game_btn.setText("🎮")
        self.game_btn.setToolTip("游戏管理")
        self.game_btn.clicked.connect(lambda: self.switch_page("game"))
        self.game_btn.setStyleSheet("""
            QPushButton#sidebarBtnInactive {
                background: #2e2e2e;
                color: #888888;
                border: none;
                font-size: 28px;
            }
            QPushButton#sidebarBtnInactive:hover {
                background: #3e3e3e;
                color: #aaaaaa;
            }
        """)
        layout.addWidget(self.game_btn)
        
        # 设置按钮
        settings_btn = QPushButton()
        settings_btn.setObjectName("sidebarBtnInactive")
        settings_btn.setFixedSize(70, 70)
        settings_btn.setText("⚙️")
        settings_btn.setToolTip("设置")
        settings_btn.clicked.connect(self.show_log_dialog)
        settings_btn.setStyleSheet("""
            QPushButton#sidebarBtnInactive {
                background: #2e2e2e;
                color: #888888;
                border: none;
                font-size: 28px;
            }
            QPushButton#sidebarBtnInactive:hover {
                background: #3e3e3e;
                color: #aaaaaa;
            }
        """)
        
        layout.addStretch()
        layout.addWidget(settings_btn)
        
        return sidebar
    
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
    
    def create_game_page(self):
        """创建游戏管理页面"""
        page = QWidget()
        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧：游戏列�?
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_panel.setStyleSheet("""
            QWidget {
                background: #f5f5f5;
                border-right: 1px solid #e0e0e0;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 游戏列表标题
        game_list_title = QLabel("游戏列表")
        game_list_title.setStyleSheet("""
            color: #333333;
            font-size: 16px;
            font-weight: bold;
            padding: 20px 15px;
            background: #f5f5f5;
            border-bottom: 1px solid #e0e0e0;
        """)
        left_layout.addWidget(game_list_title)
        
        # 游戏列表
        self.game_list_widget = QListWidget()
        self.game_list_widget.setStyleSheet("""
            QListWidget {
                background: #f5f5f5;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #e0e0e0;
                color: #666666;
            }
            QListWidget::item:selected {
                background: #ffffff;
                color: #07c160;
                border-left: 3px solid #07c160;
            }
            QListWidget::item:hover {
                background: #fafafa;
            }
        """)
        self.game_list_widget.currentRowChanged.connect(self.on_game_selected)
        left_layout.addWidget(self.game_list_widget)
        
        # 添加游戏按钮
        add_game_btn = QPushButton("�?添加游戏")
        add_game_btn.setFixedHeight(50)
        add_game_btn.setCursor(Qt.PointingHandCursor)
        add_game_btn.clicked.connect(self.show_add_game_dialog)
        add_game_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                font-size: 14px;
                text-align: center;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        left_layout.addWidget(add_game_btn)
        
        main_layout.addWidget(left_panel)
        
        # 右侧：游戏详�?存档管理
        self.right_panel_stack = QStackedWidget()
        self.right_panel_stack.setStyleSheet("""
            QStackedWidget {
                background: #ffffff;
            }
        """)
        
        # 默认页：未选择游戏
        default_page = self.create_default_right_page()
        self.right_panel_stack.addWidget(default_page)
        
        main_layout.addWidget(self.right_panel_stack)
        
        # 加载游戏列表
        self.load_game_list()
        
        return page
    
    def create_default_right_page(self):
        """创建默认右侧页面（未选择游戏时显示）"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel("🎮\n\n请在左侧选择或添加游�?)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            color: #999999;
            font-size: 16px;
        """)
        layout.addWidget(label)
        return page
    
    def load_game_list(self):
        """加载游戏列表"""
        self.game_list_widget.clear()
        
        # 添加 Minecraft（固定项�?
        minecraft_item = QListWidgetItem("🎮 Minecraft")
        minecraft_item.setData(Qt.UserRole, {"type": "minecraft"})
        self.game_list_widget.addItem(minecraft_item)
        
        # 添加其他游戏
        game_list = self.config_data.get("game_list", [])
        for game in game_list:
            if game.get("type") != "minecraft":  # 跳过 minecraft 类型的游�?
                item_text = f"💾 {game['name']}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, game)
                self.game_list_widget.addItem(item)
    
    def on_game_selected(self, index):
        """当选择游戏时触�?""
        if index < 0:
            return
        
        item = self.game_list_widget.item(index)
        game_data = item.data(Qt.UserRole)
        
        if game_data.get("type") == "minecraft":
            # 显示 Minecraft 管理页面
            self.show_minecraft_page()
        else:
            # 显示普通游戏详情页�?
            self.show_normal_game_page(game_data)
    
    def show_minecraft_page(self):
        """显示 Minecraft 管理页面"""
        # 移除旧页�?
        while self.right_panel_stack.count() > 1:
            widget = self.right_panel_stack.widget(1)
            self.right_panel_stack.removeWidget(widget)
            widget.deleteLater()
        
        # 检查是否已配置启动�?
        minecraft_config = self.config_data.get("minecraft_config", {})
        minecraft_dir = minecraft_config.get("minecraft_dir")
        
        if not minecraft_dir:
            # 未配置启动器，显示配置页�?
            config_page = self.create_minecraft_config_page()
            self.right_panel_stack.addWidget(config_page)
            self.right_panel_stack.setCurrentIndex(1)
        else:
            # 已配置，显示存档管理页面
            saves_page = self.create_minecraft_saves_page(minecraft_dir)
            self.right_panel_stack.addWidget(saves_page)
            self.right_panel_stack.setCurrentIndex(1)
    
    def create_minecraft_config_page(self):
        """创建 Minecraft 配置页面（未配置启动器时�?""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        # 提示信息
        title = QLabel("🎮 Minecraft")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: #333333;
            font-size: 24px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        info = QLabel("请先配置 Minecraft 启动器\n以便管理游戏存档")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("""
            color: #666666;
            font-size: 14px;
        """)
        layout.addWidget(info)
        
        # 配置按钮
        config_btn = QPushButton("📂 选择启动�?)
        config_btn.setFixedHeight(50)
        config_btn.setFixedWidth(200)
        config_btn.setCursor(Qt.PointingHandCursor)
        config_btn.clicked.connect(self.configure_minecraft_launcher)
        config_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        layout.addWidget(config_btn, 0, Qt.AlignCenter)
        
        layout.addStretch()
        
        return page
    
    def configure_minecraft_launcher(self):
        """配置 Minecraft 启动�?""
        self.add_minecraft_game(None)
        # 重新加载页面
        self.show_minecraft_page()
    
    def create_minecraft_saves_page(self, minecraft_dir):
        """创建 Minecraft 存档管理页面"""
        import os
        
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        
        # 标题�?
        header_layout = QHBoxLayout()
        title = QLabel("🎮 Minecraft - 存档管理")
        title.setStyleSheet("""
            color: #333333;
            font-size: 20px;
            font-weight: bold;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 重新配置按钮
        reconfig_btn = QPushButton("🔄 重新配置启动�?)
        reconfig_btn.setCursor(Qt.PointingHandCursor)
        reconfig_btn.clicked.connect(self.reconfigure_minecraft_launcher)
        reconfig_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px 15px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        header_layout.addWidget(reconfig_btn)
        
        layout.addLayout(header_layout)
        
        # 启动器信�?
        minecraft_config = self.config_data.get("minecraft_config", {})
        launcher_type = minecraft_config.get("launcher_type", "Unknown")
        info_label = QLabel(f"启动器：{launcher_type} | 路径：{minecraft_dir}")
        info_label.setStyleSheet("""
            color: #999999;
            font-size: 12px;
            padding: 5px;
            background: #f5f5f5;
            border-radius: 4px;
        """)
        layout.addWidget(info_label)
        
        # 存档列表
        saves_label = QLabel("💾 存档列表")
        saves_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
        """)
        layout.addWidget(saves_label)
        
        saves_list = QListWidget()
        saves_list.setSelectionMode(QListWidget.MultiSelection)
        saves_list.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 4px;
                margin: 2px;
                border: 1px solid transparent;
            }
            QListWidget::item:selected {
                background: #e8f5e9;
                color: #333333;
                border: 1px solid #07c160;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        layout.addWidget(saves_list)
        
        # 加载存档列表（支持版本隔离）
        synced_saves = self.config_data.get("game_list", [])
        synced_save_paths = [g.get("path") for g in synced_saves if g.get("type") == "minecraft"]
        
        all_saves = []  # 存储所有找到的存档 {"name": xxx, "path": xxx, "version": xxx}
        
        # 1. 检查标准位置：.minecraft/saves
        standard_saves_dir = os.path.join(minecraft_dir, "saves")
        if os.path.exists(standard_saves_dir):
            for save_name in os.listdir(standard_saves_dir):
                save_path = os.path.join(standard_saves_dir, save_name)
                if os.path.isdir(save_path):
                    level_dat = os.path.join(save_path, "level.dat")
                    if os.path.exists(level_dat):
                        all_saves.append({
                            "name": save_name,
                            "path": save_path,
                            "version": "通用"
                        })
        
        # 2. 检查版本隔离位置：.minecraft/versions/*/saves
        versions_dir = os.path.join(minecraft_dir, "versions")
        if os.path.exists(versions_dir):
            for version_name in os.listdir(versions_dir):
                version_saves_dir = os.path.join(versions_dir, version_name, "saves")
                if os.path.exists(version_saves_dir):
                    for save_name in os.listdir(version_saves_dir):
                        save_path = os.path.join(version_saves_dir, save_name)
                        if os.path.isdir(save_path):
                            level_dat = os.path.join(save_path, "level.dat")
                            if os.path.exists(level_dat):
                                all_saves.append({
                                    "name": save_name,
                                    "path": save_path,
                                    "version": version_name
                                })
        
        # 添加到列�?
        for save_info in sorted(all_saves, key=lambda x: (x["version"], x["name"])):
            save_name = save_info["name"]
            save_path = save_info["path"]
            version = save_info["version"]
            
            # 判断是否已同�?
            if save_path in synced_save_paths:
                item_text = f"�?{save_name} ({version})" if version != "通用" else f"�?{save_name}"
            else:
                item_text = f"💾 {save_name} ({version})" if version != "通用" else f"💾 {save_name}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, {"name": save_name, "path": save_path, "version": version})
            saves_list.addItem(item)
            
            # 如果已同步，默认选中
            if save_path in synced_save_paths:
                item.setSelected(True)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 保存同步设置")
        save_btn.setFixedHeight(40)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(lambda: self.save_minecraft_sync_settings(saves_list, minecraft_dir))
        save_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        return page
    
    def save_minecraft_sync_settings(self, saves_list, minecraft_dir):
        """保存 Minecraft 同步设置"""
        import os
        
        selected_items = saves_list.selectedItems()
        
        # 移除旧的 minecraft 存档
        game_list = self.config_data.get("game_list", [])
        game_list = [g for g in game_list if g.get("type") != "minecraft"]
        
        # 添加新选中的存�?
        minecraft_config = self.config_data.get("minecraft_config", {})
        launcher_type = minecraft_config.get("launcher_type", "Unknown")
        
        for item in selected_items:
            save_data = item.data(Qt.UserRole)
            save_name = save_data["name"]
            save_path = save_data["path"]  # 使用实际路径
            version = save_data.get("version", "通用")
            
            # 生成显示名称和同步路�?
            if version == "通用":
                display_name = f"Minecraft - {save_name}"
                relative_path = f"saves/{save_name}"  # 标准存档，只同步存档
                sync_type = "save"
            else:
                display_name = f"Minecraft - {save_name} ({version})"
                relative_path = f"versions/{version}"  # 版本隔离，同步整个版本目�?
                sync_type = "version"
            
            game_list.append({
                "name": display_name,
                "path": save_path,  # 本地绝对路径
                "relative_path": relative_path,  # 相对路径（用于同步）
                "sync_type": sync_type,  # 同步类型
                "type": "minecraft",
                "launcher": launcher_type,
                "save_name": save_name,
                "version": version,
                "minecraft_dir": minecraft_dir
            })
        
        self.config_data["game_list"] = game_list
        ConfigCache.save(self.config_data)
        
        QMessageBox.information(self, "成功", f"已保存同步设置，�?{len(selected_items)} 个存�?)
        
        # 刷新页面
        self.show_minecraft_page()
    
    def reconfigure_minecraft_launcher(self):
        """重新配置 Minecraft 启动�?""
        self.add_minecraft_game(None)
        self.show_minecraft_page()
    
    def resolve_minecraft_save_path(self, relative_path, sync_type="save", save_name=None):
        """
        根据相对路径计算本地存档绝对路径
        支持智能映射�?
        - 如果本地有对应版�?-> 使用版本隔离路径
        - 如果本地没有对应版本 -> 使用标准路径
        
        Args:
            relative_path: 相对�?.minecraft 的路�?
            sync_type: 同步类型 (save/version)
            save_name: 存档名称
        
        Returns:
            本地绝对路径
        """
        import os
        import re
        
        minecraft_config = self.config_data.get("minecraft_config", {})
        minecraft_dir = minecraft_config.get("minecraft_dir")
        
        if not minecraft_dir:
            return None
        
        # 新逻辑：处理版本目录同�?(sync_type == "version")
        if sync_type == "version":
            # relative_path 是整个版本目录，例如 "versions/1.21.8"
            match = re.match(r"versions/(.+)", relative_path)
            if match:
                version = match.group(1)
                
                # 检查本地是否有这个版本
                version_dir = os.path.join(minecraft_dir, "versions", version)
                if os.path.exists(version_dir):
                    # 本地有这个版本，直接使用
                    logger.info(f"本地已有版本 {version}，使用现有版本目�?)
                    return version_dir
                else:
                    # 本地没有这个版本，创建目录并接收
                    logger.info(f"本地没有版本 {version}，将创建并接收完整版本文�?)
                    if not os.path.exists(version_dir):
                        os.makedirs(version_dir)
                    return version_dir
        
        # 旧逻辑：处理单独存档同�?(sync_type == "save" 或旧数据)
        # 解析相对路径
        # 格式 1: versions/{version}/saves/{save_name} (旧格�?
        # 格式 2: saves/{save_name}
        match = re.match(r"versions/(.+?)/saves/(.+)", relative_path)
        if match:
            # 旧格式：版本隔离存档
            version = match.group(1)
            save_name = match.group(2)
            
            # 检查本地是否有这个版本
            version_dir = os.path.join(minecraft_dir, "versions", version)
            if os.path.exists(version_dir):
                # 本地有这个版本，使用版本隔离路径
                version_saves_dir = os.path.join(version_dir, "saves")
                if not os.path.exists(version_saves_dir):
                    os.makedirs(version_saves_dir)
                return os.path.join(version_saves_dir, save_name)
            else:
                # 本地没有这个版本，使用标准路�?
                standard_saves_dir = os.path.join(minecraft_dir, "saves")
                if not os.path.exists(standard_saves_dir):
                    os.makedirs(standard_saves_dir)
                
                # 记录警告：版本不匹配
                logger.warning(
                    f"本地没有找到版本 {version}，存�?{save_name} 将被放置在标准目录：{standard_saves_dir}"
                )
                return os.path.join(standard_saves_dir, save_name)
        else:
            # 标准存档：需要检查本地是否开启了版本隔离
            match = re.match(r"saves/(.+)", relative_path)
            if match:
                save_name = match.group(1)
                
                # 检查本地是否有 versions 目录（判断是否开启版本隔离）
                versions_dir = os.path.join(minecraft_dir, "versions")
                has_version_isolation = os.path.exists(versions_dir) and os.path.isdir(versions_dir)
                
                # 检查是否有标准 saves 目录
                standard_saves_dir = os.path.join(minecraft_dir, "saves")
                has_standard_saves = os.path.exists(standard_saves_dir) and os.path.isdir(standard_saves_dir)
                
                if has_version_isolation and not has_standard_saves:
                    # 本地开启了版本隔离，但没有标准 saves 目录
                    # 需要将存档放到某个版本�?
                    # 选择第一个有 saves 目录的版�?
                    for version_name in os.listdir(versions_dir):
                        version_path = os.path.join(versions_dir, version_name)
                        if os.path.isdir(version_path):
                            version_saves_dir = os.path.join(version_path, "saves")
                            if os.path.exists(version_saves_dir):
                                # 找到了一个有 saves 的版�?
                                logger.warning(
                                    f"接收到标准存档，但本地开启了版本隔离�?
                                    f"存档 {save_name} 将被放置在版�?{version_name} 下：{version_saves_dir}"
                                )
                                return os.path.join(version_saves_dir, save_name)
                    
                    # 如果没有找到任何�?saves 的版本，创建标准目录
                    logger.info(f"本地开启了版本隔离但没有找到任何版本，创建标准 saves 目录")
                    if not os.path.exists(standard_saves_dir):
                        os.makedirs(standard_saves_dir)
                    return os.path.join(standard_saves_dir, save_name)
                else:
                    # 本地有标�?saves 目录，或者没开启版本隔�?
                    if not os.path.exists(standard_saves_dir):
                        os.makedirs(standard_saves_dir)
                    return os.path.join(standard_saves_dir, save_name)
        
        # 如果无法解析，直接拼�?
        return os.path.join(minecraft_dir, relative_path)
    
    def update_minecraft_paths(self):
        """
        更新所�?Minecraft 存档的本地路�?
        根据 relative_path 重新计算 path
        用于应用启动时，根据本机环境调整路径
        """
        game_list = self.config_data.get("game_list", [])
        updated = False
        
        for game in game_list:
            if game.get("type") == "minecraft" and game.get("relative_path"):
                # 根据 relative_path 重新计算本地路径
                sync_type = game.get("sync_type", "save")  # 默认�?save 类型（兼容旧数据�?
                save_name = game.get("save_name")
                
                new_path = self.resolve_minecraft_save_path(
                    game["relative_path"],
                    sync_type=sync_type,
                    save_name=save_name
                )
                
                if new_path and new_path != game.get("path"):
                    old_path = game.get("path")
                    game["path"] = new_path
                    updated = True
                    logger.info(f"更新 Minecraft 路径: {old_path} -> {new_path}")
        
        if updated:
            ConfigCache.save(self.config_data)
            logger.info("已更�?Minecraft 路径")
    
    def show_normal_game_page(self, game_data):
        """显示普通游戏详情页�?""
        # 移除旧页�?
        while self.right_panel_stack.count() > 1:
            widget = self.right_panel_stack.widget(1)
            self.right_panel_stack.removeWidget(widget)
            widget.deleteLater()
        
        # 创建普通游戏详情页�?
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel(f"💾 {game_data.get('name', '未知游戏')}")
        title.setStyleSheet("""
            color: #333333;
            font-size: 20px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        # 游戏信息
        info_group = QWidget()
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(10)
        
        path_label = QLabel(f"📂 存档路径：{game_data.get('path', 'N/A')}")
        path_label.setWordWrap(True)
        path_label.setStyleSheet("""
            color: #666666;
            font-size: 13px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
        """)
        info_layout.addWidget(path_label)
        
        layout.addWidget(info_group)
        layout.addStretch()
        
        # 删除按钮
        btn_layout = QHBoxLayout()
        delete_btn = QPushButton("🗑�?删除游戏")
        delete_btn.setFixedHeight(40)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.delete_normal_game(game_data))
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #fa5151;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: #fa5151;
                color: #ffffff;
            }
        """)
        btn_layout.addStretch()
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        self.right_panel_stack.addWidget(page)
        self.right_panel_stack.setCurrentIndex(1)
    
    def delete_normal_game(self, game_data):
        """删除普通游�?""
        result = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除游戏「{game_data.get('name')}」吗�?,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            game_list = self.config_data.get("game_list", [])
            game_list = [g for g in game_list if g.get("path") != game_data.get("path")]
            self.config_data["game_list"] = game_list
            ConfigCache.save(self.config_data)
            
            # 刷新列表
            self.load_game_list()
            
            # 显示默认页面
            self.right_panel_stack.setCurrentIndex(0)
    
    def show_add_game_dialog(self):
        """显示添加游戏对话�?""
        # 创建游戏类型选择对话�?
        dialog = QDialog(self)
        dialog.setWindowTitle("添加游戏")
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        # 主容�?
        main_container = QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(dialog)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("选择游戏类型")
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # 游戏类型选择
        type_group = QWidget()
        type_layout = QVBoxLayout(type_group)
        type_layout.setSpacing(10)
        
        # Minecraft 按钮
        mc_btn = QPushButton("🎮 Minecraft (我的世界)")
        mc_btn.setFixedHeight(50)
        mc_btn.setCursor(Qt.PointingHandCursor)
        mc_btn.clicked.connect(lambda: self.add_minecraft_game(dialog))
        mc_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        type_layout.addWidget(mc_btn)
        
        # 普通游戏按�?
        normal_btn = QPushButton("💾 普通游戏（选择存档目录�?)
        normal_btn.setFixedHeight(50)
        normal_btn.setCursor(Qt.PointingHandCursor)
        normal_btn.clicked.connect(lambda: self.add_normal_game(dialog))
        normal_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        type_layout.addWidget(normal_btn)
        
        layout.addWidget(type_group)
        layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        layout.addWidget(cancel_btn)
        
        container_layout.addWidget(main_container)
        dialog.exec_()
    
    def add_minecraft_game(self, dialog):
        """添加 Minecraft 游戏"""
        dialog.accept()
        self.show_minecraft_add_dialog()
    
    def show_minecraft_add_dialog(self):
        """显示 Minecraft 添加对话�?""
        # 创建对话�?
        dialog = QDialog(self)
        dialog.setWindowTitle("添加 Minecraft 游戏")
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        # 主容�?
        main_container = QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(dialog)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("添加 Minecraft 游戏")
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # 游戏名称
        name_label = QLabel("游戏名称")
        name_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入游戏名�?)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #07c160;
            }
        """)
        layout.addWidget(self.name_input)
        
        # 游戏路径
        path_label = QLabel("游戏路径")
        path_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(path_label)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("请输入游戏路�?)
        self.path_input.setStyleSheet("""
            QLineEdit {
                background: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #07c160;
            }
        """)
        layout.addWidget(self.path_input)
        
        # 选择路径按钮
        select_path_btn = QPushButton("选择路径")
        select_path_btn.setFixedHeight(40)
        select_path_btn.setCursor(Qt.PointingHandCursor)
        select_path_btn.clicked.connect(self.select_minecraft_path)
        select_path_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        layout.addWidget(select_path_btn)
        
        # 添加按钮
        add_btn = QPushButton("添加")
        add_btn.setFixedHeight(40)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_minecraft_game_to_list)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                font-size: 14px;
                text-align: center;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        layout.addWidget(add_btn)
        
        container_layout.addWidget(main_container)
        dialog.exec_()
    
    def select_minecraft_path(self):
        """选择 Minecraft 游戏路径"""
        path = QFileDialog.getExistingDirectory(self, "选择 Minecraft 游戏路径")
        if path:
            self.path_input.setText(path)
    
    def add_minecraft_game_to_list(self):
        """�?Minecraft 游戏添加到列�?""
        name = self.name_input.text().strip()
        path = self.path_input.text().strip()
        
        if not name or not path:
            QMessageBox.warning(self, "警告", "游戏名称和路径不能为�?)
            return
        
        game = {
            "type": "minecraft",
            "name": name,
            "path": path,
            "version": "",
            "mods": [],
            "resourcepacks": [],
            "shaders": [],
            "options": {}
        }
        
        game_list = self.config_data.get("game_list", [])
        game_list.append(game)
        self.config_data["game_list"] = game_list
        self.save_config()
        self.load_game_list()
    
    def add_normal_game(self, dialog):
        """添加普通游�?""
        dialog.accept()
        self.show_normal_add_dialog()
    
    def show_normal_add_dialog(self):
        """显示普通游戏添加对话框"""
        # 创建对话�?
        dialog = QDialog(self)
        dialog.setWindowTitle("添加普通游�?)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        # 主容�?
        main_container = QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(dialog)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("添加普通游�?)
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # 游戏名称
        name_label = QLabel("游戏名称")
        name_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入游戏名�?)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #07c160;
            }
        """)
        layout.addWidget(self.name_input)
        
        # 游戏路径
        path_label = QLabel("游戏路径")
        path_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(path_label)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("请输入游戏路�?)
        self.path_input.setStyleSheet("""
            QLineEdit {
                background: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #07c160;
            }
        """)
        layout.addWidget(self.path_input)
        
        # 选择路径按钮
        select_path_btn = QPushButton("选择路径")
        select_path_btn.setFixedHeight(40)
        select_path_btn.setCursor(Qt.PointingHandCursor)
        select_path_btn.clicked.connect(self.select_normal_path)
        select_path_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        layout.addWidget(select_path_btn)
        
        # 添加按钮
        add_btn = QPushButton("添加")
        add_btn.setFixedHeight(40)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_normal_game_to_list)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                font-size: 14px;
                text-align: center;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        layout.addWidget(add_btn)
        
        container_layout.addWidget(main_container)
        dialog.exec_()
    
    def select_normal_path(self):
        """选择普通游戏路�?""
        path = QFileDialog.getExistingDirectory(self, "选择普通游戏路�?)
        if path:
            self.path_input.setText(path)
    
    def add_normal_game_to_list(self):
        """将普通游戏添加到列表"""
        name = self.name_input.text().strip()
        path = self.path_input.text().strip()
        
        if not name or not path:
            QMessageBox.warning(self, "警告", "游戏名称和路径不能为�?)
            return
        
        game = {
            "type": "normal",
            "name": name,
            "path": path,
            "options": {}
        }
        
        game_list = self.config_data.get("game_list", [])
        game_list.append(game)
        self.config_data["game_list"] = game_list
        self.save_config()
        self.load_game_list()
    
    def show_minecraft_game_details(self, game):
        """显示 Minecraft 游戏详情"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel(f"{game['name']} - Minecraft")
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # 游戏路径
        path_label = QLabel(f"游戏路径: {game['path']}")
        path_label.setStyleSheet("""
            color: #666666;
            font-size: 14px;
            margin-bottom: 10px;
        """)
        layout.addWidget(path_label)
        
        # 版本
        version_label = QLabel(f"版本: {game['version']}")
        version_label.setStyleSheet("""
            color: #666666;
            font-size: 14px;
            margin-bottom: 10px;
        """)
        layout.addWidget(version_label)
        
        # 模组
        mods_label = QLabel("模组:")
        mods_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(mods_label)
        
        mods_list = QListWidget()
        mods_list.setStyleSheet("""
            QListWidget {
                background: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
                color: #666666;
            }
            QListWidget::item:hover {
                background: #fafafa;
            }
        """)
        for mod in game['mods']:
            item = QListWidgetItem(mod)
            mods_list.addItem(item)
        layout.addWidget(mods_list)
        
        # 资源�?
        resourcepacks_label = QLabel("资源�?")
        resourcepacks_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(resourcepacks_label)
        
        resourcepacks_list = QListWidget()
        resourcepacks_list.setStyleSheet("""
            QListWidget {
                background: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
                color: #666666;
            }
            QListWidget::item:hover {
                background: #fafafa;
            }
        """)
        for resourcepack in game['resourcepacks']:
            item = QListWidgetItem(resourcepack)
            resourcepacks_list.addItem(item)
        layout.addWidget(resourcepacks_list)
        
        # 着色器
        shaders_label = QLabel("着色器:")
        shaders_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(shaders_label)
        
        shaders_list = QListWidget()
        shaders_list.setStyleSheet("""
            QListWidget {
                background: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        layout.addWidget(cancel_btn)
        
        container_layout.addWidget(main_container)
        
        # 居中显示
        dialog.adjustSize()
        if self.isVisible():
            parent_rect = self.frameGeometry()
            dialog_rect = dialog.frameGeometry()
            center_point = parent_rect.center()
            dialog_rect.moveCenter(center_point)
            dialog.move(dialog_rect.topLeft())
        
        dialog.exec_()
    
    def add_minecraft_game(self, parent_dialog):
        """添加 Minecraft 游戏"""
        # 关闭父对话框（如果有�?
        if parent_dialog:
            parent_dialog.close()
        
        # 创建拖入对话�?
        drop_dialog = QDialog(self)
        drop_dialog.setWindowTitle("选择启动�?)
        drop_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        drop_dialog.setAttribute(Qt.WA_TranslucentBackground)
        drop_dialog.setModal(True)
        drop_dialog.resize(500, 350)
        drop_dialog.setAcceptDrops(True)
        
        # 主容�?
        main_container = QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(drop_dialog)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("选择 HMCL/PCL 启动�?)
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # 拖放区域
        drop_area = QLabel("📥\n\n�?HMCL �?PCL 启动器\n拖入此处\n\n或点击下方按钮选择")
        drop_area.setObjectName("dropArea")
        drop_area.setAlignment(Qt.AlignCenter)
        drop_area.setMinimumHeight(150)
        drop_area.setStyleSheet("""
            QLabel#dropArea {
                background: #f5f5f5;
                border: 2px dashed #d0d0d0;
                border-radius: 8px;
                color: #999999;
                font-size: 14px;
                padding: 20px;
            }
        """)
        layout.addWidget(drop_area)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        browse_btn = QPushButton("📂 浏览选择")
        browse_btn.setFixedHeight(40)
        browse_btn.setMinimumWidth(120)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(drop_dialog.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        
        def handle_launcher_file(launcher_file):
            drop_dialog.accept()
            self.process_launcher_file(launcher_file)
        
        def browse_file():
            launcher_file, _ = QFileDialog.getOpenFileName(
                drop_dialog,
                "选择 HMCL �?PCL 启动�?,
                "",
                "Launcher Files (*.jar *.exe);;All Files (*.*)"
            )
            if launcher_file:
                handle_launcher_file(launcher_file)
        
        browse_btn.clicked.connect(browse_file)
        
        # 实现拖放功能
        def dragEnterEvent(event):
            if event.mimeData().hasUrls():
                event.accept()
                drop_area.setStyleSheet("""
                    QLabel#dropArea {
                        background: #e8f5e9;
                        border: 2px dashed #07c160;
                        border-radius: 8px;
                        color: #07c160;
                        font-size: 14px;
                        padding: 20px;
                    }
                """)
            else:
                event.ignore()
        
        def dragLeaveEvent(event):
            drop_area.setStyleSheet("""
                QLabel#dropArea {
                    background: #f5f5f5;
                    border: 2px dashed #d0d0d0;
                    border-radius: 8px;
                    color: #999999;
                    font-size: 14px;
                    padding: 20px;
                }
            """)
        
        def dropEvent(event):
            try:
                import os
                files = [u.toLocalFile() for u in event.mimeData().urls()]
                if not files:
                    logger.warning("拖入操作没有文件")
                    return
                
                launcher_file = files[0]
                if not launcher_file or not os.path.exists(launcher_file):
                    MessageBox.show_warning(drop_dialog, "警告", "文件不存在或无效")
                    return
                
                if launcher_file.lower().endswith(('.jar', '.exe')):
                    handle_launcher_file(launcher_file)
                else:
                    MessageBox.show_warning(drop_dialog, "警告", "请选择 .jar �?.exe 文件")
            except Exception as e:
                logger.error(f"处理拖入文件时出�? {e}")
                MessageBox.show_error(drop_dialog, "错误", f"处理文件失败：{str(e)}")
        
        drop_dialog.dragEnterEvent = dragEnterEvent
        drop_dialog.dragLeaveEvent = dragLeaveEvent
        drop_dialog.dropEvent = dropEvent
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(browse_btn)
        
        layout.addLayout(btn_layout)
        
        container_layout.addWidget(main_container)
        
        # 居中显示
        drop_dialog.adjustSize()
        if self.isVisible():
            parent_rect = self.frameGeometry()
            dialog_rect = drop_dialog.frameGeometry()
            center_point = parent_rect.center()
            dialog_rect.moveCenter(center_point)
            drop_dialog.move(dialog_rect.topLeft())
        
        drop_dialog.exec_()
    
    def process_launcher_file(self, launcher_file):
        """处理启动器文�?""
        try:
            import os
            from PyQt5.QtWidgets import QFileDialog
            
            # 验证文件
            if not launcher_file or not os.path.exists(launcher_file):
                MessageBox.show_warning(self, "警告", "启动器文件不存在")
                return
            
            launcher_dir = os.path.dirname(launcher_file)
            launcher_name = os.path.basename(launcher_file).lower()
        
            minecraft_dir = None
            
            # 判断启动器类型（仅用于显示）
            if "hmcl" in launcher_name:
                launcher_type = "HMCL"
            elif "pcl" in launcher_name or "plain craft launcher" in launcher_name:
                launcher_type = "PCL"
            else:
                launcher_type = "Minecraft"
            
            # 通用的目录检测逻辑（与启动器类型无关）
            potential_dirs = [
                launcher_dir,  # 启动器所在目�?
                os.path.join(launcher_dir, ".minecraft"),  # 同目录下�?.minecraft
                os.path.join(launcher_dir, "minecraft"),    # 同目录下�?minecraft
            ]
            
            # 尝试查找 .minecraft 目录（通过检�?saves �?versions 文件夹）
            for potential_dir in potential_dirs:
                # 优先检�?saves 文件�?
                saves_dir = os.path.join(potential_dir, "saves")
                versions_dir = os.path.join(potential_dir, "versions")
                
                # 只要�?saves �?versions 文件夹就认为是有效的 .minecraft 目录
                if (os.path.exists(saves_dir) and os.path.isdir(saves_dir)) or \
                   (os.path.exists(versions_dir) and os.path.isdir(versions_dir)):
                    minecraft_dir = potential_dir
                    break
            
            # 如果没有找到，让用户手动选择
            if not minecraft_dir:
                # 显示调试信息
                debug_info = f"已尝试的路径：\n"
                for pd in potential_dirs:
                    saves_check = os.path.join(pd, "saves")
                    exists = os.path.exists(saves_check)
                    debug_info += f"- {pd}\n  saves: {exists}\n"
                
                result = MessageBox.show_question(
                    self,
                    "未找到游戏目�?,
                    f"未能自动检测到 .minecraft 目录\n\n{debug_info}\n是否手动选择�?
                )
                
                from PyQt5.QtWidgets import QMessageBox
                if result == QMessageBox.Yes:
                    minecraft_dir = QFileDialog.getExistingDirectory(
                        self,
                        "选择包含 saves 文件夹的目录",
                        launcher_dir
                    )
                
                if not minecraft_dir:
                    return
            
            # 读取存档列表（支持版本隔离）
            all_saves = []  # 所有存�?
            
            # 1. 检查标准位置：.minecraft/saves
            standard_saves_dir = os.path.join(minecraft_dir, "saves")
            if os.path.exists(standard_saves_dir):
                for save_name in os.listdir(standard_saves_dir):
                    save_path = os.path.join(standard_saves_dir, save_name)
                    if os.path.isdir(save_path):
                        level_dat = os.path.join(save_path, "level.dat")
                        if os.path.exists(level_dat):
                            all_saves.append(save_name)
            
            # 2. 检查版本隔离位置：.minecraft/versions/*/saves
            versions_dir = os.path.join(minecraft_dir, "versions")
            if os.path.exists(versions_dir):
                for version_name in os.listdir(versions_dir):
                    version_path = os.path.join(versions_dir, version_name)
                    if os.path.isdir(version_path):
                        version_saves_dir = os.path.join(version_path, "saves")
                        if os.path.exists(version_saves_dir):
                            for save_name in os.listdir(version_saves_dir):
                                save_path = os.path.join(version_saves_dir, save_name)
                                if os.path.isdir(save_path):
                                    level_dat = os.path.join(save_path, "level.dat")
                                    if os.path.exists(level_dat):
                                        # 避免重复，使�?"存档�?(版本�?" 格式
                                        all_saves.append(f"{save_name} [{version_name}]")
            
            if not all_saves:
                # 没有找到任何存档，只保存启动器配�?
                self.config_data["minecraft_config"] = {
                    "minecraft_dir": minecraft_dir,
                    "launcher_type": launcher_type
                }
                ConfigCache.save(self.config_data)
                
                MessageBox.show_info(
                    self, 
                    "配置完成", 
                    f"�?已保�?Minecraft 启动器配置\n\n"
                    f"启动器：{launcher_type}\n"
                    f"路径：{minecraft_dir}\n\n"
                    f"📌 提示：\n"
                    f"未找到存档，但启动器配置已保存。\n\n"
                    f"�?如果你是主机：请先在游戏中创建存档，\n"
                    f"  然后在游戏管理页面重新配置。\n\n"
                    f"�?如果你是客机：请连接到网络，\n"
                    f"  等待接收主机分享的存档�?
                )
                return
            
            # 找到了存档，但这里改为可选操�?
            # 保存启动器配�?
            self.config_data["minecraft_config"] = {
                "minecraft_dir": minecraft_dir,
                "launcher_type": launcher_type
            }
            ConfigCache.save(self.config_data)
            
            # 询问用户选择角色：主机还是客�?
            from PyQt5.QtWidgets import QMessageBox
            
            msg_box = MessageBox.create_custom(
                self,
                "选择角色",
                f"已保�?Minecraft 启动器配置\n\n"
                f"找到 {len(all_saves)} 个存档\n\n"
                f"请选择你的角色�?,
                "�?主机模式：选择要分享的存档（其他玩家可以接收）\n"
                "�?客机模式：接收其他玩家分享的存档（自动同步）"
            )
            
            host_btn = msg_box.addButton("🎮 主机模式", QMessageBox.YesRole)
            client_btn = msg_box.addButton("📥 客机模式", QMessageBox.NoRole)
            msg_box.setDefaultButton(client_btn)
            
            msg_box.exec_()
            
            if msg_box.clickedButton() == host_btn:
                # 主机模式：选择要分享的存档
                self.show_saves_select_dialog(all_saves, minecraft_dir, launcher_type)
            else:
                # 客机模式：等待接收同�?
                MessageBox.show_info(
                    self,
                    "客机模式",
                    "�?启动器配置完成！\n\n"
                    "您已进入客机模式，将自动接收其他玩家分享的存档。\n\n"
                    "📌 下一步：\n"
                    "请确保已连接到网络（首页 - 网络管理），\n"
                    "然后等待主机玩家分享存档即可�?
                )
                # 刷新页面
                self.load_game_list()
                self.show_minecraft_page()
                
        except Exception as e:
            logger.error(f"处理启动器文件时出错: {e}", exc_info=True)
            MessageBox.show_error(self, "错误", f"处理启动器文件失败：\n\n{str(e)}")
    
    def show_saves_select_dialog(self, saves, minecraft_dir, launcher_type):
        """显示存档选择对话�?- 支持多�?""
        save_dialog = QDialog(self)
        save_dialog.setWindowTitle("选择要同步的存档")
        save_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        save_dialog.setAttribute(Qt.WA_TranslucentBackground)
        save_dialog.setModal(True)
        save_dialog.resize(500, 550)
        
        # 主容�?
        main_container = QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(save_dialog)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel(f"选择要同步的存档 ({launcher_type})")
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(title_label)
        
        # 提示信息
        info_label = QLabel(f"💡 找到 {len(saves)} 个存档，请勾选需要同步的存档")
        info_label.setStyleSheet("""
            color: #666666;
            font-size: 13px;
            padding: 8px;
            background: #f5f5f5;
            border-radius: 4px;
            margin-bottom: 5px;
        """)
        layout.addWidget(info_label)
        
        # 存档列表（使�?QListWidget 支持多选）
        save_list = QListWidget()
        save_list.setSelectionMode(QListWidget.MultiSelection)
        save_list.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 4px;
                margin: 2px;
                border: 1px solid transparent;
            }
            QListWidget::item:selected {
                background: #e8f5e9;
                color: #333333;
                border: 1px solid #07c160;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        
        # 添加存档�?
        for save in sorted(saves):
            item = QListWidgetItem(f"💾 {save}")
            save_list.addItem(item)
        
        layout.addWidget(save_list)
        
        # 快捷操作按钮
        quick_btn_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("全�?)
        select_all_btn.setFixedHeight(32)
        select_all_btn.setCursor(Qt.PointingHandCursor)
        select_all_btn.clicked.connect(save_list.selectAll)
        select_all_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 13px;
                padding: 0 15px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        
        clear_all_btn = QPushButton("清空")
        clear_all_btn.setFixedHeight(32)
        clear_all_btn.setCursor(Qt.PointingHandCursor)
        clear_all_btn.clicked.connect(save_list.clearSelection)
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 13px;
                padding: 0 15px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        
        quick_btn_layout.addWidget(select_all_btn)
        quick_btn_layout.addWidget(clear_all_btn)
        quick_btn_layout.addStretch()
        
        layout.addLayout(quick_btn_layout)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        confirm_btn = QPushButton("确定")
        confirm_btn.setFixedHeight(40)
        confirm_btn.setMinimumWidth(100)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(save_dialog.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        
        def confirm_saves():
            import os
            import re
            selected_items = save_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(save_dialog, "警告", "请至少选择一个存�?)
                return
            
            # 保存 Minecraft 配置
            self.config_data["minecraft_config"] = {
                "minecraft_dir": minecraft_dir,
                "launcher_type": launcher_type
            }
            
            # 获取当前游戏列表
            game_list = self.config_data.get("game_list", [])
            
            # 添加所有选中的存�?
            added_count = 0
            for item in selected_items:
                # 移除前面�?"💾 " 前缀
                selected_save = item.text().replace("💾 ", "")
                
                # 解析存档名和版本
                # 格式: "存档�?[版本名]" �?"存档�?
                match = re.match(r"(.+?) \[(.+?)\]$", selected_save)
                if match:
                    # 版本隔离存档
                    save_name = match.group(1)
                    version = match.group(2)
                    save_path = os.path.join(minecraft_dir, "versions", version, "saves", save_name)
                else:
                    # 标准存档
                    save_name = selected_save
                    version = "通用"
                    save_path = os.path.join(minecraft_dir, "saves", save_name)
                
                # 检查是否已存在
                exists = any(
                    game.get("type") == "minecraft" and 
                    game.get("path") == save_path
                    for game in game_list
                )
                
                if not exists:
                    # 生成显示名称和同步路�?
                    if version == "通用":
                        display_name = f"Minecraft - {save_name}"
                        relative_path = f"saves/{save_name}"  # 标准存档，只同步存档
                        sync_type = "save"
                    else:
                        display_name = f"Minecraft - {save_name} ({version})"
                        relative_path = f"versions/{version}"  # 版本隔离，同步整个版本目�?
                        sync_type = "version"
                    
                    game_list.append({
                        "name": display_name,
                        "path": save_path,  # 本地绝对路径（仅用于本地显示�?
                        "relative_path": relative_path,  # 相对路径（用于同步）
                        "sync_type": sync_type,  # 同步类型
                        "type": "minecraft",
                        "launcher": launcher_type,
                        "save_name": save_name,
                        "version": version,
                        "minecraft_dir": minecraft_dir
                    })
                    added_count += 1
            
            # 保存配置
            self.config_data["game_list"] = game_list
            ConfigCache.save(self.config_data)
            self.load_game_list()
            
            # 提示用户
            if added_count > 0:
                QMessageBox.information(
                    save_dialog, 
                    "成功", 
                    f"成功添加 {added_count} 个存档到同步列表"
                )
            else:
                QMessageBox.information(
                    save_dialog, 
                    "提示", 
                    "所选存档已存在，未添加新存�?
                )
            
            save_dialog.accept()
        
        confirm_btn.clicked.connect(confirm_saves)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        
        layout.addLayout(btn_layout)
        
        container_layout.addWidget(main_container)
        
        # 居中显示
        save_dialog.adjustSize()
        if self.isVisible():
            parent_rect = self.frameGeometry()
            dialog_rect = save_dialog.frameGeometry()
            center_point = parent_rect.center()
            dialog_rect.moveCenter(center_point)
            save_dialog.move(dialog_rect.topLeft())
        
        save_dialog.exec_()
    
    def add_normal_game(self, parent_dialog):
        """添加普通游�?""
        parent_dialog.close()
        
        folder = QFileDialog.getExistingDirectory(self, "选择游戏存档目录")
        if folder:
            name, ok = QInputDialog.getText(self, "游戏名称", "请输入游戏名�?")
            
            if ok and name:
                game_list = self.config_data.get("game_list", [])
                game_list.append({
                    "name": name,
                    "path": folder,
                    "type": "normal"
                })
                self.config_data["game_list"] = game_list
                ConfigCache.save(self.config_data)
                self.load_game_list()
    
    def remove_game(self):
        """移除游戏"""
        current_item = self.game_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请选择要移除的游戏")
            return
        
        row = self.game_list.row(current_item)
        game_list = self.config_data.get("game_list", [])
        game_list.pop(row)
        self.config_data["game_list"] = game_list
        ConfigCache.save(self.config_data)
        self.load_game_list()
    
    def create_title_bar(self):
        """创建自定义标题栏"""
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(50)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(0)
        
        # Logo和标�?
        title_label = QLabel("🎮 LanGameSync")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # 最小化按钮
        min_btn = QPushButton("�?)
        min_btn.setObjectName("minBtn")
        min_btn.setFixedSize(45, 50)
        min_btn.clicked.connect(self.showMinimized)
        min_btn.setStyleSheet("""
            QPushButton#minBtn {
                background: transparent;
                color: #ffffff;
                border: none;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton#minBtn:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(min_btn)
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(45, 50)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton#closeBtn {
                background: transparent;
                color: #ffffff;
                border: none;
                font-size: 28px;
                font-weight: bold;
            }
            QPushButton#closeBtn:hover {
                background: #e81123;
            }
        """)
        layout.addWidget(close_btn)
        
        return title_bar
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            # 只在标题栏区域允许拖�?
            if event.pos().y() <= 50:
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.drag_position = None
    
    def create_menu(self):
        """创建菜单�?""
        menubar = self.menuBar()
        
        # 网络管理菜单（当前主要功能）
        network_menu = menubar.addMenu("网络管理")
        
        connect_action = QAction("连接网络", self)
        connect_action.triggered.connect(self.connect_to_network)
        network_menu.addAction(connect_action)
        
        disconnect_action = QAction("断开网络", self)
        disconnect_action.triggered.connect(self.disconnect_from_network)
        network_menu.addAction(disconnect_action)
        
        network_menu.addSeparator()
        
        log_action = QAction("查看运行日志", self)
        log_action.triggered.connect(self.show_log_dialog)
        network_menu.addAction(log_action)
        
        # 游戏管理菜单（待开发）
        game_menu = menubar.addMenu("游戏管理")
        
        placeholder_action = QAction("功能开发中...", self)
        placeholder_action.setEnabled(False)
        game_menu.addAction(placeholder_action)
    
    def create_network_group(self):
        """创建网络管理�?- 微信风格"""
        group = QWidget()
        group.setObjectName("networkGroup")
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 20, 25, 20)
        
        # 节点设置标题
        node_title = QLabel("节点设置")
        node_title.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        layout.addWidget(node_title)
        
        # 节点选择
        peer_layout = QHBoxLayout()
        peer_layout.setSpacing(10)
        
        peer_label = QLabel("节点选择")
        peer_label.setMinimumWidth(80)
        peer_label.setStyleSheet("color: #333333; font-size: 14px;")
        peer_layout.addWidget(peer_label)
        
        # 下拉�?
        self.peer_combo = QComboBox()
        self.peer_combo.setEditable(False)
        self.peer_combo.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
                color: #333333;
                min-height: 20px;
            }
            QComboBox:hover {
                border: 1px solid #07c160;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #999999;
                margin-right: 10px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #07c160;
            }
        """)
        self.load_peer_list()
        peer_layout.addWidget(self.peer_combo, 1)  # 占据剩余空间
        
        # 管理按钮（小按钮�?
        manage_btn = QPushButton("管理")
        manage_btn.setFixedSize(60, 40)
        manage_btn.setCursor(Qt.PointingHandCursor)
        manage_btn.clicked.connect(self.show_peer_manager)
        manage_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #07c160;
                color: #ffffff;
                border-color: #07c160;
            }
        """)
        peer_layout.addWidget(manage_btn)
        
        layout.addLayout(peer_layout)
        
        # 添加间距替代分隔�?
        layout.addSpacing(20)
        
        # 网络设置标题
        title = QLabel("网络设置")
        title.setStyleSheet("""
            color: #333333;
            font-size: 18px;
            font-weight: bold;
            padding-top: 5px;
            padding-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # 房间名输�?
        room_layout = QHBoxLayout()
        room_label = QLabel("房间名称")
        room_label.setMinimumWidth(80)
        room_label.setStyleSheet("color: #333333; font-size: 14px;")
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("输入房间名称")
        self.room_input.setText(self.config_data.get("room_name", "langamesync-network"))
        self.room_input.textChanged.connect(self.save_config)
        room_layout.addWidget(room_label)
        room_layout.addWidget(self.room_input)
        layout.addLayout(room_layout)
        
        # 密码输入
        password_layout = QHBoxLayout()
        password_label = QLabel("房间密码")
        password_label.setMinimumWidth(80)
        password_label.setStyleSheet("color: #333333; font-size: 14px;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("输入房间密码")
        self.password_input.setText(self.config_data.get("password", "langamesync-2025"))
        self.password_input.textChanged.connect(self.save_config)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # 连接按钮
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        
        self.connect_btn = QPushButton("连接到网�?)
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.clicked.connect(self.connect_to_network)
        self.connect_btn.setMinimumSize(160, 45)
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        btn_container.addWidget(self.connect_btn)
        
        btn_container.addStretch()
        layout.addLayout(btn_container)
        
        group.setLayout(layout)
        return group
    
    def load_peer_list(self):
        """加载节点列表"""
        self.peer_combo.clear()
        
        # 从配置加载自定义节点
        peer_list = self.config_data.get("peer_list", [])
        
        # 如果没有配置，添加默认节�?
        if not peer_list:
            peer_list = [
                {"name": "官方节点（推荐）", "peers": "tcp://public.easytier.cn:11010,udp://public.easytier.cn:11010"},
                {"name": "不使用公共节�?, "peers": ""}
            ]
            self.config_data["peer_list"] = peer_list
            ConfigCache.save(self.config_data)
        
        # 添加到下拉框
        for peer_config in peer_list:
            self.peer_combo.addItem(peer_config["name"], peer_config["peers"])
        
        # 选中上次使用的节�?
        last_peer = self.config_data.get("selected_peer", 0)
        if last_peer < self.peer_combo.count():
            self.peer_combo.setCurrentIndex(last_peer)
        
        # 连接信号
        self.peer_combo.currentIndexChanged.connect(self.on_peer_changed)
    
    def on_peer_changed(self, index):
        """节点选择改变"""
        self.config_data["selected_peer"] = index
        ConfigCache.save(self.config_data)
    
    def show_peer_manager(self):
        """显示节点管理对话�?""
        dialog = PeerManagerDialog(self, self.config_data)
        if dialog.exec_() == QDialog.Accepted:
            # 重新加载节点列表
            self.load_peer_list()
    
    def create_clients_group(self):
        """创建客户端信息表格组 - 微信风格"""
        group = QWidget()
        group.setObjectName("clientsGroup")
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("网络中的设备")
        title.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)
        
        # 创建表格
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(3)
        self.clients_table.setHorizontalHeaderLabels(["主机�?, "IP地址", "延迟"])
        
        # 设置表格样式
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.clients_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.clients_table.setAlternatingRowColors(False)
        self.clients_table.verticalHeader().setVisible(False)
        self.clients_table.setShowGrid(False)
        self.clients_table.setMinimumHeight(250)
        
        layout.addWidget(self.clients_table)
        
        group.setLayout(layout)
        return group
    
    def init_services(self):
        """初始化后台服�?""
        # 启动Syncthing
        logger.info("正在初始化Syncthing...")
    
    def connect_to_network(self):
        """连接到网络（异步�?""
        if self.is_connected:
            QMessageBox.information(self, "提示", "已经连接到网络了")
            return
        
        room_name = self.room_input.text().strip()
        password = self.password_input.text().strip()
        
        if not room_name or not password:
            QMessageBox.warning(self, "警告", "请输入房间名称和密码")
            return
        
        # 禁用连接按钮
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("连接�?..")
        
        # 更新配置
        Config.EASYTIER_NETWORK_NAME = room_name
        Config.EASYTIER_NETWORK_SECRET = password
        
        # 更新公共节点配置
        peer_text = self.peer_combo.currentData()
        if peer_text:
            # 按逗号分割并去除空�?
            Config.EASYTIER_PUBLIC_PEERS = [p.strip() for p in peer_text.split(',') if p.strip()]
        else:
            # 不使用公共节�?
            Config.EASYTIER_PUBLIC_PEERS = []
        
        # 创建连接线程
        self.connect_thread = ConnectThread(self.controller, room_name, password)
        self.connect_thread.progress.connect(self.on_connect_progress)
        self.connect_thread.connected.connect(self.on_connected)
        self.connect_thread.start()
    
    def on_connect_progress(self, message):
        """连接进度回调"""
        self.status_label.setText(f"状�? {message}")
    
    def on_connected(self, success, message):
        """连接完成回调"""
        if success:
            self.is_connected = True
            virtual_ip = message
            self.connect_btn.setText("断开连接")
            self.connect_btn.setEnabled(True)
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.disconnect_from_network)
            self.connect_btn.setStyleSheet("""
                QPushButton#connectBtn {
                    background: #fa5151;
                    color: #ffffff;
                    border: none;
                }
                QPushButton#connectBtn:hover {
                    background: #e04444;
                }
            """)
            self.status_label.setText(f"状�? 已连接到房间 '{self.room_input.text()}' | 虚拟IP: {virtual_ip}")
            
            # 初始�?discovered_devices，添加本�?
            self.controller.discovered_devices = [{
                "ip": virtual_ip,
                "device_id": self.controller.syncthing.device_id,
                "name": "本机",
                "hostname": "localhost"
            }]
            
            # 启动设备监听
            self.scan_timer = QTimer()
            self.scan_timer.timeout.connect(self.background_scan_devices)
            self.scan_timer.start(5000)  # 初始5�?
            
            # 播放连接成功动画
            self.play_connect_animation()
        else:
            self.connect_btn.setText("连接到网�?)
            self.connect_btn.setEnabled(True)
            self.status_label.setText(f"状�? 连接失败 - {message}")
            QMessageBox.critical(self, "错误", f"连接失败: {message}")
    
    def disconnect_from_network(self):
        """断开网络"""
        if not self.is_connected:
            return
        
        # 停止服务
        self.controller.easytier.stop()
        self.is_connected = False
        
        # 恢复按钮状�?
        self.connect_btn.setText("连接到网�?)
        self.connect_btn.setEnabled(True)
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.connect_to_network)
        self.connect_btn.setStyleSheet("")  # 恢复默认样式
        
        self.status_label.setText("状�? 已断开")
        self.clients_table.setRowCount(0)
        
        if hasattr(self, 'scan_timer'):
            self.scan_timer.stop()
    
    def background_scan_devices(self):
        """后台监听设备变化（异步）"""
        try:
            self.scan_count += 1
            
            # 快速监听阶段：�?次（30秒），每5秒一�?
            if self.scan_count == 6:
                remote_device_count = len([d for d in self.controller.discovered_devices if d.get('name') != '本机'])
                
                if remote_device_count > 0:
                    self.scan_timer.setInterval(15000)
                else:
                    self.scan_timer.setInterval(30000)
            
            # 如果上一次扫描还在进行，跳过本次
            if self.scan_thread and self.scan_thread.isRunning():
                return
            
            # 创建新的扫描线程
            self.scan_thread = ScanThread(self.controller)
            self.scan_thread.peers_found.connect(self.on_peers_found)
            self.scan_thread.start()
                        
        except Exception as e:
            logger.error(f"后台扫描设备失败: {e}")
    
    def on_peers_found(self, peers):
        """扫描结果回调（在主线程中处理�?""
        try:
            if not peers:
                return
            
            # 检测变�?
            current_peer_ips = {p.get('ipv4') for p in peers if p.get('ipv4')}
            new_ips = current_peer_ips - self.last_peer_ips
            removed_ips = self.last_peer_ips - current_peer_ips
            
            # 有设备变化才处理
            if new_ips or removed_ips:
                # 更新记录
                self.last_peer_ips = current_peer_ips
                
                # 处理新设备（获取device_id并添加到discovered_devices�?
                for peer in peers:
                    peer_ip = peer.get('ipv4', '')
                    if peer_ip in new_ips:
                        # 检查是否已存在
                        existing_ips = {d.get('ip') for d in self.controller.discovered_devices}
                        if peer_ip not in existing_ips and peer_ip != self.controller.easytier.virtual_ip:
                            # 尝试获取设备ID
                            hostname = peer.get('hostname', '')
                            logger.info(f"发现新设�? {hostname} ({peer_ip})")
                            
                            # 异步获取device_id
                            try:
                                device_id = self.controller._get_remote_device_id(peer_ip, timeout=5)
                                if device_id and device_id != self.controller.syncthing.device_id:
                                    # 使用主机名作为设备名�?
                                    device_name = hostname or f"Device-{peer_ip.split('.')[-1]}"
                                    
                                    # 添加到discovered_devices
                                    self.controller.discovered_devices.append({
                                        "ip": peer_ip,
                                        "device_id": device_id,
                                        "name": device_name,
                                        "hostname": hostname,
                                        "latency": peer.get('latency', '0')
                                    })
                                    
                                    # 添加到Syncthing
                                    self.controller.syncthing.add_device(device_id, device_name)
                                    logger.info(f"成功添加设备: {device_name} ({device_id[:7]}...)")
                                    
                                    # 提高扫描频率
                                    if self.scan_timer.interval() > 15000:
                                        self.scan_timer.setInterval(15000)
                            except Exception as e:
                                logger.error(f"获取设备ID失败: {e}")
            
            # 更新表格（不阻塞�?
            self.update_clients_table_from_cache(peers)
                        
        except Exception as e:
            logger.error(f"处理扫描结果失败: {e}")
    
    def update_clients_table_from_cache(self, peers):
        """从缓存的peer数据更新表格（不阻塞�?""
        try:
            # 清空表格
            self.clients_table.setRowCount(0)
            
            # 填充数据
            for peer in peers:
                ipv4 = peer.get('ipv4', '')
                hostname = peer.get('hostname', '')
                latency = peer.get('latency', '')
                
                if not ipv4:
                    continue
                
                row = self.clients_table.rowCount()
                self.clients_table.insertRow(row)
                
                # 主机�?
                item_hostname = QTableWidgetItem(hostname)
                item_hostname.setTextAlignment(Qt.AlignCenter)
                self.clients_table.setItem(row, 0, item_hostname)
                
                # IP地址
                item_ip = QTableWidgetItem(ipv4)
                item_ip.setTextAlignment(Qt.AlignCenter)
                self.clients_table.setItem(row, 1, item_ip)
                
                # 延迟
                latency_text = f"{latency}ms" if latency != '-' else "本机"
                item_latency = QTableWidgetItem(latency_text)
                item_latency.setTextAlignment(Qt.AlignCenter)
                
                # 根据延迟设置颜色
                if latency == '-':
                    item_latency.setForeground(QColor("#4caf50"))  # 绿色（本机）
                elif latency != '' and float(latency) < 50:
                    item_latency.setForeground(QColor("#2196f3"))  # 蓝色（低延迟�?
                elif latency != '' and float(latency) < 100:
                    item_latency.setForeground(QColor("#ff9800"))  # 橙色（中延迟�?
                else:
                    item_latency.setForeground(QColor("#f44336"))  # 红色（高延迟�?
                
                self.clients_table.setItem(row, 2, item_latency)
                
        except Exception as e:
            logger.error(f"更新客户端表格失�? {e}")
    
    def play_connect_animation(self):
        """播放连接成功动画"""
        # 状态标签淡入动�?
        animation = QPropertyAnimation(self.status_label, b"geometry")
        animation.setDuration(500)
        animation.setEasingCurve(QEasingCurve.OutBounce)
        
        # 获取当前几何信息
        current_geo = self.status_label.geometry()
        
        # 设置动画
        animation.setStartValue(QRect(
            current_geo.x(),
            current_geo.y() - 20,
            current_geo.width(),
            current_geo.height()
        ))
        animation.setEndValue(current_geo)
        animation.start()
    
    def show_log_dialog(self):
        """显示运行日志对话�?""
        if self.log_dialog is None:
            self.log_dialog = LogDialog(self)
        
        # 每次显示时刷新日�?
        self.log_dialog.load_log()
        self.log_dialog.show()
        self.log_dialog.raise_()
        self.log_dialog.activateWindow()
    
    def save_config(self):
        """保存配置"""
        config = {
            "room_name": self.room_input.text(),
            "password": self.password_input.text(),
        }
        # 合并现有配置
        self.config_data.update(config)
        ConfigCache.save(self.config_data)
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        # 保存配置
        self.save_config()
        
        # 停止服务
        self.controller.easytier.stop()
        self.controller.syncthing.stop()
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # 设置应用字体
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

