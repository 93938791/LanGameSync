"""
节点编辑对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget
)
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    LineEdit, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, CardWidget, IconWidget, FluentIcon
)


class PeerEditDialog(QDialog):
    """节点编辑对话框"""
    
    def __init__(self, parent=None, name="", peers=""):
        super().__init__(parent)
        self.setWindowTitle("编辑节点")
        self.setModal(True)
        self.resize(520, 340)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置 Fluent 风格背景
        self.setStyleSheet("""
            QDialog {
                background: transparent;
            }
        """)
        
        self.name_input = None
        self.peers_input = None
        
        self.init_ui(name, peers)
        self.drag_position = None
    
    def init_ui(self, name, peers):
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
        content = self.create_content(name, peers)
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
        icon_widget = IconWidget(FluentIcon.EDIT)
        icon_widget.setFixedSize(24, 24)
        title_layout.addWidget(icon_widget)
        
        # 标题文本
        title_label = SubtitleLabel("编辑节点")
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
    
    def create_content(self, name, peers):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)
        
        # 名称输入
        name_layout = QVBoxLayout()
        name_layout.setSpacing(8)
        name_label = BodyLabel("节点名称")
        name_label.setStyleSheet("font-weight: 600;")
        name_layout.addWidget(name_label)
        
        self.name_input = LineEdit()
        self.name_input.setText(name)
        self.name_input.setPlaceholderText("请输入节点名称")
        self.name_input.setFixedHeight(36)
        name_layout.addWidget(self.name_input)
        content_layout.addLayout(name_layout)
        
        # Peers输入
        peers_layout = QVBoxLayout()
        peers_layout.setSpacing(8)
        peers_label = BodyLabel("Peers 地址")
        peers_label.setStyleSheet("font-weight: 600;")
        peers_layout.addWidget(peers_label)
        
        self.peers_input = LineEdit()
        self.peers_input.setText(peers)
        self.peers_input.setPlaceholderText("例如：tcp://39.104.85.218:11010")
        self.peers_input.setFixedHeight(36)
        peers_layout.addWidget(self.peers_input)
        
        # 提示文本
        hint_card = CardWidget()
        hint_card.setStyleSheet("""
            CardWidget {
                background: #f3f3f3;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        hint_layout = QHBoxLayout(hint_card)
        hint_layout.setContentsMargins(12, 8, 12, 8)
        
        hint_icon = IconWidget(FluentIcon.INFO)
        hint_icon.setFixedSize(16, 16)
        hint_layout.addWidget(hint_icon)
        
        hint_label = CaptionLabel("留空表示不使用公共节点")
        hint_label.setStyleSheet("color: #666666; margin-left: 6px;")
        hint_layout.addWidget(hint_label)
        hint_layout.addStretch()
        
        peers_layout.addWidget(hint_card)
        content_layout.addLayout(peers_layout)
        
        content_layout.addStretch()
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        cancel_btn = PushButton("取消")
        cancel_btn.setFixedSize(100, 36)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = PrimaryPushButton("保存")
        save_btn.setFixedSize(100, 36)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        content_layout.addLayout(btn_layout)
        
        return content_widget
    
    def get_data(self):
        """获取输入的数据"""
        return self.name_input.text().strip(), self.peers_input.text().strip()
    
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
