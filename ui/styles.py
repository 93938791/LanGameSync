""" 
微信PC版风格样式表
"""

MODERN_STYLE = """
/* 全局样式 */
QMainWindow {
    background: transparent;
}

/* 主容器 - 微信灰色背景 */
#mainContainer {
    background: #f0f0f0;
    border-radius: 8px;
}

/* 标题栏 */
#titleBar {
    background: #2e2e2e;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

/* 内容区域 */
#contentWidget {
    background: #f0f0f0;
    border-bottom-right-radius: 8px;
}

/* 侧边栏 */
#sidebar {
    background: #2e2e2e;
    border-bottom-left-radius: 8px;
}

/* 网络设置区域 */
#networkGroup {
    background: #ffffff;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    padding-top: 10px;
}

#networkGroup::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 8px 15px;
    font-size: 16px;
    font-weight: bold;
    color: #333333;
}

/* 设备列表区域 */
#clientsGroup {
    background: #ffffff;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    padding-top: 10px;
}

#clientsGroup::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 8px 15px;
    font-size: 16px;
    font-weight: bold;
    color: #333333;
}

/* QGroupBox 通用样式 */
QGroupBox {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 15px;
    background: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 5px 15px;
    font-size: 16px;
    font-weight: bold;
    color: #333333;
    background: transparent;
}

/* 输入框样式 - 微信风格 */
QLineEdit {
    background: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 10px 12px;
    font-size: 14px;
    color: #333333;
    selection-background-color: #07c160;
    min-height: 20px;
}

QLineEdit:focus {
    border: 1px solid #07c160;
}

QLineEdit:hover {
    border: 1px solid #b0b0b0;
}

/* 按钮样式 - 微信绿 */
QPushButton {
    background: #f0f0f0;
    color: #333333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 14px;
}

QPushButton:hover {
    background: #e0e0e0;
    border: 1px solid #b0b0b0;
}

QPushButton:pressed {
    background: #d0d0d0;
}

QPushButton:disabled {
    background: #f5f5f5;
    color: #999999;
    border: 1px solid #e0e0e0;
}

/* 连接按钮 - 微信绿色 */
QPushButton#connectBtn {
    background: #07c160;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    padding: 12px 24px;
}

QPushButton#connectBtn:hover {
    background: #06ae56;
}

QPushButton#connectBtn:pressed {
    background: #059048;
}

QPushButton#connectBtn:disabled {
    background: #a0a0a0;
    color: #ffffff;
}

/* 列表样式 */
QListWidget {
    background: rgba(255, 255, 255, 0.7);
    border: 2px solid #90caf9;
    border-radius: 10px;
    padding: 10px;
    font-size: 12px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 5px;
    margin: 2px;
}

QListWidget::item:hover {
    background: rgba(33, 150, 243, 0.1);
}

QListWidget::item:selected {
    background: rgba(33, 150, 243, 0.3);
    color: #1565c0;
}

/* 进度条样式 */
QProgressBar {
    background: rgba(255, 255, 255, 0.7);
    border: 2px solid #90caf9;
    border-radius: 10px;
    height: 25px;
    text-align: center;
    color: #1565c0;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #42a5f5, stop:1 #1e88e5);
    border-radius: 8px;
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
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 12px 20px;
    font-size: 13px;
    color: #666666;
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
    border-radius: 4px;
    gridline-color: #f0f0f0;
    font-size: 13px;
    color: #333333;
}

QTableWidget::item {
    padding: 12px 8px;
    border-bottom: 1px solid #f0f0f0;
}

QTableWidget::item:selected {
    background: #f0f0f0;
    color: #333333;
}

QTableWidget::item:hover {
    background: #f5f5f5;
}

QHeaderView::section {
    background: #fafafa;
    color: #666666;
    padding: 12px 8px;
    border: none;
    border-bottom: 1px solid #e0e0e0;
    font-weight: bold;
    font-size: 13px;
}

QTableWidget QTableCornerButton::section {
    background: #fafafa;
    border: none;
}
"""
