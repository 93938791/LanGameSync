"""
进程管理工具
"""
import subprocess
import psutil
import time
import sys
from utils.logger import Logger

logger = Logger().get_logger("ProcessHelper")

# Windows平台的CREATE_NO_WINDOW常量
if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

class ProcessHelper:
    """进程管理辅助类"""
    
    @staticmethod
    def start_process(exe_path, args=None, env=None, hide_window=True, require_admin=False):
        """
        启动进程
        
        Args:
            exe_path: 可执行文件路径
            args: 命令行参数列表
            env: 环境变量字典
            hide_window: 是否隐藏窗口
            require_admin: 是否需要管理员权限（仅Windows）
        
        Returns:
            subprocess.Popen对象
        """
        cmd = [str(exe_path)]
        if args:
            cmd.extend(args)
        
        # Windows平台特殊处理
        if sys.platform == 'win32':
            # 如果需要管理员权限，使用ShellExecute启动
            if require_admin:
                import ctypes
                logger.info(f"以管理员权限启动进程: {' '.join(cmd)}")
                
                # 准备参数
                params = ' '.join([f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in args]) if args else ''
                
                # 使用ShellExecute以管理员身份启动，不显示窗口
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",  # 以管理员身份运行
                    str(exe_path),
                    params,
                    None,
                    0  # SW_HIDE - 隐藏窗口
                )
                
                if ret <= 32:
                    raise RuntimeError(f"启动进程失败，错误代码: {ret}")
                
                # ShellExecute无法返回Popen对象，需要找到启动的进程
                import time
                time.sleep(1)  # 等待进程启动
                
                # 尝试通过进程名找到刚启动的进程
                import psutil
                exe_name = str(exe_path).split('\\')[-1]
                for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                    try:
                        if proc.info['name'] == exe_name:
                            # 找到最近创建的进程
                            if time.time() - proc.info['create_time'] < 5:
                                # 创建伪Popen对象用于管理
                                class PseudoPopen:
                                    def __init__(self, pid):
                                        self.pid = pid
                                        self._proc = psutil.Process(pid)
                                    
                                    def poll(self):
                                        try:
                                            return None if self._proc.is_running() else 0
                                        except:
                                            return 0
                                    
                                    def terminate(self):
                                        try:
                                            self._proc.terminate()
                                        except:
                                            pass
                                    
                                    def kill(self):
                                        try:
                                            self._proc.kill()
                                        except:
                                            pass
                                    
                                    def wait(self, timeout=None):
                                        try:
                                            self._proc.wait(timeout=timeout)
                                        except:
                                            pass
                                
                                logger.info(f"找到启动的进程 PID: {proc.info['pid']}")
                                return PseudoPopen(proc.info['pid'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                logger.warning("无法找到启动的进程，返回空对象")
                return None
            
            # 常规启动（非管理员）
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
                creationflags=CREATE_NO_WINDOW if hide_window else 0
            )
            
            return process
        
        # 非Windows平台
        logger.info(f"启动进程: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
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
        killed_count = 0
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    try:
                        proc = psutil.Process(conn.pid)
                        proc_name = proc.name()
                        logger.info(f"杀死占用端口 {port} 的进程: {proc_name} (PID: {conn.pid})")
                        proc.kill()
                        proc.wait(timeout=3)  # 等待进程终止
                        killed_count += 1
                    except psutil.NoSuchProcess:
                        logger.warning(f"进程 PID {conn.pid} 已不存在")
                    except psutil.TimeoutExpired:
                        logger.warning(f"进程 PID {conn.pid} 未响应终止")
                    except Exception as e:
                        logger.error(f"杀死进程 PID {conn.pid} 失败: {e}")
        except Exception as e:
            logger.error(f"扫描端口失败: {e}")
        
        if killed_count > 0:
            logger.info(f"共杀死 {killed_count} 个占用端口 {port} 的进程")
            time.sleep(1)  # 等待端口释放
        
        return killed_count
    
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
