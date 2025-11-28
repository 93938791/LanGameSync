"""
同步诊断工具
用于检测和诊断同步失败的常见问题
"""
import socket
import requests
from pathlib import Path
from config import Config
from utils.logger import Logger

logger = Logger().get_logger("SyncDiagnostic")


class SyncDiagnostic:
    """同步诊断工具"""
    
    @staticmethod
    def check_port_accessibility(port, host='0.0.0.0'):
        """检查端口是否可访问"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host if host != '0.0.0.0' else 'localhost', port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"检查端口失败: {e}")
            return False
    
    @staticmethod
    def check_syncthing_api():
        """检查 Syncthing API 是否可访问"""
        try:
            url = f"http://localhost:{Config.SYNCTHING_API_PORT}/rest/system/status"
            headers = {"X-API-Key": Config.SYNCTHING_API_KEY}
            resp = requests.get(url, headers=headers, timeout=3)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Syncthing API 不可访问: {e}")
            return False
    
    @staticmethod
    def check_folder_writable(folder_path):
        """检查文件夹是否可写"""
        try:
            folder = Path(folder_path)
            if not folder.exists():
                return False, "文件夹不存在"
            
            # 尝试创建测试文件
            test_file = folder / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                return True, "文件夹可写"
            except Exception as e:
                return False, f"无写入权限: {str(e)}"
        except Exception as e:
            return False, f"检查失败: {str(e)}"
    
    @staticmethod
    def check_disk_space(folder_path, min_mb=100):
        """检查磁盘剩余空间"""
        try:
            import shutil
            folder = Path(folder_path)
            if not folder.exists():
                return False, "文件夹不存在"
            
            stat = shutil.disk_usage(folder)
            free_mb = stat.free / (1024 * 1024)
            
            if free_mb < min_mb:
                return False, f"磁盘空间不足: {free_mb:.1f}MB (需要至少 {min_mb}MB)"
            return True, f"磁盘空间充足: {free_mb:.1f}MB"
        except Exception as e:
            return False, f"检查失败: {str(e)}"
    
    @staticmethod
    def diagnose_all(syncthing_manager=None, easytier_manager=None, folder_path=None):
        """执行完整诊断"""
        results = {}
        
        # 1. 检查 Syncthing API
        logger.info("检查 Syncthing API...")
        results['syncthing_api'] = SyncDiagnostic.check_syncthing_api()
        
        # 2. 检查 Syncthing 同步端口
        logger.info("检查 Syncthing 同步端口 22000...")
        results['syncthing_port'] = SyncDiagnostic.check_port_accessibility(22000)
        
        # 3. 检查虚拟 IP
        if easytier_manager:
            logger.info("检查虚拟 IP...")
            results['virtual_ip'] = easytier_manager.virtual_ip not in [None, "unknown", "waiting..."]
            results['virtual_ip_value'] = easytier_manager.virtual_ip
        
        # 4. 检查设备连接
        if syncthing_manager:
            logger.info("检查设备连接...")
            connections = syncthing_manager.get_connections()
            if connections and connections.get('connections'):
                connected_count = sum(1 for conn in connections['connections'].values() if conn.get('connected'))
                results['connected_devices'] = connected_count
            else:
                results['connected_devices'] = 0
        
        # 5. 检查文件夹可写性和磁盘空间
        if folder_path:
            logger.info(f"检查文件夹: {folder_path}")
            writable, msg = SyncDiagnostic.check_folder_writable(folder_path)
            results['folder_writable'] = writable
            results['folder_writable_msg'] = msg
            
            space_ok, space_msg = SyncDiagnostic.check_disk_space(folder_path)
            results['disk_space'] = space_ok
            results['disk_space_msg'] = space_msg
        
        # 生成诊断报告
        logger.info("=" * 50)
        logger.info("同步诊断报告")
        logger.info("=" * 50)
        
        for key, value in results.items():
            status = "✅" if value else "❌"
            logger.info(f"{status} {key}: {value}")
        
        logger.info("=" * 50)
        
        return results
    
