"""
消息框辅助类
统一管理所有消息框调用，避免打包后的作用域问题
"""
from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt


class MessageBox:
    """消息框辅助类（静态方法）"""
    
    @staticmethod
    def show_warning(parent, title, message):
        """显示警告消息框"""
        return MessageBox._show_custom(parent, title, message, "warning")
    
    @staticmethod
    def show_info(parent, title, message):
        """显示信息消息框"""
        return MessageBox._show_custom(parent, title, message, "info")
    
    @staticmethod
    def show_error(parent, title, message):
        """显示错误消息框"""
        return MessageBox._show_custom(parent, title, message, "error")
    
    @staticmethod
    def show_question(parent, title, message, buttons=None):
        """显示确认消息框"""
        if buttons is None:
            buttons = QMessageBox.Yes | QMessageBox.No
        return QMessageBox.question(parent, title, message, buttons)
    
    @staticmethod
    def _show_custom(parent, title, message, msg_type="info"):
        """显示自定义样式的消息框"""
        dialog = QDialog(parent)
        dialog.setWindowTitle("")
        dialog.setModal(True)
        dialog.setFixedWidth(400)
        
        # 设置无边框窗口
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        
        # 主容器
        main_container = QWidget()
        main_container.setObjectName("msgContainer")
        main_container.setStyleSheet("""
            #msgContainer {
                background: #ffffff;
                border-radius: 8px;
                border: 1px solid #d0d0d0;
            }
        """)
        
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QWidget()
        title_bar.setObjectName("msgTitleBar")
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("""
            #msgTitleBar {
                background: #2e2e2e;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        
        # 根据类型显示不同emoji
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        title_text = f"{emoji_map.get(msg_type, 'ℹ️')} {title}"
        
        title_label = QLabel(title_text)
        title_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        container_layout.addWidget(title_bar)
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(25, 25, 25, 20)
        content_layout.setSpacing(20)
        
        # 消息文本
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            line-height: 1.6;
        """)
        content_layout.addWidget(msg_label)
        
        # 确定按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.setFixedSize(100, 40)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(dialog.accept)
        
        if msg_type == "error":
            ok_btn.setStyleSheet("""
                QPushButton {
                    background: #fa5151;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #e84545;
                }
            """)
        else:
            ok_btn.setStyleSheet("""
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
        
        btn_layout.addWidget(ok_btn)
        content_layout.addLayout(btn_layout)
        
        container_layout.addWidget(content_widget)
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_container)
        
        return dialog.exec_()
    
    @staticmethod
    def create_custom(parent, title, text, info_text=None):
        """创建自定义消息框"""
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        if info_text:
            msg_box.setInformativeText(info_text)
        return msg_box
