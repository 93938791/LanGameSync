"""
进程管理工具
"""
import subprocess
import psutil
import time
import sys
from pathlib import Path
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
                
                # 准备参数 - 正确处理参数，确保每个参数都被正确引用
                if args:
                    # 对每个参数进行适当的转义和引用
                    params_list = []
                    for arg in args:
                        arg_str = str(arg)
                        # 如果参数包含空格或特殊字符，需要加引号
                        if ' ' in arg_str or '|' in arg_str or '<' in arg_str or '>' in arg_str:
                            params_list.append(f'"{arg_str}"')
                        else:
                            params_list.append(arg_str)
                    params = ' '.join(params_list)
                else:
                    params = ''
                
                # 设置工作目录为exe文件所在目录（确保能找到依赖文件如wintun.dll）
                exe_dir = str(Path(exe_path).parent.resolve())
                
                # 使用ShellExecute以管理员身份启动，不显示窗口
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",  # 以管理员身份运行
                    str(exe_path),
                    params,
                    exe_dir,  # 工作目录：exe文件所在目录
                    0  # SW_HIDE - 隐藏窗口
                )
                
                if ret <= 32:
                    error_codes = {
                        0: "内存不足",
                        2: "文件未找到",
                        3: "路径未找到",
                        5: "拒绝访问",
                        8: "内存不足",
                        11: "无效的可执行文件",
                        26: "共享冲突",
                        27: "关联不完整",
                        28: "DDE事务超时",
                        29: "DDE事务失败",
                        30: "DDE忙碌",
                        31: "没有文件关联",
                        32: "动态数据交换（DDE）失败"
                    }
                    error_msg = error_codes.get(ret, f"未知错误")
                    raise RuntimeError(f"启动进程失败，错误代码: {ret} ({error_msg})")
                
                # ShellExecute无法返回Popen对象，需要找到启动的进程
                # 增加等待时间并多次尝试查找进程
                exe_name = str(exe_path).split('\\')[-1]
                exe_path_normalized = str(Path(exe_path).resolve()).lower()
                
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
                
                # 尝试多次查找进程，最多等待10秒
                max_wait_time = 10
                check_interval = 0.5
                max_attempts = int(max_wait_time / check_interval)
                
                for attempt in range(max_attempts):
                    time.sleep(check_interval)
                    start_time = time.time() - 15  # 查找最近15秒内创建的进程
                    
                    for proc in psutil.process_iter(['pid', 'name', 'create_time', 'exe', 'cmdline']):
                        try:
                            proc_info = proc.info
                            
                            # 首先通过进程名匹配
                            if proc_info.get('name') and proc_info['name'].lower() == exe_name.lower():
                                # 验证进程路径
                                proc_exe = proc_info.get('exe', '')
                                if proc_exe:
                                    proc_exe_normalized = str(Path(proc_exe).resolve()).lower()
                                    if proc_exe_normalized == exe_path_normalized:
                                        # 验证进程创建时间
                                        if proc_info.get('create_time', 0) >= start_time:
                                            # 验证进程是否仍在运行
                                            proc_obj = psutil.Process(proc_info['pid'])
                                            if proc_obj.is_running() and proc_obj.status() != psutil.STATUS_ZOMBIE:
                                                logger.info(f"找到启动的进程 PID: {proc_info['pid']} (尝试 {attempt + 1}/{max_attempts})")
                                                return PseudoPopen(proc_info['pid'])
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                        except Exception as e:
                            logger.debug(f"检查进程时出错: {e}")
                            continue
                
                logger.warning(f"无法找到启动的进程（已等待 {max_wait_time} 秒），进程可能启动失败")
                # 尝试通过进程名查找任何运行中的进程（用于调试）
                try:
                    found_procs = []
                    for proc in psutil.process_iter(['pid', 'name', 'exe']):
                        try:
                            if proc.info.get('name') and proc.info['name'].lower() == exe_name.lower():
                                found_procs.append(f"PID={proc.info['pid']}, exe={proc.info.get('exe', 'N/A')}")
                        except:
                            pass
                    if found_procs:
                        logger.warning(f"发现同名进程但路径不匹配: {found_procs}")
                except:
                    pass
                
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
        """等待端口可用（检查端口是否在监听）"""
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            try:
                # 检查端口是否在监听
                for conn in psutil.net_connections(kind='inet'):
                    try:
                        if conn.laddr and conn.laddr.port == port:
                            # 检查是否是监听状态
                            status_str = str(conn.status).upper() if conn.status else ''
                            if status_str == 'LISTEN':
                                logger.info(f"端口 {port} 已就绪 (检查 {check_count} 次)")
                                return True
                            # 也接受 ESTABLISHED 状态（可能已经建立了连接）
                            elif status_str == 'ESTABLISHED':
                                logger.info(f"端口 {port} 已就绪（已建立连接）")
                                return True
                    except (AttributeError, psutil.AccessDenied):
                        continue
            except (psutil.AccessDenied, PermissionError) as e:
                # 如果没有权限查看网络连接，尝试使用 socket 连接测试
                logger.debug(f"无法访问网络连接信息（需要管理员权限），尝试连接测试: {e}")
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    result = sock.connect_ex(('127.0.0.1', port))
                    sock.close()
                    if result == 0:
                        logger.info(f"端口 {port} 已就绪（通过连接测试，检查 {check_count} 次）")
                        return True
                except Exception as e2:
                    logger.debug(f"连接测试失败: {e2}")
            except Exception as e:
                logger.debug(f"检查端口时出错: {e}")
            
            # 每5次检查输出一次进度
            if check_count % 10 == 0:
                elapsed = time.time() - start_time
                logger.debug(f"等待端口 {port} 就绪... ({elapsed:.1f}s / {timeout}s)")
            
            time.sleep(0.5)
        
        elapsed_time = time.time() - start_time
        logger.warning(f"等待端口 {port} 超时（已等待 {elapsed_time:.1f} 秒，检查了 {check_count} 次）")
        return False
