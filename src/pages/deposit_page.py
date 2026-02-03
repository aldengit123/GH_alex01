"""
存款页面对象 - 修复版
"""
from typing import Optional, Dict, Any
from selenium.webdriver.common.by import By

from ..core.base_page import BasePage
from ..utils.logger import get_logger


class DepositPage(BasePage):
    """存款页面"""
    
    def __init__(self, driver, selectors: Optional[Dict] = None):
        super().__init__(driver)
        self.logger = get_logger("DepositPage")
        self.selectors = selectors or {}
    
    # ==================== 导航 ====================
    
    def navigate_to_deposit(self) -> bool:
        """导航到存款页面"""
        self.logger.info("导航到存款页面...")
        self.close_popups()
        
        # 方式1: 顶部存款按钮
        try:
            btns = self.driver.find_elements(By.CSS_SELECTOR, ".recharge-btn, .recharge-btn-wrapper, [class*='recharge']")
            for btn in btns:
                if btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", btn)
                    self.logger.info("点击顶部存款按钮")
                    # 等待页面跳转
                    self.sleep(3)
                    if self._is_deposit_url():
                        return True
        except:
            pass
        
        # 方式2: 底部导航
        if self.click_nav_by_index(3) or self.click_nav_by_text("存款"):
            self.sleep(3)
            return True
        
        self.logger.warning("未找到存款入口")
        return False
    
    def _is_deposit_url(self) -> bool:
        """检查URL是否为存款页面"""
        url = self.get_current_url().lower()
        return any(kw in url for kw in ["walletcounter", "recharge", "deposit", "counter", "wallet"])
    
    def is_deposit_page(self) -> bool:
        """验证是否在存款页面"""
        if self._is_deposit_url():
            self.logger.info("URL验证存款页面")
            return True
        
        # 检查页面头部
        try:
            header = self.find_element(By.CSS_SELECTOR, ".navigation-header", timeout=2)
            if header and "存款" in header.text:
                self.logger.info("页面头部验证存款页面")
                return True
        except:
            pass
        
        # 检查iframe存在（存款页面特征）
        try:
            iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe.payment-iframe")
            if iframes:
                self.logger.info("检测到支付iframe")
                return True
        except:
            pass
        
        return False
    
    # ==================== 存款流程 ====================
    
    def switch_to_payment_iframe(self) -> bool:
        """切换到支付iframe"""
        self.logger.info("尝试切换到支付iframe...")
        
        # 等待iframe加载
        self.sleep(2)
        
        try:
            # 优先使用 payment-iframe 类
            iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe.payment-iframe")
            if iframes:
                for iframe in iframes:
                    if iframe.is_displayed():
                        self.driver.switch_to.frame(iframe)
                        self.logger.info("切换到 payment-iframe")
                        self.sleep(2)
                        return True
            
            # 备用：所有iframe
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            self.logger.info(f"找到 {len(iframes)} 个iframe")
            for iframe in iframes:
                if iframe.is_displayed():
                    self.driver.switch_to.frame(iframe)
                    self.logger.info("切换到iframe")
                    self.sleep(2)
                    return True
                    
        except Exception as e:
            self.logger.warning(f"iframe切换失败: {e}")
        
        return False
    
    def select_payment_method(self, index: int = 0) -> bool:
        """选择支付方式"""
        self.logger.info(f"选择支付方式 #{index}")
        
        selectors = [
            "[class*='payment-item']",
            "[class*='pay-item']",
            "[class*='channel-item']",
            "[class*='payment']",
            "[class*='channel']",
            "[class*='method']",
            "label[class*='radio']",
            "[role='radio']",
        ]
        
        for selector in selectors:
            try:
                methods = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if methods and len(methods) > index:
                    self.driver.execute_script("arguments[0].click();", methods[index])
                    self.logger.info(f"支付方式选择成功: {selector}")
                    self.sleep(1)
                    return True
            except:
                continue
        
        self.logger.warning("未找到支付方式")
        return False
    
    def input_amount(self, amount: str) -> bool:
        """输入存款金额"""
        self.logger.info(f"输入金额: {amount}")
        
        selectors = [
            "input[type='number']",
            "input[type='text'][class*='amount']",
            "input[placeholder*='金额']",
            "input[placeholder*='amount']",
            "input[class*='amount']",
            "input[class*='money']",
            "input"
        ]
        
        for selector in selectors:
            try:
                inputs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for inp in inputs:
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys(amount)
                        self.logger.info(f"金额输入成功: {selector}")
                        return True
            except:
                continue
        
        # 尝试快捷金额按钮
        try:
            btns = self.driver.find_elements(By.CSS_SELECTOR, "[class*='quick'], [class*='preset'], [class*='fast']")
            for btn in btns:
                if btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", btn)
                    self.logger.info("点击快捷金额")
                    return True
        except:
            pass
        
        return False
    
    def click_submit_button(self) -> bool:
        """点击提交按钮"""
        self.logger.info("点击提交按钮...")
        
        selectors = [
            "button[class*='submit']",
            "button[class*='confirm']",
            "button[type='submit']",
            "[class*='submit-btn']",
            "[class*='pay-btn']",
            "button"
        ]
        
        for selector in selectors:
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in btns:
                    if btn.is_displayed():
                        text = btn.text.strip()
                        # 避免点击取消按钮
                        if text and '取消' not in text:
                            self.driver.execute_script("arguments[0].click();", btn)
                            self.logger.info(f"提交按钮点击成功: {text or selector}")
                            self.sleep(2)
                            return True
            except:
                continue
        
        return False
    
    def is_submit_button_present(self) -> bool:
        """检查提交按钮是否存在"""
        selectors = ["button[class*='submit']", "button[class*='confirm']", "button[type='submit']", "button"]
        for selector in selectors:
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if any(btn.is_displayed() for btn in btns):
                    self.logger.info("提交按钮存在")
                    return True
            except:
                pass
        return False
    
    # ==================== 验证流程 ====================
    
    def verify_deposit_flow(self, amount: str = "100", submit: bool = False) -> Dict[str, bool]:
        """验证完整存款流程"""
        results = {
            "navigate": False,
            "page_loaded": False,
            "iframe_switched": False,
            "select_payment": False,
            "input_amount": False,
            "submit_clicked": False,
        }
        
        try:
            # 1. 导航
            results["navigate"] = self.navigate_to_deposit()
            if not results["navigate"]:
                return results
            
            # 2. 页面验证
            results["page_loaded"] = self.is_deposit_page()
            if not results["page_loaded"]:
                return results
            
            # 3. 切换到iframe
            results["iframe_switched"] = self.switch_to_payment_iframe()
            
            # 4. 选择支付方式
            results["select_payment"] = self.select_payment_method()
            
            # 5. 输入金额
            results["input_amount"] = self.input_amount(amount)
            
            # 6. 提交
            if submit:
                results["submit_clicked"] = self.click_submit_button()
            else:
                results["submit_clicked"] = self.is_submit_button_present()
            
        finally:
            self.switch_to_default()
        
        return results
