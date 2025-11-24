"""
节点管理对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QWidget, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
from utils.config_cache import ConfigCache


class PeerManagerDialog(QDialog):
    """节点管理对话框"""
    
    def __init__(self, parent=None, config_data=None):
        super().__init__(parent)
        self.config_data = config_data if config_data else {}
        self.setWindowTitle("节点管理")
        self.setModal(True)
        self.resize(700, 500)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()
        self.drag_position = None
    
    def init_ui(self):
        # 主容器
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
        
        # 标题栏
        title_bar = self.create_title_bar()
        container_layout.addWidget(title_bar)
        
        # 内容区域
        content = self.create_content()
        container_layout.addWidget(content)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_container)
    
    def create_title_bar(self):
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
        
        return title_bar
    
    def create_content(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        # 说明文本
        info_label = QLabel("💡 管理公共节点，用于跨网络 NAT 穿透连接")
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
        
        from .peer_edit import PeerEditDialog
        
        add_btn = QPushButton("新增节点")
        add_btn.setFixedHeight(40)
        add_btn.setMinimumWidth(120)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(lambda: self.add_peer(PeerEditDialog))
        add_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedHeight(40)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.edit_peer(PeerEditDialog))
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
            }
        """)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("完成")
        close_btn.setFixedHeight(40)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
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
        btn_layout.addWidget(close_btn)
        
        content_layout.addLayout(btn_layout)
        
        return content_widget
    
    def load_peers(self):
        """加载节点列表"""
        self.peer_list.clear()
        peer_list = self.config_data.get("peer_list", [])
        
        for peer in peer_list:
            item_text = f"{peer['name']}\n{peer['peers'] if peer['peers'] else '（不使用节点）'}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, peer)
            self.peer_list.addItem(item)
    
    def add_peer(self, PeerEditDialog):
        """新增节点"""
        dialog = PeerEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, peers = dialog.get_data()
            peer_list = self.config_data.get("peer_list", [])
            peer_list.append({"name": name, "peers": peers})
            self.config_data["peer_list"] = peer_list
            ConfigCache.save(self.config_data)
            self.load_peers()
    
    def edit_peer(self, PeerEditDialog):
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
