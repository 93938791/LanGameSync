"""
编辑名称对话框
"""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap


class EditNameDialog(QDialog):
    """编辑名称对话框"""
    
    def __init__(self, parent, title, current_name):
        super().__init__(parent)
        self.new_name = None
        
        self.setWindowTitle("")
        self.setModal(True)
        self.setFixedSize(400, 180)
        
        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui(title, current_name)
    
    def init_ui(self, title, current_name):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 主容器
        container = QLabel()
        container.setStyleSheet("""
            QLabel {
                background: #ffffff;
                border-radius: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QLabel()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("""
            QLabel {
                background: #fafafa;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 10, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #2c2c2c;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons')
        close_icon_path = os.path.join(icon_dir, 'close.png')
        if os.path.exists(close_icon_path):
            close_btn.setIcon(QIcon(close_icon_path))
            close_btn.setIconSize(QPixmap(16, 16).size())
        else:
            close_btn.setText("✕")
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #666666;
                font-size: 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #f0f0f0;
                color: #333333;
            }
        """)
        title_layout.addWidget(close_btn)
        
        container_layout.addWidget(title_bar)
        
        # 内容区域
        content = QLabel()
        content.setStyleSheet("background: #ffffff;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(15)
        
        # 输入框
        self.name_input = QLineEdit()
        self.name_input.setText(current_name)
        self.name_input.selectAll()
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
                color: #2c2c2c;
            }
            QLineEdit:focus {
                border: 1px solid #07c160;
                background: #ffffff;
            }
        """)
        self.name_input.returnPressed.connect(self.accept_input)
        content_layout.addWidget(self.name_input)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(90, 36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #f5f5f5;
            }
        """)
        btn_layout.addWidget(cancel_btn)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.setFixedSize(90, 36)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(self.accept_input)
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #07c160;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #06ae56;
            }
        """)
        btn_layout.addWidget(ok_btn)
        
        content_layout.addLayout(btn_layout)
        
        container_layout.addWidget(content)
        
        layout.addWidget(container)
        
        # 自动聚焦输入框
        self.name_input.setFocus()
    
    def accept_input(self):
        """接受输入"""
        text = self.name_input.text().strip()
        if text:
            self.new_name = text
            self.accept()
