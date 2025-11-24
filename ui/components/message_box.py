"""
消息框辅助类
统一管理所有消息框调用，避免打包后的作用域问题
"""
from PyQt5.QtWidgets import QMessageBox


class MessageBox:
    """消息框辅助类（静态方法）"""
    
    @staticmethod
    def show_warning(parent, title, message):
        """显示警告消息框"""
        return QMessageBox.warning(parent, title, message)
    
    @staticmethod
    def show_info(parent, title, message):
        """显示信息消息框"""
        return QMessageBox.information(parent, title, message)
    
    @staticmethod
    def show_error(parent, title, message):
        """显示错误消息框"""
        return QMessageBox.critical(parent, title, message)
    
    @staticmethod
    def show_question(parent, title, message, buttons=None):
        """显示确认消息框"""
        if buttons is None:
            buttons = QMessageBox.Yes | QMessageBox.No
        return QMessageBox.question(parent, title, message, buttons)
    
    @staticmethod
    def create_custom(parent, title, text, info_text=None):
        """创建自定义消息框"""
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        if info_text:
            msg_box.setInformativeText(info_text)
        return msg_box
