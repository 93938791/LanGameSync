"""
进程管理工具
"""
import subprocess
import psutil
import time
from utils.logger import Logger

logger = Logger().get_logger("ProcessHelper")

class ProcessHelper:
    """进程管理辅助类"""
    
    @staticmethod
    def start_process(exe_path, args=None, env=None, hide_window=True):
        """
        启动进程
        
        Args:
            exe_path: 可执行文件路径
            args: 命令行参数列表
            env: 环境变量字典
            hide_window: 是否隐藏窗口
        
        Returns:
            subprocess.Popen对象
        """
        cmd = [str(exe_path)]
        if args:
            cmd.extend(args)
        
        startup_info = None
        if hide_window:
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = subprocess.SW_HIDE
        
        logger.info(f"启动进程: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startup_info,
            creationflags=subprocess.CREATE_NO_WINDOW if hide_window else 0
        )
        
        return process
    
    @staticmethod
    def is_process_running(process):
        """检查进程是否运行"""
        if process is None:
            return False
        return process.poll() is None
    
    @staticmethod
    def kill_process(process, timeout=5):
        """终止进程"""
        if not ProcessHelper.is_process_running(process):
            return True
        
        try:
            logger.info(f"终止进程 PID: {process.pid}")
            process.terminate()
            process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            logger.warning(f"进程 {process.pid} 未响应终止，强制杀死")
            process.kill()
            return True
        except Exception as e:
            logger.error(f"终止进程失败: {e}")
            return False
    
    @staticmethod
    def kill_by_port(port):
        """根据端口号杀死占用的进程"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    logger.info(f"杀死占用端口 {port} 的进程: {proc.name()} (PID: {conn.pid})")
                    proc.kill()
                except Exception as e:
                    logger.error(f"杀死进程失败: {e}")
    
    @staticmethod
    def wait_for_port(port, timeout=30):
        """等待端口可用"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    logger.info(f"端口 {port} 已就绪")
                    return True
            time.sleep(0.5)
        
        logger.warning(f"等待端口 {port} 超时")
        return False
