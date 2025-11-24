"""
主程序入口
"""
import sys
from config import Config
from ui.main_window import main as run_app
from utils.logger import logger

def main():
    """主函数"""
    try:
        # 初始化配置目录
        Config.init_dirs()
        
        logger.info(f"=== {Config.APP_NAME} v{Config.APP_VERSION} 启动 ===")
        
        # 运行GUI应用
        run_app()
        
    except Exception as e:
        logger.error(f"应用异常: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
