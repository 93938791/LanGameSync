"""
节点编辑对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QWidget
)
from PyQt5.QtCore import Qt


class PeerEditDialog(QDialog):
    """节点编辑对话框"""
    
    def __init__(self, parent=None, name="", peers=""):
        super().__init__(parent)
        self.setWindowTitle("编辑节点")
        self.setModal(True)
        self.resize(500, 280)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.name_input = None
        self.peers_input = None
        
        self.init_ui(name, peers)
        self.drag_position = None
    
    def init_ui(self, name, peers):
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
        content = self.create_content(name, peers)
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
        
        title_label = QLabel("✏️ 编辑节点")
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
    
    def create_content(self, name, peers):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(25, 20, 25, 20)
        content_layout.setSpacing(20)
        
        # 名称输入
        name_layout = QVBoxLayout()
        name_layout.setSpacing(8)
        name_label = QLabel("节点名称:")
        name_label.setStyleSheet("font-size: 14px; color: #333333; font-weight: bold;")
        name_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setText(name)
        self.name_input.setPlaceholderText("请输入节点名称")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #07c160;
            }
        """)
        name_layout.addWidget(self.name_input)
        content_layout.addLayout(name_layout)
        
        # Peers输入
        peers_layout = QVBoxLayout()
        peers_layout.setSpacing(8)
        peers_label = QLabel("Peers地址:")
        peers_label.setStyleSheet("font-size: 14px; color: #333333; font-weight: bold;")
        peers_layout.addWidget(peers_label)
        
        self.peers_input = QLineEdit()
        self.peers_input.setText(peers)
        self.peers_input.setPlaceholderText("wss://example.com:11011")
        self.peers_input.setStyleSheet("""
            QLineEdit {
                background: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #07c160;
            }
        """)
        peers_layout.addWidget(self.peers_input)
        
        # 提示文本
        hint_label = QLabel("💡 留空表示不使用公共节点")
        hint_label.setStyleSheet("color: #999999; font-size: 12px;")
        peers_layout.addWidget(hint_label)
        
        content_layout.addLayout(peers_layout)
        
        content_layout.addStretch()
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
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
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.setFixedSize(100, 40)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("""
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
        btn_layout.addWidget(save_btn)
        
        content_layout.addLayout(btn_layout)
        
        return content_widget
    
    def get_data(self):
        """获取输入的数据"""
        return self.name_input.text().strip(), self.peers_input.text().strip()
    
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
