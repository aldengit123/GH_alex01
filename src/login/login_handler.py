"""
登录处理器
实现半自动化登录流程：自动输入凭证 + 等待人工处理验证码 + 保存会话
"""
import time
from typing import Optional

from selenium import webdriver

from ..core.browser_manager import BrowserManager
from ..core.cache_manager import CacheManager
from ..utils.config_loader import config
from ..utils.logger import get_logger
from ..utils.constants import CacheStatus, MANUAL_LOGIN_TIMEOUT
from .login_page import LoginPage


class LoginHandler:
    """
    登录处理器
    实现半自动化登录流程
    """
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session_name: str = "default",
        cache_enabled: bool = True
    ):
        self.logger = get_logger("LoginHandler")
        
        # 加载账号配置
        self.username = username or config.get("account.username")
        self.password = password or config.get("account.password")
        self.session_name = session_name
        self.cache_enabled = cache_enabled
        
        # 初始化管理器
        self.browser_manager = BrowserManager()
        self.cache_manager = CacheManager()
        
        # 当前状态
        self.driver: Optional[webdriver.Chrome] = None
        self.login_page: Optional[LoginPage] = None
    
    def semi_auto_login(self) -> Optional[webdriver.Chrome]:
        """
        半自动登录主流程
        
        流程：
        1. 检查是否存在有效缓存
        2. 如果有效，直接复用
        3. 如果无效：
           a. 创建浏览器
           b. 打开登录页
           c. 自动输入账号密码
           d. 点击登录
           e. 等待人工处理滑块
           f. 验证登录成功
           g. 保存会话缓存
        4. 返回已登录的driver
        
        Returns:
            已登录的WebDriver实例，失败返回None
        """
        self.logger.info("="*60)
        self.logger.info("        半自动登录流程开始")
        self.logger.info("="*60)
        
        # 获取缓存目录
        cache_dir = config.get("cache.cache_dir", "./cache/user_session")
        user_data_dir = f"{cache_dir}/{self.session_name}/browser_data"
        
        # Step 1: 检查缓存状态
        if self.cache_enabled:
            cache_status = self.cache_manager.get_cache_status(self.session_name)
            self.logger.info(f"📦 缓存状态: {cache_status}")
            
            if cache_status == CacheStatus.VALID:
                # 尝试使用缓存登录
                self.logger.info("🔄 尝试使用缓存会话...")
                
                if self._try_cached_login(user_data_dir):
                    self.logger.info("✅ 缓存会话有效，已成功登录")
                    return self.driver
                
                # 缓存失效，清除旧缓存后重新登录
                self.logger.info("🗑️ 清除失效的缓存数据...")
                self._clear_browser_cache(user_data_dir)
        
        # Step 2: 执行新登录流程
        self.logger.info("\n🚀 开始新登录流程...")
        
        try:
            # 2.1 创建浏览器
            self.driver = self.browser_manager.create_driver(
                user_data_dir=user_data_dir,
                headless=config.get("browser.headless", False),
                mobile_emulation=config.get("browser.mobile_emulation", True)
            )
            
            # 2.2 初始化登录页面对象
            self.login_page = LoginPage(self.driver)
            
            # 2.3 执行登录步骤
            login_result = self._perform_login_steps()
            
            if login_result == "already_logged_in":
                # 已经是登录状态，无需验证码
                self.logger.info("✅ 浏览器已是登录状态，跳过验证码")
            elif login_result:
                # 正常完成登录步骤，检查是否需要验证码
                # 2.4 等待人工处理验证码
                if self.login_page.is_captcha_present():
                    self.logger.info("\n🧩 检测到验证码，等待人工处理...")
                    if not self._wait_for_manual_verification():
                        self.logger.error("❌ 验证码处理超时或失败")
                        return None
                
                # 2.5 验证登录结果
                if not self._verify_login_success():
                    self.logger.error("❌ 登录验证失败")
                    return None
            else:
                self.logger.error("❌ 登录步骤执行失败")
                return None
            
            # 2.6 保存会话
            if self.cache_enabled:
                self.cache_manager.save_session(self.driver, self.session_name)
            
            self.logger.info("\n" + "="*60)
            self.logger.info("        ✅ 登录成功！")
            self.logger.info("="*60 + "\n")
            
            return self.driver
            
        except Exception as e:
            self.logger.error(f"❌ 登录过程出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _clear_browser_cache(self, user_data_dir: str):
        """清除浏览器缓存数据"""
        import shutil
        import os
        import subprocess
        
        try:
            # 清除session缓存（cookies、localStorage等）
            self.cache_manager.clear_session(self.session_name)
            self.logger.info("  ✓ 清除session缓存")
        except Exception as e:
            self.logger.debug(f"清除session缓存出错: {e}")
        
        # 关闭可能占用目录的Chrome进程
        try:
            subprocess.run(['pkill', '-f', 'chrome'], capture_output=True, timeout=5)
            time.sleep(1)  # 等待进程退出
        except:
            pass
        
        # 清除浏览器用户数据目录
        if os.path.exists(user_data_dir):
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    shutil.rmtree(user_data_dir)
                    self.logger.info("  ✓ 清除浏览器用户数据目录")
                    break
                except Exception as e:
                    if attempt < max_attempts - 1:
                        time.sleep(1)
                    else:
                        self.logger.warning(f"清除用户数据目录失败: {e}")
    
    def _try_cached_login(self, user_data_dir: str) -> bool:
        """尝试使用缓存会话登录"""
        try:
            # 使用缓存的用户数据目录创建浏览器
            self.driver = self.browser_manager.create_driver(
                user_data_dir=user_data_dir,
                headless=config.get("browser.headless", False),
                mobile_emulation=config.get("browser.mobile_emulation", True)
            )
            
            # 检查会话是否有效（静默模式，不输出失败日志）
            if self.browser_manager.is_session_valid(self.driver, silent=True):
                return True
            
            # 尝试加载保存的cookies和storage
            self.logger.debug("浏览器数据目录会话未检测到，尝试加载cookies...")
            if self.cache_manager.load_session(self.driver, self.session_name):
                # 再次检查（这次输出结果）
                time.sleep(2)
                if self.browser_manager.is_session_valid(self.driver):
                    return True
            
            self.logger.info("❌ 缓存会话无效，需要重新登录")
            # 缓存无效，关闭浏览器以便重新创建
            self.browser_manager.close()
            self.driver = None
            return False
            
        except Exception as e:
            self.logger.warning(f"缓存登录失败: {e}")
            # 确保关闭浏览器
            if self.driver:
                try:
                    self.browser_manager.close()
                except:
                    pass
                self.driver = None
            return False
    
    def _perform_login_steps(self):
        """
        执行登录步骤（自动化部分）
        
        Returns:
            "already_logged_in": 已经是登录状态
            True: 登录步骤执行成功
            False: 登录步骤执行失败
        """
        self.logger.info("\n📋 执行自动化登录步骤...")
        
        # Step 1: 打开登录页
        self.logger.info("🔹 [1/5] 打开登录页面...")
        self.login_page.open()
        
        # 检查是否已经登录（可能是缓存的浏览器状态）
        if self.login_page.is_login_success():
            self.logger.info("✅ 检测到已登录状态（浏览器缓存）")
            return "already_logged_in"
        
        # Step 2: 关闭弹窗
        self.logger.info("🔹 [2/5] 检查并关闭弹窗...")
        self.login_page.close_popup()
        time.sleep(2)
        
        # Step 3: 点击登录入口
        self.logger.info("🔹 [3/5] 点击登录入口...")
        if not self.login_page.click_login_entry():
            self.logger.warning("未能打开登录框，尝试继续...")
        time.sleep(2)
        
        # Step 4: 输入账号密码
        self.logger.info("🔹 [4/5] 输入账号密码...")
        if not self.login_page.input_credentials(self.username, self.password):
            self.logger.error("输入凭证失败")
            return False
        time.sleep(1)
        
        # Step 5: 点击登录按钮
        self.logger.info("🔹 [5/5] 点击登录按钮...")
        if not self.login_page.click_submit():
            self.logger.error("点击登录按钮失败")
            return False
        
        self.logger.info("✓ 自动化步骤完成\n")
        return True
    
    def _wait_for_manual_verification(self) -> bool:
        """等待人工处理验证码"""
        self.logger.info("\n" + "="*60)
        self.logger.info("⏳ 请在浏览器中手动完成滑块验证...")
        self.logger.info("="*60)
        self.logger.info("👉 找到验证码滑块")
        self.logger.info("👉 拖动滑块完成验证")
        self.logger.info("👉 脚本会自动检测登录状态")
        self.logger.info("="*60 + "\n")
        
        timeout = config.get("login.timeout", MANUAL_LOGIN_TIMEOUT)
        return self.browser_manager.wait_for_manual_login(
            self.driver, 
            timeout=timeout
        )
    
    def _verify_login_success(self) -> bool:
        """
        验证登录是否成功
        核心检测：余额/钱包元素出现 或 登录按钮消失
        """
        self.logger.info("🔍 验证登录状态...")
        
        # 等待页面稳定
        time.sleep(2)
        
        from selenium.webdriver.common.by import By
        
        # 登录成功后会出现的元素（余额、钱包等）
        success_selectors = [
            "[class*='balance']",
            "[class*='wallet']", 
            "[class*='money']",
            "[class*='coin']",
            "[class*='amount']",
        ]
        
        # 检测方法1：余额/钱包元素出现（最可靠）
        for selector in success_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        self.logger.info(f"✓ 验证通过 - 检测到余额/钱包元素: {selector}")
                        return True
            except:
                pass
        
        # 检测方法2：登录按钮消失
        try:
            login_btn = self.driver.find_elements(By.CSS_SELECTOR, ".login-btn")
            login_btn_visible = any(e.is_displayed() for e in login_btn if e)
            if not login_btn_visible:
                self.logger.info("✓ 验证通过 - 登录按钮已消失")
                return True
        except:
            pass
        
        self.logger.warning(f"❌ 登录验证失败，当前URL: {self.driver.current_url}")
        return False
    
    def get_driver(self) -> Optional[webdriver.Chrome]:
        """获取WebDriver实例"""
        return self.driver
    
    def close(self):
        """关闭浏览器"""
        if self.browser_manager:
            self.browser_manager.close()
        self.driver = None
    
    def clear_cache(self):
        """清除会话缓存"""
        self.cache_manager.clear_session(self.session_name)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        # 注意：不自动关闭，让用户决定何时关闭
        pass
