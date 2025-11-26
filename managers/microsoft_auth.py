# -*- coding: utf-8 -*-
"""
Microsoft账号认证与Token刷新
用于刷新过期的Microsoft accessToken
"""
import json
import requests
from typing import Dict, Optional
from utils.logger import Logger

logger = Logger().get_logger("MicrosoftAuth")


class MicrosoftAuthRefresher:
    """Microsoft账号认证刷新器"""
    
    # Microsoft认证端点
    OAUTH_TOKEN_URL = "https://login.live.com/oauth20_token.srf"
    XBOX_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
    XSTS_AUTH_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
    MC_AUTH_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
    MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def refresh_token_from_launcher(self, launcher_path: str) -> Optional[Dict]:
        """
        从启动器读取refreshToken并刷新accessToken
        
        Args:
            launcher_path: 启动器路径
            
        Returns:
            刷新后的账号信息，包含新的accessToken
        """
        try:
            from pathlib import Path
            
            launcher_path = Path(launcher_path)
            launcher_dir = launcher_path.parent
            
            # 查找launcher_profiles.json
            minecraft_dirs = [
                launcher_dir / '.minecraft',
                launcher_dir.parent / '.minecraft',
            ]
            
            for minecraft_dir in minecraft_dirs:
                profiles_file = minecraft_dir / 'launcher_profiles.json'
                if not profiles_file.exists():
                    continue
                
                logger.info(f"读取启动器配置: {profiles_file}")
                
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                
                # 获取当前账号
                selected_user = profiles_data.get('selectedUser', {})
                auth_database = profiles_data.get('authenticationDatabase', {})
                
                if not selected_user or not auth_database:
                    continue
                
                account_id = selected_user.get('account')
                if not account_id or account_id not in auth_database:
                    continue
                
                account_data = auth_database[account_id]
                
                # 检查是否有refreshToken
                # PCL2的配置文件中可能没有存储refreshToken
                # 因为PCL2使用了自己的认证缓存机制
                refresh_token = account_data.get('refreshToken')
                
                if not refresh_token:
                    logger.warning("⚠️ 启动器配置中没有找到refreshToken")
                    logger.warning("   PCL2可能使用了独立的认证缓存")
                    return None
                
                # 使用refreshToken刷新accessToken
                logger.info("开始刷新Microsoft token...")
                new_token_data = self._refresh_microsoft_token(refresh_token)
                
                if new_token_data:
                    # 更新配置文件
                    account_data['accessToken'] = new_token_data['access_token']
                    if 'refresh_token' in new_token_data:
                        account_data['refreshToken'] = new_token_data['refresh_token']
                    
                    # 保存回文件
                    with open(profiles_file, 'w', encoding='utf-8') as f:
                        json.dump(profiles_data, f, indent=2, ensure_ascii=False)
                    
                    logger.info("✅ Token刷新成功并已保存到配置文件")
                    
                    return {
                        'player_name': account_data.get('username', 'Player'),
                        'uuid': self._extract_uuid_from_token(new_token_data['access_token']),
                        'access_token': new_token_data['access_token'],
                        'account_type': 'microsoft',
                        'is_valid': True
                    }
                else:
                    logger.error("❌ Token刷新失败")
                    return None
            
            logger.warning("未找到有效的启动器配置")
            return None
            
        except Exception as e:
            logger.error(f"刷新token失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _refresh_microsoft_token(self, refresh_token: str) -> Optional[Dict]:
        """
        使用refreshToken刷新accessToken
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            新的token数据
        """
        try:
            # 步骤1: 刷新Microsoft OAuth token
            logger.info("步骤1/6: 刷新Microsoft OAuth token...")
            
            # 注意：这里需要client_id，但PCL2可能使用了自己的client_id
            # 我们需要从PCL2的配置或代码中获取
            # 这是一个简化实现，实际可能需要更多参数
            
            oauth_data = {
                'client_id': '00000000402b5328',  # 这是Minecraft官方的client_id
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
                'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
                'scope': 'service::user.auth.xboxlive.com::MBI_SSL'
            }
            
            response = self.session.post(
                self.OAUTH_TOKEN_URL,
                data=oauth_data,
                timeout=25
            )
            
            if response.status_code != 200:
                logger.error(f"OAuth刷新失败: {response.status_code}")
                logger.error(f"响应: {response.text}")
                return None
            
            oauth_result = response.json()
            access_token = oauth_result.get('access_token')
            new_refresh_token = oauth_result.get('refresh_token', refresh_token)
            
            if not access_token:
                logger.error("OAuth响应中没有access_token")
                return None
            
            logger.info("✓ OAuth token刷新成功")
            
            # 步骤2: Xbox Live认证
            logger.info("步骤2/6: Xbox Live认证...")
            xbox_auth_data = {
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={access_token}"
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT"
            }
            
            response = self.session.post(
                self.XBOX_AUTH_URL,
                json=xbox_auth_data,
                timeout=25
            )
            
            if response.status_code != 200:
                logger.error(f"Xbox Live认证失败: {response.status_code}")
                return None
            
            xbox_result = response.json()
            xbox_token = xbox_result.get('Token')
            user_hash = xbox_result.get('DisplayClaims', {}).get('xui', [{}])[0].get('uhs')
            
            logger.info("✓ Xbox Live认证成功")
            
            # 步骤3: XSTS认证
            logger.info("步骤3/6: XSTS认证...")
            xsts_auth_data = {
                "Properties": {
                    "SandboxId": "RETAIL",
                    "UserTokens": [xbox_token]
                },
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT"
            }
            
            response = self.session.post(
                self.XSTS_AUTH_URL,
                json=xsts_auth_data,
                timeout=25
            )
            
            if response.status_code != 200:
                logger.error(f"XSTS认证失败: {response.status_code}")
                return None
            
            xsts_result = response.json()
            xsts_token = xsts_result.get('Token')
            
            logger.info("✓ XSTS认证成功")
            
            # 步骤4: Minecraft登录
            logger.info("步骤4/6: Minecraft登录...")
            mc_auth_data = {
                "identityToken": f"XBL3.0 x={user_hash};{xsts_token}",
                "ensureLegacyEnabled": True
            }
            
            response = self.session.post(
                self.MC_AUTH_URL,
                json=mc_auth_data,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Minecraft登录失败: {response.status_code}")
                return None
            
            mc_result = response.json()
            mc_access_token = mc_result.get('access_token')
            
            logger.info("✓ Minecraft登录成功")
            logger.info(f"  新Token长度: {len(mc_access_token)}")
            
            return {
                'access_token': mc_access_token,
                'refresh_token': new_refresh_token,
                'expires_in': mc_result.get('expires_in', 86400)
            }
            
        except Exception as e:
            logger.error(f"刷新Microsoft token失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_uuid_from_token(self, access_token: str) -> str:
        """
        从JWT token中提取UUID
        
        Args:
            access_token: JWT格式的accessToken
            
        Returns:
            UUID（去掉横线）
        """
        try:
            import base64
            
            # JWT格式: header.payload.signature
            parts = access_token.split('.')
            if len(parts) < 2:
                return '00000000000000000000000000000000'
            
            # 解码payload
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding and padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            token_data = json.loads(decoded)
            
            # 从profiles.mc中提取UUID
            profiles = token_data.get('profiles', {})
            mc_profile = profiles.get('mc')
            
            if mc_profile:
                return mc_profile.replace('-', '')
            
            return '00000000000000000000000000000000'
            
        except Exception as e:
            logger.warning(f"从token提取UUID失败: {e}")
            return '00000000000000000000000000000000'


def test_refresh_token(launcher_path: str):
    """测试token刷新"""
    print("\n" + "="*60)
    print("🔄 测试Microsoft Token刷新")
    print("="*60)
    print(f"\n启动器路径: {launcher_path}\n")
    
    refresher = MicrosoftAuthRefresher()
    result = refresher.refresh_token_from_launcher(launcher_path)
    
    if result:
        print("\n✅ Token刷新成功:")
        print(f"   玩家名称: {result['player_name']}")
        print(f"   UUID: {result['uuid']}")
        print(f"   新Token: {result['access_token'][:50]}...")
        print(f"   Token长度: {len(result['access_token'])}")
    else:
        print("\n❌ Token刷新失败")
        print("   可能原因:")
        print("   1. 启动器配置中没有refreshToken")
        print("   2. refreshToken已过期")
        print("   3. 网络连接问题")


if __name__ == '__main__':
    """测试"""
    import sys
    
    if len(sys.argv) > 1:
        launcher_path = sys.argv[1]
    else:
        # 默认测试路径
        launcher_path = r"C:\Users\Administrator\Desktop\我的世界\PCL2\Plain Craft Launcher 2.exe"
    
    test_refresh_token(launcher_path)
