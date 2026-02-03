"""
缓存管理器
负责保存和恢复浏览器会话状态（cookies、localStorage、sessionStorage）
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from selenium import webdriver

from ..utils.logger import get_logger
from ..utils.config_loader import config
from ..utils.constants import (
    COOKIES_FILE, 
    STORAGE_FILE, 
    SESSION_INFO_FILE,
    CacheStatus
)


class CacheManager:
    """
    缓存管理器
    负责保存和恢复浏览器会话状态
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = get_logger("CacheManager")
        self.cache_dir = cache_dir or config.get("cache.cache_dir", "./cache/user_session")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_session_dir(self, session_name: str) -> str:
        """获取会话目录路径"""
        session_dir = os.path.join(self.cache_dir, session_name)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir
    
    def save_session(
        self, 
        driver: webdriver.Chrome, 
        session_name: str = "default"
    ) -> bool:
        """
        保存当前浏览器会话
        
        Args:
            driver: WebDriver实例
            session_name: 会话名称
        
        Returns:
            是否保存成功
        """
        self.logger.info(f"正在保存会话: {session_name}")
        
        try:
            session_dir = self._get_session_dir(session_name)
            
            # 1. 保存Cookies
            cookies = driver.get_cookies()
            cookies_path = os.path.join(session_dir, COOKIES_FILE)
            with open(cookies_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"已保存 {len(cookies)} 个cookies")
            
            # 2. 保存localStorage和sessionStorage
            storage_data = self._extract_storage(driver)
            storage_path = os.path.join(session_dir, STORAGE_FILE)
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(storage_data, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"已保存storage数据")
            
            # 3. 保存会话元信息
            session_info = {
                "session_name": session_name,
                "created_at": datetime.now().isoformat(),
                "url": driver.current_url,
                "cookies_count": len(cookies),
                "local_storage_keys": list(storage_data.get("localStorage", {}).keys()),
                "expire_hours": config.get("cache.expire_hours", 24)
            }
            info_path = os.path.join(session_dir, SESSION_INFO_FILE)
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 会话保存成功: {session_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 保存会话失败: {e}")
            return False
    
    def load_session(
        self, 
        driver: webdriver.Chrome, 
        session_name: str = "default"
    ) -> bool:
        """
        加载已保存的会话到浏览器
        
        Args:
            driver: WebDriver实例
            session_name: 会话名称
        
        Returns:
            是否加载成功
        """
        self.logger.info(f"正在加载会话: {session_name}")
        
        try:
            session_dir = self._get_session_dir(session_name)
            
            # 检查文件是否存在
            cookies_path = os.path.join(session_dir, COOKIES_FILE)
            storage_path = os.path.join(session_dir, STORAGE_FILE)
            
            if not os.path.exists(cookies_path):
                self.logger.warning("会话文件不存在")
                return False
            
            # 先访问目标域名（设置cookie前必须）
            base_url = config.get("app.base_url")
            driver.get(base_url)
            time.sleep(2)
            
            # 1. 加载Cookies
            with open(cookies_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                try:
                    # 移除可能导致问题的字段
                    for key in ['sameSite', 'expiry', 'expires']:
                        cookie.pop(key, None)
                    driver.add_cookie(cookie)
                except Exception as e:
                    self.logger.debug(f"添加cookie失败: {cookie.get('name')} - {e}")
            
            self.logger.debug(f"已加载 {len(cookies)} 个cookies")
            
            # 2. 加载localStorage
            if os.path.exists(storage_path):
                with open(storage_path, 'r', encoding='utf-8') as f:
                    storage_data = json.load(f)
                
                self._restore_storage(driver, storage_data)
                self.logger.debug("已加载storage数据")
            
            # 3. 刷新页面使cookie生效
            driver.refresh()
            time.sleep(2)
            
            self.logger.info("✅ 会话加载成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 加载会话失败: {e}")
            return False
    
    def _extract_storage(self, driver: webdriver.Chrome) -> Dict[str, Dict]:
        """提取浏览器存储数据"""
        storage_data = {
            "localStorage": {},
            "sessionStorage": {}
        }
        
        try:
            # 提取localStorage
            local_storage = driver.execute_script("""
                let items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    let key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            """)
            storage_data["localStorage"] = local_storage or {}
            
            # 提取sessionStorage
            session_storage = driver.execute_script("""
                let items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    let key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
            """)
            storage_data["sessionStorage"] = session_storage or {}
            
        except Exception as e:
            self.logger.warning(f"提取storage失败: {e}")
        
        return storage_data
    
    def _restore_storage(self, driver: webdriver.Chrome, storage_data: Dict):
        """恢复浏览器存储数据"""
        try:
            # 恢复localStorage
            local_storage = storage_data.get("localStorage", {})
            for key, value in local_storage.items():
                driver.execute_script(
                    f"localStorage.setItem('{key}', '{value}')"
                )
            
            # 恢复sessionStorage
            session_storage = storage_data.get("sessionStorage", {})
            for key, value in session_storage.items():
                driver.execute_script(
                    f"sessionStorage.setItem('{key}', '{value}')"
                )
                
        except Exception as e:
            self.logger.warning(f"恢复storage失败: {e}")
    
    def get_cache_status(self, session_name: str = "default") -> str:
        """
        获取缓存状态
        
        Returns:
            CacheStatus枚举值
        """
        session_dir = self._get_session_dir(session_name)
        info_path = os.path.join(session_dir, SESSION_INFO_FILE)
        
        # 检查文件是否存在
        if not os.path.exists(info_path):
            return CacheStatus.NOT_FOUND
        
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                session_info = json.load(f)
            
            # 检查是否过期
            created_at = datetime.fromisoformat(session_info["created_at"])
            expire_hours = session_info.get("expire_hours", 24)
            expire_time = created_at + timedelta(hours=expire_hours)
            
            if datetime.now() > expire_time:
                self.logger.info(f"缓存已过期: {created_at} + {expire_hours}h")
                return CacheStatus.EXPIRED
            
            return CacheStatus.VALID
            
        except Exception as e:
            self.logger.error(f"读取缓存信息失败: {e}")
            return CacheStatus.INVALID
    
    def extract_token(self, driver: webdriver.Chrome) -> Optional[str]:
        """
        从浏览器中提取token
        
        Returns:
            token字符串或None
        """
        token_keys = config.get("token.storage_keys", ["token", "auth_token"])
        
        # 从localStorage查找
        for key in token_keys:
            try:
                token = driver.execute_script(
                    f"return localStorage.getItem('{key}')"
                )
                if token:
                    self.logger.debug(f"从localStorage提取到token: {key}")
                    return token
            except:
                pass
        
        # 从cookie查找
        cookie_names = config.get("token.cookie_names", ["token", "session"])
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] in cookie_names:
                self.logger.debug(f"从cookie提取到token: {cookie['name']}")
                return cookie['value']
        
        return None
    
    def clear_session(self, session_name: str = "default") -> bool:
        """
        清除会话缓存
        
        Args:
            session_name: 会话名称
        
        Returns:
            是否清除成功
        """
        try:
            session_dir = self._get_session_dir(session_name)
            
            for filename in [COOKIES_FILE, STORAGE_FILE, SESSION_INFO_FILE]:
                filepath = os.path.join(session_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            self.logger.info(f"已清除会话缓存: {session_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"清除缓存失败: {e}")
            return False
