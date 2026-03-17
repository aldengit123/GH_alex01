"""
浏览器管理器
负责创建和管理WebDriver实例，支持会话复用
"""
import os
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from ..utils.logger import get_logger
from ..utils.config_loader import config
from ..utils.constants import MANUAL_LOGIN_TIMEOUT, CHECK_INTERVAL


class BrowserManager:
    """
    浏览器管理器 - 核心类
    负责创建浏览器并支持会话复用
    """
    
    def __init__(self):
        self.logger = get_logger("BrowserManager")
        self.driver: Optional[webdriver.Chrome] = None
        self._chromedriver_path = self._find_chromedriver()
    
    def _find_chromedriver(self) -> Optional[str]:
        """使用webdriver-manager自动获取匹配当前Chrome版本的chromedriver"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            raw_path = ChromeDriverManager().install()
            parent = os.path.dirname(raw_path)

            # webdriver-manager 某些版本会返回 THIRD_PARTY_NOTICES 等非可执行文件
            # 这里按平台优先挑选真正的驱动二进制
            candidates = []
            if os.name == 'nt':
                candidates = [
                    raw_path,
                    os.path.join(parent, 'chromedriver.exe'),
                    os.path.join(parent, 'chromedriver'),
                ]
            else:
                candidates = [
                    raw_path,
                    os.path.join(parent, 'chromedriver'),
                ]

            for candidate in candidates:
                if os.path.isfile(candidate):
                    name = os.path.basename(candidate).lower()
                    if name.startswith('chromedriver'):
                        self.logger.debug(f"chromedriver: {candidate}")
                        return candidate

            self.logger.warning(f"未找到有效的chromedriver可执行文件，webdriver-manager返回: {raw_path}")
            return None
        except Exception as e:
            self.logger.debug(f"webdriver-manager获取失败({e})，使用Selenium内置管理")
            return None
    
    def create_driver(
        self,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
        mobile_emulation: bool = True
    ) -> webdriver.Chrome:
        """
        创建Chrome WebDriver
        
        Args:
            user_data_dir: 用户数据目录（用于保存会话状态）
            headless: 是否无头模式
            mobile_emulation: 是否启用移动端模拟
        
        Returns:
            WebDriver实例
        """
        self.logger.info("正在创建浏览器实例...")
        
        options = Options()
        
        # 基础配置
        if headless:
            options.add_argument('--headless=new')
        
        # 反自动化检测（增强版）
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 其他优化参数
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        
        # 用户数据目录（关键：保存所有浏览器状态）
        if user_data_dir:
            os.makedirs(user_data_dir, exist_ok=True)
            options.add_argument(f'--user-data-dir={os.path.abspath(user_data_dir)}')
            self.logger.info(f"使用用户数据目录: {user_data_dir}")
        
        # 移动端模拟
        if mobile_emulation:
            browser_config = config.browser
            mobile_config = {
                "deviceMetrics": {
                    "width": browser_config.get("device_width", 375),
                    "height": browser_config.get("device_height", 812),
                    "pixelRatio": browser_config.get("pixel_ratio", 3.0)
                },
                "userAgent": browser_config.get(
                    "user_agent",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15"
                )
            }
            options.add_experimental_option("mobileEmulation", mobile_config)
            self.logger.debug("已启用移动端模拟")
        
        # 创建WebDriver
        try:
            if self._chromedriver_path:
                if os.name != 'nt':
                    os.chmod(self._chromedriver_path, 0o755)
                service = Service(self._chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            # 注入反检测脚本
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = { runtime: {} };
                '''
            })
            
            self.logger.info("✅ 浏览器创建成功")
            return self.driver
            
        except WebDriverException as e:
            self.logger.error(f"❌ 创建浏览器失败: {e}")
            raise
    
    def wait_for_manual_login(
        self,
        driver: webdriver.Chrome,
        timeout: int = MANUAL_LOGIN_TIMEOUT,
        check_interval: int = CHECK_INTERVAL
    ) -> bool:
        """
        等待用户手动完成登录（包括滑块验证）
        
        Args:
            driver: WebDriver实例
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）
        
        Returns:
            是否登录成功
        """
        self.logger.info("="*60)
        self.logger.info("⏳ 请在浏览器中手动完成登录和滑块验证...")
        self.logger.info("="*60)
        
        start_time = time.time()
        initial_url = driver.current_url
        
        success_keywords = config.get("app.success_url_keywords", ["lobby", "home", "dashboard"])
        token_keys = config.get("token.storage_keys", ["token", "auth_token"])
        
        # 登录成功的标识元素选择器（余额、钱包等）
        success_element_selectors = [
            "[class*='balance']",
            "[class*='wallet']", 
            "[class*='money']",
            "[class*='coin']",
            "[class*='amount']",
            "[class*='user-money']",
            "[class*='my-money']",
        ]
        
        while time.time() - start_time < timeout:
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            
            try:
                # 检查方法1：检测余额/钱包等登录后才会出现的元素（最可靠）
                for selector in success_element_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                self.logger.info(f"✅ 检测到余额/钱包元素出现，登录成功！")
                                self.logger.info(f"   选择器: {selector}")
                                return True
                    except:
                        pass
                
                # 检查方法2：登录按钮消失
                try:
                    login_btn = driver.find_elements(By.CSS_SELECTOR, ".login-btn")
                    login_btn_visible = any(e.is_displayed() for e in login_btn if e)
                    if not login_btn_visible and elapsed > 10:
                        # 登录按钮消失了，可能登录成功
                        self.logger.info("✅ 登录按钮已消失，登录成功！")
                        return True
                except:
                    pass
                
                # 检查方法3：URL变化（备用）
                current_url = driver.current_url
                if current_url and any(keyword in current_url for keyword in success_keywords):
                    self.logger.info(f"✅ 检测到URL变化，登录成功！")
                    return True
                
                # 显示进度
                if elapsed % 10 == 0:
                    self.logger.info(f"⏳ 等待中... {elapsed}/{timeout}秒 (剩余{remaining}秒)")
                
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.debug(f"检测过程出错: {e}")
                time.sleep(check_interval)
        
        self.logger.warning("⚠️ 等待手动登录超时")
        return False
    
    def is_session_valid(self, driver: webdriver.Chrome, silent: bool = False) -> bool:
        """
        检查当前会话是否有效（已登录状态）
        核心检测：余额/钱包元素出现且有实际内容 + 登录按钮不存在
        
        Args:
            driver: WebDriver实例
            silent: 静默模式，不输出失败日志
        
        Returns:
            是否是有效的登录状态
        """
        try:
            # 访问主页
            base_url = config.get("app.base_url")
            driver.get(base_url)
            time.sleep(3)
            
            # 先检查是否有登录按钮（如果有，说明未登录）
            login_selectors = [
                ".login-btn",
                "[class*='login-btn']",
                "[class*='loginBtn']",
                "button[class*='login']",
                "[class*='unlogin']",
                "[class*='not-login']",
            ]
            
            for selector in login_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            text = elem.text.strip()
                            if text and any(kw in text for kw in ['登录', '注册', 'Login', 'Sign']):
                                if not silent:
                                    self.logger.info(f"❌ 检测到登录按钮，会话无效")
                                return False
                except:
                    pass
            
            # 检查是否有"被挤掉"或"重新登录"的提示
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                kicked_keywords = ['重新登录', '已在其他', '被迫下线', '登录已过期', '请重新登录', '会话过期']
                if any(kw in body_text for kw in kicked_keywords):
                    if not silent:
                        self.logger.info(f"❌ 检测到会话失效提示，需要重新登录")
                    return False
            except:
                pass
            
            # 登录成功后会出现的元素（余额、钱包等）
            success_selectors = [
                "[class*='balance']",
                "[class*='wallet']", 
                "[class*='money']",
                "[class*='coin']",
                "[class*='amount']",
                "[class*='user-info']",
                "[class*='userInfo']",
            ]
            
            # 检测余额/钱包元素出现且有内容
            for selector in success_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            text = elem.text.strip()
                            # 确保有实际内容（数字或货币符号）
                            if text and (any(c.isdigit() for c in text) or '¥' in text or '$' in text):
                                self.logger.info(f"✅ 会话有效，检测到余额/钱包元素: {selector} (内容: {text[:20]})")
                                return True
                except:
                    pass
            
            if not silent:
                self.logger.debug("会话检测未通过")
            return False
            
        except Exception as e:
            self.logger.error(f"检查会话状态失败: {e}")
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("浏览器已关闭")
            except:
                pass
            finally:
                self.driver = None
    
    def __del__(self):
        """析构函数"""
        self.close()
