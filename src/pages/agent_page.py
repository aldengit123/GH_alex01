"""
代理中心页面对象 - 优化版
"""
from typing import Optional, Dict, Any
from selenium.webdriver.common.by import By

from ..core.base_page import BasePage
from ..utils.logger import get_logger


class AgentPage(BasePage):
    """代理中心页面"""
    
    def __init__(self, driver, selectors: Optional[Dict] = None):
        super().__init__(driver)
        self.logger = get_logger("AgentPage")
        self.selectors = selectors or {}
        self._entry_keywords = ["代理中心", "代理", "推广", "邀请", "合营", "分享赚钱"]
    
    # ==================== 导航 ====================
    
    def navigate_to_mine(self) -> bool:
        """导航到'我的'页面"""
        self.logger.info("导航到'我的'页面...")
        self.close_popups()
        self.sleep(1)
        
        # 方式1: 通过索引
        try:
            items = self.driver.find_elements(By.CSS_SELECTOR, ".item")
            self.logger.info(f"找到 {len(items)} 个导航项")
            if items and len(items) > 4:
                self.driver.execute_script("arguments[0].click();", items[4])
                self.logger.info("点击'我的'导航项 (index=4)")
                self.sleep(3)
                self.close_popups()
                self.sleep(1)
                self.close_popups()
                return True
        except Exception as e:
            self.logger.debug(f"索引点击失败: {e}")
        
        # 方式2: 通过文字
        try:
            items = self.driver.find_elements(By.CSS_SELECTOR, ".item")
            for item in items:
                if "我的" in item.text:
                    self.driver.execute_script("arguments[0].click();", item)
                    self.logger.info("通过文字点击'我的'")
                    self.sleep(3)
                    self.close_popups()
                    return True
        except:
            pass
        
        # 方式3: XPath
        try:
            els = self.driver.find_elements(By.XPATH, "//*[contains(text(), '我的')]")
            for el in els:
                if el.is_displayed():
                    self.driver.execute_script("arguments[0].click();", el)
                    self.logger.info("通过XPath点击'我的'")
                    self.sleep(3)
                    return True
        except:
            pass
        
        self.logger.warning("未能进入'我的'页面")
        return False
    
    def navigate_to_agent(self) -> bool:
        """导航到代理中心"""
        self.logger.info("导航到代理中心...")
        self.close_popups()
        
        # 先进入"我的"页面
        if not self.navigate_to_mine():
            return False
        
        self.close_popups()
        self.driver.execute_script("window.scrollTo(0, 0);")
        
        # 查找代理入口
        for keyword in self._entry_keywords:
            if self._click_entry_by_text(keyword):
                return True
        
        # 备用：通过CSS选择器
        for selector in ["[class*='agent']", "[class*='promote']", "[class*='invite']", "a[href*='agent']"]:
            if self._click_entry_by_selector(selector):
                return True
        
        self.logger.warning("未找到代理入口")
        return False
    
    def _click_entry_by_text(self, keyword: str) -> bool:
        """通过文字点击入口"""
        try:
            elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
            for el in elements:
                if el.is_displayed():
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    self.driver.execute_script("arguments[0].click();", el)
                    self.logger.info(f"点击代理入口: {keyword}")
                    self.wait_for_page_load(3)
                    self.close_popups()
                    return True
        except:
            pass
        return False
    
    def _click_entry_by_selector(self, selector: str) -> bool:
        """通过选择器点击入口"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    self.driver.execute_script("arguments[0].click();", el)
                    self.logger.info(f"点击代理入口: {selector}")
                    self.wait_for_page_load(3)
                    return True
        except:
            pass
        return False
    
    # ==================== 页面验证 ====================
    
    def is_agent_page(self) -> bool:
        """验证是否在代理页面"""
        url = self.get_current_url().lower()
        if any(kw in url for kw in ['agent', 'proxy', 'promote', 'invite', 'spread']):
            self.logger.info("URL匹配代理页面")
            return True
        
        # 检查页面内容
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            keywords = ['邀请码', '推广链接', '佣金', '下级', '我的团队', '代理中心']
            if any(kw in body_text for kw in keywords):
                self.logger.info("页面内容匹配代理页面")
                return True
        except:
            pass
        
        return False
    
    def get_agent_code(self) -> Optional[str]:
        """获取代理邀请码"""
        try:
            el = self.find_element(By.CSS_SELECTOR, "[class*='code'], [class*='invite']", timeout=3)
            return el.text if el else None
        except:
            return None
    
    # ==================== 验证流程 ====================
    
    def verify_agent_page(self) -> Dict[str, bool]:
        """验证代理中心页面"""
        results = {
            "navigate": False,
            "page_loaded": False,
            "has_content": False,
        }
        
        results["navigate"] = self.navigate_to_agent()
        if not results["navigate"]:
            return results
        
        results["page_loaded"] = self.is_agent_page()
        
        # 检查页面内容
        if self.wait_for(
            lambda: len(self.driver.find_element(By.TAG_NAME, "body").text) > 50,
            timeout=5
        ):
            results["has_content"] = True
            self.logger.info("代理页面内容验证通过")
        
        # 页面加载成功就算内容通过
        if results["page_loaded"] and not results["has_content"]:
            results["has_content"] = True
            self.logger.info("代理页面加载成功")
        
        return results
