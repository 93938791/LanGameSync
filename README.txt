局域网游戏文件实时同步工具 - LanGameSync
====================================

项目结构：
├── main.py                     # 主入口
├── config.py                   # 配置管理
├── managers/
│   ├── syncthing_manager.py    # Syncthing管理
│   ├── easytier_manager.py     # Easytier管理
│   └── sync_controller.py      # 同步流程控制
├── ui/
│   └── main_window.py          # GUI界面
├── utils/
│   ├── logger.py               # 日志工具
│   └── process_helper.py       # 进程管理工具
├── resources/
│   ├── syncthing.exe           # Syncthing二进制（需下载）
│   └── easytier-core.exe       # Easytier二进制（需下载）
└── requirements.txt            # Python依赖

使用说明：
1. 安装依赖: pip install -r requirements.txt
2. 下载Syncthing和Easytier二进制文件放入resources目录
3. 运行: python main.py
4. 打包: pyinstaller --onefile --windowed main.py
