"""
节点管理对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from qfluentwidgets import (
    MessageBox, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, InfoBar, InfoBarPosition,
    CardWidget, IconWidget, FluentIcon
)
import os
from utils.config_cache import ConfigCache


class PeerManagerDialog(QDialog):
    """节点管理对话框"""
    
    def __init__(self, parent=None, config_data=None):
        super().__init__(parent)
        self.config_data = config_data if config_data else {}
        self.setWindowTitle("节点管理")
        self.setModal(True)
        self.resize(750, 550)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置 Fluent 风格背景
        self.setStyleSheet("""
            QDialog {
                background: transparent;
            }
        """)
        
        self.init_ui()
        self.drag_position = None
    
    def init_ui(self):
        # 主容器 - 使用 CardWidget
        main_container = CardWidget()
        main_container.setStyleSheet("""
            CardWidget {
                background: white;
                border-radius: 10px;
            }
        """)
        
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 标题栏
        title_bar = self.create_title_bar()
        container_layout.addWidget(title_bar)
        
        # 分割线
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: #e0e0e0;")
        container_layout.addWidget(separator)
        
        # 内容区域
        content = self.create_content()
        container_layout.addWidget(content)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(main_container)
    
    def create_title_bar(self):
        title_bar = QWidget()
        title_bar.setFixedHeight(56)
        title_bar.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(24, 0, 16, 0)
        
        # 标题图标
        icon_widget = IconWidget(FluentIcon.GLOBE)
        icon_widget.setFixedSize(24, 24)
        title_layout.addWidget(icon_widget)
        
        # 标题文本
        title_label = SubtitleLabel("节点管理")
        title_label.setStyleSheet("font-weight: 600; margin-left: 8px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 关闭按钮
        close_btn = PushButton(FluentIcon.CLOSE, "")
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            PushButton {
                background: transparent;
                border: none;
                border-radius: 5px;
            }
            PushButton:hover {
                background: rgba(0, 0, 0, 0.05);
            }
            PushButton:pressed {
                background: rgba(0, 0, 0, 0.1);
            }
        """)
        title_layout.addWidget(close_btn)
        
        return title_bar
    
    def create_content(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)
        
        # 说明文本 - 使用 Fluent 风格卡片
        info_card = CardWidget()
        info_card.setStyleSheet("""
            CardWidget {
                background: #f3f3f3;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        
        info_icon = IconWidget(FluentIcon.INFO)
        info_icon.setFixedSize(20, 20)
        info_layout.addWidget(info_icon)
        
        info_label = BodyLabel("管理公共节点，用于跨网络 NAT 穿透连接")
        info_label.setStyleSheet("color: #666666; margin-left: 8px;")
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        
        content_layout.addWidget(info_card)
        
        # 节点列表
        self.peer_list = QListWidget()
        self.peer_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 14px 12px;
                border-radius: 4px;
                margin: 2px;
                border: none;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 120, 212, 0.1),
                    stop:1 rgba(0, 120, 212, 0.05));
                color: #0078d4;
                border-left: 3px solid #0078d4;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        self.load_peers()
        content_layout.addWidget(self.peer_list)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        from .peer_edit import PeerEditDialog
        
        add_btn = PrimaryPushButton(FluentIcon.ADD, "新增节点")
        add_btn.setFixedHeight(36)
        add_btn.setMinimumWidth(110)
        add_btn.clicked.connect(lambda: self.add_peer(PeerEditDialog))
        btn_layout.addWidget(add_btn)
        
        edit_btn = PushButton(FluentIcon.EDIT, "编辑")
        edit_btn.setFixedHeight(36)
        edit_btn.clicked.connect(lambda: self.edit_peer(PeerEditDialog))
        btn_layout.addWidget(edit_btn)
        
        delete_btn = PushButton(FluentIcon.DELETE, "删除")
        delete_btn.setFixedHeight(36)
        delete_btn.clicked.connect(self.delete_peer)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        close_btn = PushButton("完成")
        close_btn.setFixedHeight(36)
        close_btn.setMinimumWidth(90)
        close_btn.clicked.connect(self.accept)
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
            InfoBar.warning(
                title='提示',
                content="请选择要编辑的节点",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
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
            InfoBar.warning(
                title='提示',
                content="请选择要删除的节点",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 使用 Fluent 风格的确认对话框
        peer = current_item.data(Qt.UserRole)
        w = MessageBox(
            "确认删除",
            f"确定要删除节点 \"{peer['name']}\" 吗？",
            self
        )
        if w.exec_():
            row = self.peer_list.row(current_item)
            peer_list = self.config_data.get("peer_list", [])
            peer_list.pop(row)
            self.config_data["peer_list"] = peer_list
            ConfigCache.save(self.config_data)
            self.load_peers()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= 56:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.drag_position = None
