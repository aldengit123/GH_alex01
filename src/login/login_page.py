"""
登录页面对象
封装登录页面的元素和操作
"""
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By

from ..core.base_page import BasePage
from ..utils.config_loader import config
from ..utils.logger import get_logger


class LoginPage(BasePage):
    """登录页面对象"""
    
    def __init__(self, driver: webdriver.Chrome):
        super().__init__(driver)
        self.logger = get_logger("LoginPage")
        self._load_selectors()
    
    def _load_selectors(self):
        """加载选择器配置"""
        selectors = config.get("login.selectors", {})
        
        self.CLOSE_POPUP = selectors.get(
            "close_popup", 
            "button[class*='close'], [class*='close']"
        )
        self.LOGIN_BUTTON = selectors.get(
            "login_button",
            ".login-btn"
        )
        self.USERNAME_INPUT = selectors.get(
            "username_input",
            "input[type='text']"
        )
        self.PASSWORD_INPUT = selectors.get(
            "password_input",
            "input[type='password']"
        )
        self.SUBMIT_BUTTON = selectors.get(
            "submit_button",
            ".new-submit-button"
        )
        self.CAPTCHA_ELEMENT = selectors.get(
            "captcha_element",
            "[class*='botion_captcha'], [class*='captcha']"
        )
    
    def open(self, url: Optional[str] = None):
        """打开登录页面"""
        login_url = url or config.get("app.login_url")
        self.logger.info(f"正在打开登录页面: {login_url}")
        self.driver.get(login_url)
        time.sleep(3)
    
    def close_popup(self) -> bool:
        """关闭弹窗（如果存在）"""
        self.logger.debug("尝试关闭弹窗...")
        
        # 尝试多种选择器
        selectors = [
            "button[class*='close']",
            "[class*='close']",
            ".dialog button",
            "button:contains('×')"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        self.driver.execute_script("arguments[0].click();", elem)
                        self.logger.info("✓ 弹窗已关闭")
                        time.sleep(1)
                        return True
            except:
                continue
        
        self.logger.debug("无需关闭弹窗")
        return False
    
    def click_login_entry(self) -> bool:
        """点击登录入口按钮"""
        self.logger.debug("点击登录入口...")
        
        # 方法1：使用JavaScript直接查找并点击
        try:
            result = self.driver.execute_script("""
                var loginBtn = document.querySelector('.login-btn');
                if (loginBtn) {
                    loginBtn.click();
                    return true;
                }
                return false;
            """)
            if result:
                self.logger.info("✓ 登录框已打开 (JS方式)")
                time.sleep(3)
                return True
        except:
            pass
        
        # 方法2：使用Selenium查找
        selectors = [
            ".login-btn",
            "[class*='login-btn']",
            "span.login-btn",
        ]
        for selector in selectors:
            try:
                element = self.find_element(By.CSS_SELECTOR, selector, timeout=3)
                if element and element.is_displayed():
                    self.driver.execute_script("arguments[0].click();", element)
                    self.logger.info("✓ 登录框已打开")
                    time.sleep(3)
                    return True
            except:
                continue
        
        # 方法3：文本匹配
        try:
            elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '登录')]")
            for elem in elements:
                if elem.is_displayed() and '注册' not in elem.text:
                    self.driver.execute_script("arguments[0].click();", elem)
                    self.logger.info("✓ 登录框已打开")
                    time.sleep(3)
                    return True
        except:
            pass
        
        self.logger.warning("未能点击登录按钮")
        return False
    
    def input_username(self, username: str) -> bool:
        """输入用户名"""
        self.logger.debug(f"输入用户名: {username}")
        
        # 等待输入框出现
        selectors = [
            "input[type='text']",
            "input[placeholder*='账']",
            "input[placeholder*='用户']"
        ]
        
        for selector in selectors:
            try:
                element = self.find_element(By.CSS_SELECTOR, selector, timeout=5)
                if element and element.is_displayed():
                    element.clear()
                    element.send_keys(username)
                    return True
            except:
                continue
        
        return False
    
    def input_password(self, password: str) -> bool:
        """输入密码"""
        self.logger.debug("输入密码: ********")
        
        selectors = [
            "input[type='password']",
            "input[placeholder*='密码']"
        ]
        
        for selector in selectors:
            try:
                element = self.find_element(By.CSS_SELECTOR, selector, timeout=5)
                if element and element.is_displayed():
                    element.clear()
                    element.send_keys(password)
                    return True
            except:
                continue
        
        return False
    
    def input_credentials(self, username: str, password: str) -> bool:
        """输入账号密码"""
        self.logger.info(f"输入凭证: {username} / ********")
        
        username_ok = self.input_username(username)
        password_ok = self.input_password(password)
        
        if username_ok and password_ok:
            self.logger.info("✓ 凭证输入完成")
            return True
        
        self.logger.warning("凭证输入失败")
        return False
    
    def click_submit(self) -> bool:
        """点击提交/登录按钮"""
        self.logger.debug("点击登录提交按钮...")
        
        try:
            element = self.find_element(By.CSS_SELECTOR, self.SUBMIT_BUTTON, timeout=5)
            if element:
                self.driver.execute_script("arguments[0].click();", element)
                self.logger.info("✓ 登录按钮已点击")
                time.sleep(3)
                return True
        except:
            pass
        
        # 尝试查找包含"登录"文本的按钮
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "登录" in btn.text and btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", btn)
                    self.logger.info("✓ 登录按钮已点击")
                    time.sleep(3)
                    return True
        except:
            pass
        
        self.logger.warning("未能点击登录按钮")
        return False
    
    def is_captcha_present(self) -> bool:
        """检查验证码是否出现"""
        return self.is_element_present(
            By.CSS_SELECTOR, 
            self.CAPTCHA_ELEMENT, 
            timeout=3
        )
    
    def is_login_success(self) -> bool:
        """
        检查是否登录成功
        通过检测token、cookies或页面元素变化来判断
        """
        # 方法1：检查localStorage中的token
        token_keys = config.get("token.storage_keys", ["token", "auth_token", "userToken"])
        for key in token_keys:
            try:
                token = self.driver.execute_script(
                    f"return localStorage.getItem('{key}')"
                )
                if token:
                    self.logger.debug(f"检测到token: {key}")
                    return True
            except:
                pass
        
        # 方法2：检查URL（备用）
        current_url = self.get_current_url()
        success_keywords = config.get("app.success_url_keywords", ["lobby", "home"])
        if any(keyword in current_url for keyword in success_keywords):
            return True
        
        # 方法3：检查是否有用户相关元素
        try:
            user_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "[class*='user-info'], [class*='balance'], [class*='wallet']"
            )
            if user_elements and any(e.is_displayed() for e in user_elements):
                return True
        except:
            pass
        
        return False
