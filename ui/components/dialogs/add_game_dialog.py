"""
添加游戏对话框 - Fluent Design 风格
"""
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from qfluentwidgets import (
    CardWidget, SubtitleLabel, BodyLabel, PushButton,
    IconWidget, FluentIcon
)
from utils.logger import Logger

logger = Logger().get_logger("AddGameDialog")


class AddGameDialog(QDialog):
    """添加游戏对话框 - 选择游戏类型"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.game_type = None  # 'minecraft' 或 'other'
        
        self.setWindowTitle("添加游戏")
        self.setModal(True)
        self.setFixedSize(500, 340)
        
        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()
    
    def showEvent(self, event):
        """窗口显示时居中"""
        super().showEvent(event)
        self._center_window()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 主容器 - 使用 CardWidget
        container = CardWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(20)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        # 图标
        icon = IconWidget(FluentIcon.GAME)
        icon.setFixedSize(28, 28)
        title_layout.addWidget(icon)
        
        # 标题
        title_label = SubtitleLabel("选择游戏类型")
        title_label.setStyleSheet("font-weight: 600; margin-left: 8px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 关闭按钮
        close_btn = PushButton(FluentIcon.CLOSE, "")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            PushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            PushButton:hover {
                background: rgba(0, 0, 0, 0.06);
            }
            PushButton:pressed {
                background: rgba(0, 0, 0, 0.1);
            }
        """)
        title_layout.addWidget(close_btn)
        
        container_layout.addLayout(title_layout)
        
        # 提示文字
        hint_label = BodyLabel("请选择要添加的游戏类型")
        hint_label.setStyleSheet("color: #666666; font-size: 13px;")
        container_layout.addWidget(hint_label)
        
        # 我的世界按钮
        minecraft_card = self.create_game_card(
            icon_name="mc.png",
            title="我的世界",
            description="支持 HMCL 和 PCL2 启动器",
            game_type="minecraft"
        )
        container_layout.addWidget(minecraft_card)
        
        # 其他游戏按钮
        other_card = self.create_game_card(
            icon_name="game3.png",
            title="其他游戏",
            description="手动选择存档目录",
            game_type="other"
        )
        container_layout.addWidget(other_card)
        
        container_layout.addStretch()
        
        layout.addWidget(container)
    
    def _center_window(self):
        """居中显示窗口"""
        if self.parent():
            parent_geometry = self.parent().geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
        else:
            # 如果没有父窗口，使用屏幕中心
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)
    
    def create_game_card(self, icon_name, title, description, game_type):
        """创建游戏类型卡片"""
        card = GameTypeCard(game_type, self)
        card.setFixedHeight(80)
        card.setCursor(Qt.PointingHandCursor)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(16)
        
        # 游戏图标
        icon_label = QWidget()
        icon_label.setFixedSize(48, 48)
        icon_label.setStyleSheet("""
            QWidget {
                background: #f5f5f5;
                border-radius: 8px;
            }
        """)
        
        icon_layout = QVBoxLayout(icon_label)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        # 加载图标
        from PyQt5.QtWidgets import QLabel
        pixmap_label = QLabel()
        pixmap_label.setAlignment(Qt.AlignCenter)
        
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons')
        icon_path = os.path.join(icon_dir, icon_name)
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pixmap_label.setPixmap(pixmap)
        pixmap_label.setStyleSheet("background: transparent;")
        
        icon_layout.addWidget(pixmap_label)
        card_layout.addWidget(icon_label)
        
        # 文字信息
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = SubtitleLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 15px;")
        text_layout.addWidget(title_label)
        
        desc_label = BodyLabel(description)
        desc_label.setStyleSheet("color: #666666; font-size: 12px;")
        text_layout.addWidget(desc_label)
        
        card_layout.addLayout(text_layout)
        card_layout.addStretch()
        
        # 箭头图标
        arrow_icon = IconWidget(FluentIcon.CARE_RIGHT_SOLID)
        arrow_icon.setFixedSize(16, 16)
        card_layout.addWidget(arrow_icon)
        
        # 添加悬停效果
        card.setStyleSheet("""
            CardWidget:hover {
                background: #f5f5f5;
            }
        """)
        
        return card
    
    def select_game_type(self, game_type):
        """选择游戏类型"""
        self.game_type = game_type
        self.accept()


class GameTypeCard(CardWidget):
    """游戏类型卡片（自定义事件处理）"""
    
    def __init__(self, game_type, dialog):
        super().__init__()
        self.game_type = game_type
        self.dialog = dialog
    
    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.dialog.select_game_type(self.game_type)
        super().mousePressEvent(event)
