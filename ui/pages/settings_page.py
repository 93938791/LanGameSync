"""设置页面"""
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap
from qfluentwidgets import (
    ScrollArea, CardWidget, BodyLabel, SubtitleLabel
)

from utils.logger import Logger

logger = Logger().get_logger("SettingsInterface")


class SettingsInterface(ScrollArea):
    """设置界面"""
    
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        self.view = QWidget()
        self.vBoxLayout = QVBoxLayout(self.view)
        
        # 设置全局唯一的对象名称（必须）
        self.setObjectName("settingsInterface")
        
        # 设置样式
        self.setStyleSheet("QScrollArea {border: none; background: transparent;}")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        # 设置布局边距
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.setSpacing(20)
        
        # 创建内容
        self.create_content()
    
    def create_content(self):
        """创建内容"""
        # 页面标题
        title = SubtitleLabel("设置")
        title.setObjectName("pageTitle")
        title.setStyleSheet("background: transparent; border: none;")
        self.vBoxLayout.addWidget(title)
        
        # 主内容卡片
        content_card = self.create_content_card()
        self.vBoxLayout.addWidget(content_card, 1)  # 占据剩余空间
    
    def create_content_card(self):
        """创建主内容卡片"""
        card = CardWidget()
        card.setStyleSheet("""
            CardWidget {
                background: white;
                border: none;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(0)
        
        # 右上角文字：什么是设置？
        hint_label = BodyLabel("什么是设置？")
        hint_label.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 13px;
                background: transparent;
                border: none;
            }
        """)
        hint_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        card_layout.addWidget(hint_label)
        
        # 中间显示图片
        image_container = QWidget()
        image_container.setStyleSheet("background: transparent; border: none;")
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 20, 0, 20)
        
        # 加载图片
        image_label = QLabel()
        image_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'resources', 'icons', 'paidaxin.png'
        )
        
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # 设置图片大小（保持比例，最大宽度400px）
            scaled_pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
        else:
            image_label.setText("图片不存在")
        
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("background: transparent; border: none;")
        image_layout.addWidget(image_label)
        
        card_layout.addWidget(image_container, 1)  # 占据中间空间
        
        return card
