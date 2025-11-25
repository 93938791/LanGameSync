""" 
微信PC版风格样式表
"""

MODERN_STYLE = """
/* 全局样式 */
QMainWindow {
    background: transparent;
}

/* 主容器 - 微信白色背景 */
#mainContainer {
    background: #f7f7f7;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
}

/* 标题栏 - 微信浅灰 */
#titleBar {
    background: #ededed;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border-bottom: 1px solid #d6d6d6;
}

/* 内容区域 - 微信白色背景 */
#contentWidget {
    background: #ffffff;
    border-bottom-right-radius: 8px;
}

/* 侧边栏 - 微信浅灰 */
#sidebar {
    background: #ededed;
    border-bottom-left-radius: 8px;
}

/* 网络页面背景 */
#networkPage {
    background: #ffffff;
}

/* 网络设置区域 - 微信卡片风格 */
#networkGroup {
    background: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 20px;
    margin: 5px;
}

/* 设备列表区域 - 微信卡片风格 */
#clientsGroup {
    background: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 20px;
    margin: 5px;
}

/* QGroupBox 通用样式 - 微信卡片风格 */
QGroupBox {
    border: none;
    border-radius: 6px;
    margin-top: 0px;
    padding: 20px;
    background: #ffffff;
}

/* 输入框样式 - 微信风格 */
QLineEdit {
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 10px 15px;
    font-size: 13px;
    color: #2c2c2c;
    selection-background-color: #c0e7d4;
    min-height: 20px;
}

QLineEdit:focus {
    border: 1px solid #07c160;
    background: #ffffff;
}

QLineEdit:hover {
    background: #f5f5f5;
    border: 1px solid #c0c0c0;
}

/* 按钮样式 - 微信风格 */
QPushButton {
    background: #ffffff;
    color: #181818;
    border: 1px solid #d6d6d6;
    border-radius: 3px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: normal;
}

QPushButton:hover {
    background: #f7f7f7;
    border: 1px solid #c6c6c6;
    color: #000000;
}

QPushButton:pressed {
    background: #ececec;
    border: 1px solid #b8b8b8;
}

QPushButton:disabled {
    background: #f7f7f7;
    color: #b8b8b8;
    border: 1px solid #e7e7e7;
}

/* 连接按钮 - 微信绿 */
QPushButton#connectBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #09d168, stop:1 #07c160);
    color: #ffffff;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    padding: 12px 24px;
}

QPushButton#connectBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #0ae174, stop:1 #09d168);
}

QPushButton#connectBtn:pressed {
    background: #06ae56;
}

QPushButton#connectBtn:disabled {
    background: #b8e6cc;
    color: #ffffff;
}

/* 列表样式 - 微信风格 */
QListWidget {
    background: #ffffff;
    border: 1px solid #e7e7e7;
    border-radius: 4px;
    padding: 8px;
    font-size: 13px;
}

QListWidget::item {
    padding: 12px;
    border-radius: 3px;
    margin: 2px 0px;
    border: none;
}

QListWidget::item:hover {
    background: #f7f7f7;
}

QListWidget::item:selected {
    background: #e7f4ed;
    color: #000000;
}

/* 进度条样式 - 微信风格 */
QProgressBar {
    background: #f7f7f7;
    border: 1px solid #e7e7e7;
    border-radius: 3px;
    height: 20px;
    text-align: center;
    color: #000000;
    font-weight: normal;
    font-size: 12px;
}

QProgressBar::chunk {
    background: #07c160;
    border-radius: 2px;
}

/* 文本编辑框样式 */
QTextEdit {
    background: rgba(245, 245, 245, 0.9);
    border: 2px solid #90caf9;
    border-radius: 10px;
    padding: 10px;
    font-family: 'Consolas', monospace;
    font-size: 11px;
    color: #424242;
}

/* 标签样式 */
QLabel {
    color: #333333;
    font-size: 14px;
}

#statusLabel {
    background: #f7f7f7;
    border: 1px solid #e7e7e7;
    border-radius: 3px;
    padding: 10px 20px;
    font-size: 13px;
    color: #000000;
    font-weight: normal;
}

/* 菜单栏样式 */
QMenuBar {
    background: rgba(255, 255, 255, 0.8);
    border-bottom: 2px solid #90caf9;
    padding: 5px;
}

QMenuBar::item {
    background: transparent;
    padding: 8px 15px;
    border-radius: 5px;
    color: #1565c0;
    font-size: 13px;
}

QMenuBar::item:selected {
    background: rgba(33, 150, 243, 0.2);
}

QMenuBar::item:pressed {
    background: rgba(33, 150, 243, 0.3);
}

QMenu {
    background: rgba(255, 255, 255, 0.95);
    border: 2px solid #90caf9;
    border-radius: 8px;
    padding: 5px;
}

QMenu::item {
    padding: 8px 30px;
    border-radius: 5px;
    color: #424242;
}

QMenu::item:selected {
    background: rgba(33, 150, 243, 0.2);
    color: #1565c0;
}

/* 滚动条样式 - 微信风格 */
QScrollBar:vertical {
    background: #f0f0f0;
    width: 8px;
    border-radius: 4px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* 表格样式 - 微信风格 */
QTableWidget {
    background: #ffffff;
    border: none;
    border-radius: 0px;
    gridline-color: #e7e7e7;
    font-size: 13px;
    color: #000000;
}

QTableWidget::item {
    padding: 12px 10px;
    border-bottom: 1px solid #e7e7e7;
}

QTableWidget::item:selected {
    background: #e7f4ed;
    color: #000000;
}

QTableWidget::item:hover {
    background: #f7f7f7;
}

QHeaderView::section {
    background: #fafafa;
    color: #000000;
    padding: 10px 10px;
    border: none;
    border-bottom: 1px solid #d6d6d6;
    font-weight: 600;
    font-size: 13px;
}

QTableWidget QTableCornerButton::section {
    background: #fafafa;
    border: none;
}
"""
