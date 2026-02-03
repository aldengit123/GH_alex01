"""
页面基类
所有Page Object的基类
"""
import time
from typing import List, Optional, Tuple, Callable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from ..utils.logger import get_logger
from ..utils.constants import DEFAULT_TIMEOUT


class BasePage:
    """页面基类"""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.logger = get_logger(self.__class__.__name__)
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
    
    # ==================== 显式等待工具方法 ====================
    
    def wait_for(
        self, 
        condition: Callable, 
        timeout: int = DEFAULT_TIMEOUT, 
        poll: float = 0.5,
        message: str = ""
    ) -> bool:
        """
        通用显式等待
        
        Args:
            condition: 等待条件（返回True表示成功）
            timeout: 超时时间（秒）
            poll: 轮询间隔（秒）
            message: 超时提示
        """
        try:
            WebDriverWait(self.driver, timeout, poll_frequency=poll).until(lambda d: condition())
            return True
        except TimeoutException:
            if message:
                self.logger.debug(f"等待超时: {message}")
            return False
    
    def wait_for_element_clickable(
        self, 
        by: By, 
        value: str, 
        timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[WebElement]:
        """等待元素可点击"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            return None
    
    def wait_for_element_visible(
        self, 
        by: By, 
        value: str, 
        timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[WebElement]:
        """等待元素可见"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        except TimeoutException:
            return None
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """等待页面加载完成"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            return False
    
    def wait_for_url_change(self, old_url: str, timeout: int = 10) -> bool:
        """等待URL变化"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.current_url != old_url
            )
            return True
        except TimeoutException:
            return False
    
    def wait_for_text_present(
        self, 
        text: str, 
        timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        """等待页面中出现指定文本"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: text in d.find_element(By.TAG_NAME, "body").text
            )
            return True
        except TimeoutException:
            return False
    
    def wait_and_click_js(
        self, 
        by: By, 
        value: str, 
        timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        """等待元素可见后使用JS点击"""
        element = self.wait_for_element_visible(by, value, timeout)
        if element:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                pass
        return False
    
    def find_element(
        self, 
        by: By, 
        value: str, 
        timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[WebElement]:
        """
        查找元素
        
        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间
        
        Returns:
            WebElement或None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.debug(f"元素未找到: {by}={value}")
            return None
    
    def find_elements(
        self, 
        by: By, 
        value: str, 
        timeout: int = DEFAULT_TIMEOUT
    ) -> List[WebElement]:
        """查找多个元素"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            return []
    
    def click(
        self, 
        by: By, 
        value: str, 
        timeout: int = DEFAULT_TIMEOUT,
        use_js: bool = False
    ) -> bool:
        """
        点击元素
        
        Args:
            by: 定位方式
            value: 定位值
            timeout: 超时时间
            use_js: 是否使用JavaScript点击
        
        Returns:
            是否点击成功
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            
            if use_js:
                self.driver.execute_script("arguments[0].click();", element)
            else:
                element.click()
            
            self.logger.debug(f"点击元素: {by}={value}")
            return True
            
        except TimeoutException:
            self.logger.warning(f"元素不可点击: {by}={value}")
            return False
        except Exception as e:
            self.logger.error(f"点击失败: {e}")
            return False
    
    def input_text(
        self, 
        by: By, 
        value: str, 
        text: str,
        clear_first: bool = True,
        timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        """
        输入文本
        
        Args:
            by: 定位方式
            value: 定位值
            text: 要输入的文本
            clear_first: 是否先清空
            timeout: 超时时间
        
        Returns:
            是否输入成功
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            
            if clear_first:
                element.clear()
            
            element.send_keys(text)
            self.logger.debug(f"输入文本到: {by}={value}")
            return True
            
        except TimeoutException:
            self.logger.warning(f"输入框未找到: {by}={value}")
            return False
        except Exception as e:
            self.logger.error(f"输入失败: {e}")
            return False
    
    def is_element_present(
        self, 
        by: By, 
        value: str, 
        timeout: int = 3
    ) -> bool:
        """检查元素是否存在"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False
    
    def is_element_visible(
        self, 
        by: By, 
        value: str, 
        timeout: int = 3
    ) -> bool:
        """检查元素是否可见"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False
    
    def wait_for_url_contains(
        self, 
        text: str, 
        timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        """等待URL包含指定文本"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.url_contains(text)
            )
            return True
        except TimeoutException:
            return False
    
    def get_current_url(self) -> str:
        """获取当前URL"""
        return self.driver.current_url
    
    def refresh(self):
        """刷新页面"""
        self.driver.refresh()
    
    def sleep(self, seconds: float):
        """等待指定秒数"""
        time.sleep(seconds)
    
    def execute_script(self, script: str, *args) -> any:
        """执行JavaScript"""
        return self.driver.execute_script(script, *args)
    
    def screenshot(self, filename: str):
        """截图"""
        self.driver.save_screenshot(filename)
        self.logger.debug(f"截图已保存: {filename}")
    
    def close_popups(self) -> int:
        """
        关闭所有弹窗
        
        Returns:
            关闭的弹窗数量
        """
        closed = 0
        
        # 1. 首先尝试点击遮罩层外部区域来关闭弹窗
        popup_containers = [
            ".app-pop-up.open",
            ".dialog-recharge-content",
            "[class*='popup'][class*='open']",
            "[class*='modal'][class*='open']",
            ".no-domain-dialog",
        ]
        
        # 尝试找到弹窗的关闭按钮或遮罩
        popup_close_selectors = [
            # 特定弹窗的关闭按钮
            ".app-pop-up .close-btn",
            ".app-pop-up [class*='close']",
            ".dialog-recharge-content .close",
            "[class*='popup'] .close-btn",
            "[class*='modal'] .close-btn",
            # 遮罩层（点击可能关闭弹窗）
            ".app-pop-up .mask",
            ".overlay",
            # 通用关闭按钮
            "[class*='dialog'] [class*='close']",
            ".close-icon",
            "button.close",
            # 确认/取消按钮（某些提示弹窗）
            "[class*='popup'] button[class*='confirm']",
            "[class*='popup'] button[class*='cancel']",
            ".app-pop-up button",
        ]
        
        for selector in popup_close_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    try:
                        if el.is_displayed():
                            # 使用 JavaScript 点击确保能点到
                            self.driver.execute_script("arguments[0].click();", el)
                            closed += 1
                            self.sleep(0.3)
                    except:
                        pass
            except:
                pass
        
        # 2. 尝试按ESC键关闭弹窗
        if closed == 0:
            try:
                from selenium.webdriver.common.keys import Keys
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                self.sleep(0.3)
            except:
                pass
        
        if closed > 0:
            self.logger.info(f"关闭了 {closed} 个弹窗")
        
        return closed
    
    def switch_to_iframe(self, iframe_selector: str = "iframe") -> bool:
        """
        切换到 iframe
        
        Args:
            iframe_selector: iframe 选择器
        
        Returns:
            是否切换成功
        """
        try:
            iframe = self.find_element(By.CSS_SELECTOR, iframe_selector, timeout=5)
            if iframe:
                self.driver.switch_to.frame(iframe)
                self.logger.info(f"切换到 iframe: {iframe_selector}")
                return True
        except Exception as e:
            self.logger.error(f"切换 iframe 失败: {e}")
        return False
    
    def switch_to_default(self):
        """切换回主文档"""
        try:
            self.driver.switch_to.default_content()
            self.logger.debug("切换回主文档")
        except:
            pass
    
    def click_nav_by_index(self, index: int, nav_selector: str = ".item") -> bool:
        """
        通过索引点击导航项
        
        Args:
            index: 导航项索引（从0开始）
            nav_selector: 导航项选择器
        
        Returns:
            是否点击成功
        """
        try:
            # 使用短超时快速获取元素
            items = self.driver.find_elements(By.CSS_SELECTOR, nav_selector)
            if items and len(items) > index:
                # 使用JS点击避免被遮挡
                self.driver.execute_script("arguments[0].click();", items[index])
                self.sleep(2)
                self.logger.debug(f"点击导航项 index={index}")
                return True
            self.logger.warning(f"导航项不存在: index={index}, 共{len(items)}项")
            return False
        except Exception as e:
            self.logger.error(f"点击导航失败: {e}")
            return False
    
    def click_nav_by_text(self, text: str, nav_selector: str = ".item") -> bool:
        """
        通过文字点击导航项
        
        Args:
            text: 目标文字（部分匹配）
            nav_selector: 导航项选择器
        
        Returns:
            是否点击成功
        """
        try:
            # 使用快速查找
            items = self.driver.find_elements(By.CSS_SELECTOR, nav_selector)
            for item in items:
                if text in item.text:
                    # 使用JS点击
                    self.driver.execute_script("arguments[0].click();", item)
                    self.sleep(2)
                    self.logger.debug(f"点击导航项: {text}")
                    return True
            
            # 备用：XPath + JS点击
            try:
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
                for el in elements:
                    if el.is_displayed():
                        self.driver.execute_script("arguments[0].click();", el)
                        self.sleep(2)
                        return True
            except:
                pass
            
            self.logger.warning(f"未找到导航项: {text}")
            return False
        except Exception as e:
            self.logger.error(f"点击导航失败: {e}")
            return False
    
    def click_element_by_text(self, text: str, container_selector: str = None) -> bool:
        """
        通过文字点击元素
        
        Args:
            text: 目标文字
            container_selector: 容器选择器（可选）
        
        Returns:
            是否点击成功
        """
        try:
            if container_selector:
                containers = self.find_elements(By.CSS_SELECTOR, container_selector)
                for container in containers:
                    if text in container.text:
                        container.click()
                        self.sleep(2)
                        return True
            
            # XPath方式
            if self.click(By.XPATH, f"//*[contains(text(), '{text}')]", timeout=3):
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"点击元素失败: {e}")
            return False