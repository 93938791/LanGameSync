""" 
微信PC版风格样式表
"""

MODERN_STYLE = """
/* 全局样式 */
QMainWindow {
    background: transparent;
}

/* 主容器 - 现代灰色背景 */
#mainContainer {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f8f9fa, stop:1 #e8eaed);
    border-radius: 10px;
}

/* 标题栏 */
#titleBar {
    background: #2e2e2e;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

/* 内容区域 */
#contentWidget {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f8f9fa, stop:1 #e8eaed);
    border-bottom-right-radius: 10px;
}

/* 侧边栏 */
#sidebar {
    background: #2e2e2e;
    border-bottom-left-radius: 8px;
}

/* 网络设置区域 */
#networkGroup {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #f8f9fa);
    border: none;
    border-radius: 12px;
    padding: 25px;
    margin: 5px;
}

#networkGroup::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0px 8px 8px 8px;
    font-size: 17px;
    font-weight: bold;
    color: #1a73e8;
    background: transparent;
}

/* 设备列表区域 */
#clientsGroup {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #f8f9fa);
    border: none;
    border-radius: 12px;
    padding: 25px;
    margin: 5px;
}

#clientsGroup::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0px 8px 8px 8px;
    font-size: 17px;
    font-weight: bold;
    color: #1a73e8;
    background: transparent;
}

/* QGroupBox 通用样式 */
QGroupBox {
    border: none;
    border-radius: 12px;
    margin-top: 15px;
    padding-top: 20px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #f8f9fa);
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0px 8px 8px 8px;
    font-size: 17px;
    font-weight: bold;
    color: #1a73e8;
    background: transparent;
}

/* 输入框样式 - 现代风格 */
QLineEdit {
    background: #ffffff;
    border: 2px solid #e8eaed;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 14px;
    color: #202124;
    selection-background-color: #1a73e8;
    min-height: 22px;
}

QLineEdit:focus {
    border: 2px solid #1a73e8;
    background: #ffffff;
}

QLineEdit:hover {
    border: 2px solid #5f6368;
    background: #f8f9fa;
}

/* 按钮样式 - 现代风格 */
QPushButton {
    background: #ffffff;
    color: #1a73e8;
    border: 2px solid #dadce0;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 500;
}

QPushButton:hover {
    background: #f8f9fa;
    border: 2px solid #1a73e8;
    color: #1967d2;
}

QPushButton:pressed {
    background: #e8f0fe;
    border: 2px solid #1967d2;
}

QPushButton:disabled {
    background: #f8f9fa;
    color: #9aa0a6;
    border: 2px solid #e8eaed;
}

/* 连接按钮 - Google 蓝 */
QPushButton#connectBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4285f4, stop:1 #1a73e8);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: bold;
    padding: 14px 28px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

QPushButton#connectBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #5a95f5, stop:1 #2b7de9);
}

QPushButton#connectBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #1967d2, stop:1 #1557b0);
}

QPushButton#connectBtn:disabled {
    background: #e8eaed;
    color: #9aa0a6;
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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #e8f0fe, stop:1 #f8f9fa);
    border: none;
    border-radius: 8px;
    padding: 14px 24px;
    font-size: 14px;
    color: #1a73e8;
    font-weight: 500;
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

/* 表格样式 - 现代风格 */
QTableWidget {
    background: #ffffff;
    border: none;
    border-radius: 8px;
    gridline-color: #f1f3f4;
    font-size: 14px;
    color: #202124;
}

QTableWidget::item {
    padding: 14px 12px;
    border-bottom: 1px solid #f1f3f4;
}

QTableWidget::item:selected {
    background: #e8f0fe;
    color: #1a73e8;
}

QTableWidget::item:hover {
    background: #f8f9fa;
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f8f9fa, stop:1 #f1f3f4);
    color: #5f6368;
    padding: 12px 10px;
    border: none;
    border-bottom: 2px solid #e8eaed;
    font-weight: bold;
    font-size: 13px;
}
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
