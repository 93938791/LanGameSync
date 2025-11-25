# -*- coding: utf-8 -*-
"""
启动器账号信息读取器
从HMCL和PCL2启动器中读取已登录的账号信息
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from utils.logger import Logger

logger = Logger().get_logger("LauncherAccountReader")


class LauncherAccountReader:
    """启动器账号信息读取器"""
    
    def __init__(self, launcher_path: str):
        """
        初始化读取器
        
        Args:
            launcher_path: 启动器路径（.exe或.jar文件）
        """
        self.launcher_path = Path(launcher_path)
        self.launcher_dir = self.launcher_path.parent
        self.launcher_type = self._detect_launcher_type()
        
    def _detect_launcher_type(self) -> str:
        """检测启动器类型"""
        # 方法1: 通过文件名判断
        launcher_name = self.launcher_path.name.lower()
        if 'hmcl' in launcher_name:
            logger.info(f"通过文件名检测为HMCL: {launcher_name}")
            return 'HMCL'
        elif 'pcl' in launcher_name:
            logger.info(f"通过文件名检测为PCL2: {launcher_name}")
            return 'PCL2'
        
        # 方法2: 通过配置文件判断（只检查启动器所在目录，不检查全局配置）
        logger.info(f"文件名无法判断类型，尝试通过配置文件检测: {launcher_name}")
        
        # 检查HMCL配置文件（只检查启动器同目录的.hmcl文件夹）
        hmcl_config_dir = self.launcher_dir / '.hmcl'
        if hmcl_config_dir.exists() and (hmcl_config_dir / 'accounts.json').exists():
            logger.info(f"通过配置文件检测为HMCL: {hmcl_config_dir}")
            return 'HMCL'
        
        # 检查PCL2配置文件
        pcl_minecraft_dirs = [
            self.launcher_dir / '.minecraft',  # 启动器同目录
            self.launcher_dir.parent / '.minecraft'  # 启动器父目录（PCL2常见结构）
        ]
        for minecraft_dir in pcl_minecraft_dirs:
            launcher_profiles = minecraft_dir / 'launcher_profiles.json'
            if launcher_profiles.exists():
                # 读取文件检查是否有authenticationDatabase（PCL2特征）
                try:
                    with open(launcher_profiles, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'authenticationDatabase' in data:
                            logger.info(f"通过配置文件检测为PCL2: {launcher_profiles}")
                            return 'PCL2'
                except:
                    pass
        
        logger.warning(f"无法识别启动器类型: {self.launcher_path}")
        logger.warning(f"启动器目录: {self.launcher_dir}")
        logger.warning("请确保拖入的是HMCL或PCL2启动器文件")
        return 'Unknown'
    
    def get_account_info(self) -> Optional[Dict]:
        """
        获取启动器中的账号信息
        
        Returns:
            账号信息字典，包含：
            {
                'player_name': 玩家名称,
                'uuid': 玩家UUID（无横线格式）,
                'access_token': 访问令牌,
                'account_type': 账号类型（'offline', 'microsoft', 'authlib'）,
                'is_valid': 是否有效
            }
        """
        if self.launcher_type == 'HMCL':
            return self._read_hmcl_account()
        elif self.launcher_type == 'PCL2':
            return self._read_pcl_account()
        else:
            logger.warning(f"未知的启动器类型: {self.launcher_path}")
            return None
    
    def get_launcher_type(self) -> str:
        """获取启动器类型"""
        return self.launcher_type
    
    def get_all_accounts(self) -> List[Dict]:
        """
        获取启动器中的所有账号
        
        Returns:
            账号列表
        """
        if self.launcher_type == 'HMCL':
            return self._get_all_hmcl_accounts()
        elif self.launcher_type == 'PCL2':
            return self._get_all_pcl_accounts()
        else:
            logger.warning(f"不支持的启动器类型: {self.launcher_type}")
            return []
    
    def _read_hmcl_account(self) -> Optional[Dict]:
        """读取HMCL账号信息"""
        try:
            # HMCL配置路径优先级:
            # 1. 启动器同目录的.hmcl文件夹（便携模式）
            # 2. %APPDATA%\.hmcl（默认模式）
            
            config_dirs = [
                self.launcher_dir / '.hmcl',
                Path(os.getenv('APPDATA', '')) / '.hmcl'
            ]
            
            for config_dir in config_dirs:
                if not config_dir.exists():
                    continue
                
                logger.info(f"检查HMCL配置目录: {config_dir}")
                
                # 读取accounts.json
                accounts_file = config_dir / 'accounts.json'
                if not accounts_file.exists():
                    logger.warning(f"未找到accounts.json: {accounts_file}")
                    continue
                
                with open(accounts_file, 'r', encoding='utf-8') as f:
                    accounts_data = json.load(f)
                
                # HMCL的accounts.json可能是列表或字典格式
                if isinstance(accounts_data, list):
                    # 列表格式：直接是账号列表
                    accounts = accounts_data
                    selected_account = None
                elif isinstance(accounts_data, dict):
                    # 字典格式：包含selectedAccount和accounts字段
                    selected_account = accounts_data.get('selectedAccount')
                    accounts = accounts_data.get('accounts', [])
                else:
                    logger.warning(f"不支持的accounts.json格式: {type(accounts_data)}")
                    continue
                
                if not accounts:
                    logger.warning("HMCL中没有账号")
                    continue
                
                # 获取当前选中的账号
                current_account = None
                if selected_account:
                    for account in accounts:
                        if account.get('uuid') == selected_account:
                            current_account = account
                            break
                
                # 如果没有选中账号，使用最后一个账号（最近使用的）
                if not current_account and accounts:
                    current_account = accounts[-1]  # 最后一个（最近使用）
                    logger.info(f"使用最近使用的账号: {current_account.get('username') or current_account.get('displayName')} (类型: {current_account.get('type', 'offline')})")
                
                if current_account:
                    return self._parse_hmcl_account(current_account)
            
            logger.warning("未找到HMCL账号配置")
            return None
            
        except Exception as e:
            logger.error(f"读取HMCL账号失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _parse_hmcl_account(self, account_data: Dict) -> Dict:
        """解析HMCL账号数据"""
        try:
            account_type_map = {
                'offline': 'offline',
                'yggdrasil': 'authlib',
                'microsoft': 'microsoft',
                'mojang': 'mojang'
            }
            
            raw_type = account_data.get('type', 'offline')
            account_type = account_type_map.get(raw_type, 'offline')
            
            # Microsoft账号使用displayName，其他账号使用username
            if raw_type == 'microsoft':
                player_name = account_data.get('displayName') or account_data.get('username', 'Player')
            else:
                player_name = account_data.get('username') or account_data.get('displayName', 'Player')
            
            uuid = account_data.get('uuid', '00000000-0000-0000-0000-000000000000')
            
            # 去掉UUID中的横线
            uuid_clean = uuid.replace('-', '')
            
            # 获取访问令牌
            access_token = account_data.get('accessToken', 'null')
            
            # 检查账号是否有效
            # 离线账号也是有效的，只要有玩家名和UUID
            if account_type == 'offline':
                is_valid = bool(player_name and uuid_clean)
            else:
                # 正版账号需要有效的access_token
                is_valid = bool(access_token and access_token != 'null')
            
            logger.info(f"解析HMCL账号: {player_name} ({account_type})")
            
            return {
                'player_name': player_name,
                'uuid': uuid_clean,
                'access_token': access_token,
                'account_type': account_type,
                'is_valid': is_valid,
                'raw_data': account_data  # 保留原始数据
            }
            
        except Exception as e:
            logger.error(f"解析HMCL账号数据失败: {e}")
            return None
    
    def _read_pcl_account(self) -> Optional[Dict]:
        """读取PCL2账号信息"""
        try:
            # PCL2配置路径优先级:
            # 1. 启动器目录下的PCL文件夹
            # 2. 启动器目录下的.minecraft文件夹
            # 3. 启动器父目录下的.minecraft文件夹（PCL2常见结构）
            
            minecraft_dirs = [
                self.launcher_dir / '.minecraft',  # 启动器同目录
                self.launcher_dir.parent / '.minecraft',  # 启动器父目录（PCL2常见）
            ]
            
            # 方法1: 从配置文件读取
            config_dir = self.launcher_dir / 'PCL'
            if config_dir.exists():
                setup_file = config_dir / 'Setup.ini'
                if setup_file.exists():
                    account_info = self._parse_pcl_setup_file(setup_file)
                    if account_info:
                        return account_info
            
            # 方法2: 从.minecraft/launcher_profiles.json读取
            for minecraft_dir in minecraft_dirs:
                if not minecraft_dir.exists():
                    logger.debug(f"PCL2目录不存在: {minecraft_dir}")
                    continue
                
                launcher_profiles = minecraft_dir / 'launcher_profiles.json'
                if launcher_profiles.exists():
                    logger.info(f"找到PCL2配置文件: {launcher_profiles}")
                    account_info = self._parse_launcher_profiles(launcher_profiles)
                    if account_info:
                        return account_info
            
            logger.warning("未找到PCL2账号配置")
            return None
            
        except Exception as e:
            logger.error(f"读取PCL2账号失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _parse_pcl_setup_file(self, setup_file: Path) -> Optional[Dict]:
        """解析PCL的Setup.ini文件"""
        try:
            # Setup.ini是PCL的配置文件，但账号信息可能加密
            # 这里提供基础读取逻辑
            logger.info(f"尝试读取PCL配置: {setup_file}")
            
            # TODO: 实现PCL Setup.ini解析
            # PCL的配置比较复杂，可能需要解密
            
            return None
            
        except Exception as e:
            logger.error(f"解析PCL Setup.ini失败: {e}")
            return None
    
    def _parse_launcher_profiles(self, profiles_file: Path) -> Optional[Dict]:
        """
        解析launcher_profiles.json
        这是Minecraft官方启动器和大多数第三方启动器通用的账号存储格式
        """
        try:
            logger.info(f"读取launcher_profiles.json: {profiles_file}")
            
            with open(profiles_file, 'r', encoding='utf-8') as f:
                profiles_data = json.load(f)
            
            # 获取选中的账号
            selected_user = profiles_data.get('selectedUser', {})
            
            # PCL2格式：使用authenticationDatabase
            auth_database = profiles_data.get('authenticationDatabase', {})
            if auth_database and selected_user:
                account_id = selected_user.get('account')
                profile_id = selected_user.get('profile')
                
                if account_id and account_id in auth_database:
                    current_account = auth_database[account_id]
                    
                    # 获取玩家名称
                    player_name = current_account.get('username', 'Player')
                    
                    # 如果有profile_id，从 profiles 中获取displayName
                    if profile_id:
                        profiles = current_account.get('profiles', {})
                        if profile_id in profiles:
                            player_name = profiles[profile_id].get('displayName', player_name)
                    
                    access_token = current_account.get('accessToken', 'null')
                    
                    # 尝试从jwt token中解析UUID
                    uuid = None
                    if access_token and 'eyJ' in access_token:
                        try:
                            import base64
                            # JWT格式: header.payload.signature
                            parts = access_token.split('.')
                            if len(parts) >= 2:
                                # 解码payload（需要添加padding）
                                payload = parts[1]
                                # 添加缺失的padding
                                padding = 4 - len(payload) % 4
                                if padding:
                                    payload += '=' * padding
                                
                                decoded = base64.urlsafe_b64decode(payload)
                                token_data = json.loads(decoded)
                                
                                # 从Microsoft token中提取UUID
                                profiles = token_data.get('profiles', {})
                                mc_profile = profiles.get('mc')
                                if mc_profile:
                                    uuid = mc_profile
                                    logger.info(f"JWT token中提取到真实UUID: {uuid}")
                        except Exception as e:
                            logger.warning(f"解析JWT token失败: {e}")
                    
                    # 如果没有从jwt中获取，使用profile_id
                    if not uuid:
                        uuid = profile_id or account_id or '00000000000000000000000000000000'
                    
                    uuid_clean = uuid.replace('-', '')
                    
                    # 判断账号类型
                    account_type = 'offline'
                    if access_token and access_token != 'null' and 'eyJ' in access_token:
                        # JWT token格式，可能是Microsoft或Mojang
                        account_type = 'microsoft'  # PCL2通常用Microsoft
                    
                    # 检查账号是否有效
                    if account_type == 'offline':
                        is_valid = bool(player_name and uuid_clean)
                    else:
                        is_valid = bool(access_token and access_token != 'null')
                    
                    logger.info(f"从 PCL2 launcher_profiles.json 解析账号: {player_name} ({account_type})")
                    
                    return {
                        'player_name': player_name,
                        'uuid': uuid_clean,
                        'access_token': access_token,
                        'account_type': account_type,
                        'is_valid': is_valid,
                        'raw_data': current_account
                    }
            
            # 如果不是PCL2格式，尝试原版格式
            accounts = profiles_data.get('accounts', {})
            
            if not accounts:
                logger.warning("launcher_profiles.json中没有账号")
                return None
            
            # 获取当前账号
            current_account = None
            if selected_user:
                account_id = selected_user.get('account')
                if account_id and account_id in accounts:
                    current_account = accounts[account_id]
            
            # 如果没有选中账号，使用第一个
            if not current_account:
                account_id = list(accounts.keys())[0]
                current_account = accounts[account_id]
            
            # 解析账号信息
            player_name = current_account.get('username', 'Player')
            access_token = current_account.get('accessToken', 'null')
            
            # 尝试获取UUID（可能在不同字段中）
            uuid = (current_account.get('minecraftProfile', {}).get('id') or 
                   current_account.get('uuid') or 
                   '00000000000000000000000000000000')
            
            # 去掉UUID中的横线
            uuid_clean = uuid.replace('-', '')
            
            # 判断账号类型
            account_type = 'offline'
            if 'microsoft' in str(current_account.get('type', '')).lower():
                account_type = 'microsoft'
            elif access_token and access_token != 'null':
                account_type = 'mojang'
            
            # 检查账号是否有效
            if account_type == 'offline':
                is_valid = bool(player_name and uuid_clean)
            else:
                is_valid = bool(access_token and access_token != 'null')
            
            logger.info(f"解析账号: {player_name} ({account_type})")
            
            return {
                'player_name': player_name,
                'uuid': uuid_clean,
                'access_token': access_token,
                'account_type': account_type,
                'is_valid': is_valid,
                'raw_data': current_account
            }
            
        except Exception as e:
            logger.error(f"解析launcher_profiles.json失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _get_all_hmcl_accounts(self) -> List[Dict]:
        """
        获取HMCL所有账号列表
        
        Returns:
            账号列表
        """
        try:
            config_dirs = [
                self.launcher_dir / '.hmcl',
                Path(os.getenv('APPDATA', '')) / '.hmcl'
            ]
            
            for config_dir in config_dirs:
                if not config_dir.exists():
                    continue
                
                accounts_file = config_dir / 'accounts.json'
                if not accounts_file.exists():
                    continue
                
                with open(accounts_file, 'r', encoding='utf-8') as f:
                    accounts_data = json.load(f)
                
                # HMCL的accounts.json可能是列表或字典格式
                if isinstance(accounts_data, list):
                    accounts = accounts_data
                elif isinstance(accounts_data, dict):
                    accounts = accounts_data.get('accounts', [])
                else:
                    continue
                
                # 解析所有账号
                result = []
                for account_data in accounts:
                    parsed = self._parse_hmcl_account(account_data)
                    if parsed:
                        result.append(parsed)
                
                return result
            
            return []
            
        except Exception as e:
            logger.error(f"读取HMCL所有账号失败: {e}")
            return []
    
    def _get_all_pcl_accounts(self) -> List[Dict]:
        """
        获取PCL2所有账号列表
        
        Returns:
            账号列表
        """
        try:
            # PCL2的.minecraft目录可能在多个位置
            minecraft_dirs = [
                self.launcher_dir / '.minecraft',
                self.launcher_dir.parent / '.minecraft',
            ]
            
            for minecraft_dir in minecraft_dirs:
                if not minecraft_dir.exists():
                    continue
                
                launcher_profiles = minecraft_dir / 'launcher_profiles.json'
                if not launcher_profiles.exists():
                    continue
                
                logger.info(f"读取PCL2所有账号: {launcher_profiles}")
                
                with open(launcher_profiles, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                
                # PCL2格式：使用authenticationDatabase
                auth_database = profiles_data.get('authenticationDatabase', {})
                if not auth_database:
                    continue
                
                result = []
                for account_id, account_data in auth_database.items():
                    # 解析每个账号
                    parsed = self._parse_pcl_account_data(account_data)
                    if parsed:
                        result.append(parsed)
                
                if result:  # 如果找到了账号，直接返回
                    return result
            
            return []
            
        except Exception as e:
            logger.error(f"读取PCL2所有账号失败: {e}")
            return []
    
    def _parse_pcl_account_data(self, account_data: Dict) -> Optional[Dict]:
        """
        解析PCL2账号数据
        
        Args:
            account_data: PCL2账号数据
            
        Returns:
            解析后的账号信息
        """
        try:
            # 获取玩家名称
            player_name = account_data.get('username', 'Player')
            
            # 从PCL2的profiles中获取displayName
            profiles = account_data.get('profiles', {})
            if profiles:
                # 获取第一个profile
                first_profile = next(iter(profiles.values()), {})
                display_name = first_profile.get('displayName')
                if display_name:
                    player_name = display_name
            
            access_token = account_data.get('accessToken', 'null')
            
            # 尝试从jwt token中解析UUID
            uuid = None
            if access_token and 'eyJ' in access_token:
                try:
                    import base64
                    parts = access_token.split('.')
                    if len(parts) >= 2:
                        payload = parts[1]
                        padding = 4 - len(payload) % 4
                        if padding:
                            payload += '=' * padding
                        
                        decoded = base64.urlsafe_b64decode(payload)
                        token_data = json.loads(decoded)
                        
                        token_profiles = token_data.get('profiles', {})
                        mc_profile = token_profiles.get('mc')
                        if mc_profile:
                            uuid = mc_profile
                except:
                    pass
            
            # 如果没有从jwt中获取，使用profile_id
            if not uuid and profiles:
                uuid = next(iter(profiles.keys()), '00000000000000000000000000000000')
            
            if not uuid:
                uuid = '00000000000000000000000000000000'
            
            uuid_clean = uuid.replace('-', '')
            
            # 判断账号类型
            account_type = 'offline'
            if access_token and access_token != 'null' and 'eyJ' in access_token:
                account_type = 'microsoft'
            
            # 检查账号是否有效
            if account_type == 'offline':
                is_valid = bool(player_name and uuid_clean)
            else:
                is_valid = bool(access_token and access_token != 'null')
            
            return {
                'player_name': player_name,
                'uuid': uuid_clean,
                'access_token': access_token,
                'account_type': account_type,
                'is_valid': is_valid,
                'raw_data': account_data
            }
            
        except Exception as e:
            logger.error(f"解析PCL2账号数据失败: {e}")
            return None


def test_read_account(launcher_path: str):
    """测试读取账号"""
    print("\n" + "="*60)
    print("🔐 测试启动器账号读取")
    print("="*60)
    print(f"\n启动器路径: {launcher_path}\n")
    
    reader = LauncherAccountReader(launcher_path)
    print(f"启动器类型: {reader.launcher_type}")
    
    account_info = reader.get_account_info()
    
    if account_info:
        print("\n✅ 成功读取账号信息:")
        print(f"   玩家名称: {account_info['player_name']}")
        print(f"   UUID: {account_info['uuid']}")
        print(f"   账号类型: {account_info['account_type']}")
        print(f"   访问令牌: {account_info['access_token'][:20]}..." if len(account_info['access_token']) > 20 else f"   访问令牌: {account_info['access_token']}")
        print(f"   是否有效: {'是' if account_info['is_valid'] else '否'}")
    else:
        print("\n❌ 未能读取账号信息")
        print("   可能原因:")
        print("   1. 启动器中未登录账号")
        print("   2. 配置文件格式不支持")
        print("   3. 配置文件路径不正确")


if __name__ == '__main__':
    """测试"""
    import sys
    
    if len(sys.argv) > 1:
        launcher_path = sys.argv[1]
    else:
        # 默认测试路径
        launcher_path = r"C:\Users\Administrator\Desktop\我的世界\HMCL\HMCL-3.7.6.exe"
    
    test_read_account(launcher_path)
