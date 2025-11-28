"""
日志工具模块
支持日志轮转和自动清理，避免占用过多磁盘空间
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime, timedelta
from config import Config

class Logger:
    """日志管理器"""
    
    _instance = None
    
    # 日志配置
    MAX_LOG_SIZE = 5 * 1024 * 1024  # 单个日志文件最大5MB
    BACKUP_COUNT = 3  # 保留3个备份文件
    MAX_LOG_DAYS = 7  # 保留最近7天的日志文件
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        Config.init_dirs()
        
        # 清理旧日志文件
        self._cleanup_old_logs()
        
        # 创建日志文件
        log_file = Config.LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 配置日志格式（简化格式，减少日志大小）
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'  # 只显示时间，不显示日期（日期在文件名中）
        )
        
        # 使用RotatingFileHandler实现日志轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.MAX_LOG_SIZE,
            backupCount=self.BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)  # 文件日志只记录INFO及以上级别，减少日志量
        file_handler.setFormatter(formatter)
        
        # 控制台处理器（仅在调试模式下使用）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 根日志器
        self.logger = logging.getLogger(Config.APP_NAME)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _cleanup_old_logs(self):
        """清理旧的日志文件"""
        try:
            if not Config.LOG_DIR.exists():
                return
            
            # 计算过期时间
            expire_date = datetime.now() - timedelta(days=self.MAX_LOG_DAYS)
            
            deleted_count = 0
            total_size = 0
            
            # 遍历日志目录
            for log_file in Config.LOG_DIR.glob("app_*.log*"):
                try:
                    # 获取文件修改时间
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    file_size = log_file.stat().st_size
                    
                    # 如果文件过期，删除它
                    if file_mtime < expire_date:
                        log_file.unlink()
                        deleted_count += 1
                        total_size += file_size
                except Exception as e:
                    # 忽略无法删除的文件（可能正在被使用）
                    continue
            
            if deleted_count > 0:
                # 使用print而不是logger，因为logger可能还未初始化
                print(f"已清理 {deleted_count} 个旧日志文件，释放 {total_size / 1024 / 1024:.2f} MB 空间")
        except Exception as e:
            # 清理失败不影响程序运行
            pass
    
    def get_logger(self, name=None):
        """获取日志器"""
        if name:
            return logging.getLogger(f"{Config.APP_NAME}.{name}")
        return self.logger

# 全局日志实例
logger = Logger().get_logger()
