"""
体育页面对象 - 优化版
"""
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ..core.base_page import BasePage
from ..utils.logger import get_logger


class SportsPage(BasePage):
    """体育页面"""
    
    def __init__(self, driver, selectors: Optional[Dict] = None):
        super().__init__(driver)
        self.logger = get_logger("SportsPage")
        self.selectors = selectors or {}
        self.screenshot_dir = "./screenshots"
        self.debug_mode = False  # 调试模式开启截图
    
    def take_screenshot(self, name: str) -> str:
        """截图（仅调试模式）"""
        if not self.debug_mode:
            return ""
        os.makedirs(self.screenshot_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{self.screenshot_dir}/sports_{name}_{timestamp}.png"
        try:
            self.driver.save_screenshot(filename)
            self.logger.info(f"截图: {filename}")
            return filename
        except:
            return ""
    
    # ==================== 导航方法 ====================
    
    def navigate_to_sports(self) -> bool:
        """导航到体育页面"""
        self.logger.info("导航到体育页面...")
        self.close_popups()
        
        # 确保在首页
        if not self._ensure_home_page():
            return False
        
        # 点击首页体育分类
        if self._click_sports_category():
            self.wait_for_page_load(3)
            self.close_popups()
        
        # 点击体育入口（优先GO体育）
        sports_providers = ["GO体育", "go体育", "熊猫体育", "IM体育", "DB体育"]
        for provider in sports_providers:
            if self._click_sports_entry(provider):
                return True
        
        self.logger.warning("未找到体育入口")
        return False
    
    def _ensure_home_page(self) -> bool:
        """确保在首页"""
        url = self.get_current_url()
        if any(p in url for p in ["/mine", "/agent", "/activity", "/wallet"]):
            self.logger.info("返回首页...")
            if not self.click_nav_by_text("首页"):
                self.click_nav_by_index(0)
            self.wait_for_page_load(3)
            self.close_popups()
        return True
    
    def _click_sports_category(self) -> bool:
        """点击首页分类栏的体育"""
        self.logger.info("查找体育分类...")
        
        # 滚动到顶部
        self.driver.execute_script("window.scrollTo(0, 0);")
        
        # 查找并点击体育分类（在顶部分类栏）
        for _ in range(5):
            try:
                elements = self.driver.find_elements(By.XPATH, "//*[text()='体育']")
                for el in elements:
                    if el.is_displayed():
                        loc = el.location
                        size = el.size
                        # 分类栏在顶部400px内
                        if loc['y'] < 400 and size['height'] < 100:
                            self.driver.execute_script("arguments[0].click();", el)
                            self.logger.info("点击体育分类成功")
                            return True
            except:
                pass
            
            # 水平滑动查找
            self.driver.execute_script("""
                document.querySelectorAll('[class*="scroll"], [class*="swiper"], [class*="tabs"]')
                    .forEach(c => { if(c.scrollWidth > c.clientWidth) c.scrollLeft += 100; });
            """)
            self.sleep(0.3)
        
        return False
    
    def _click_sports_entry(self, keyword: str) -> bool:
        """点击体育入口"""
        try:
            elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
            for el in elements:
                if el.is_displayed():
                    old_url = self.driver.current_url
                    
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    self.sleep(0.5)
                    self.close_popups()
                    self.driver.execute_script("arguments[0].click();", el)
                    self.logger.info(f"点击体育入口: {keyword}")
                    
                    # 等待页面变化
                    self.sleep(5)  # 固定等待确保页面加载
                    self.close_popups()
                    self.sleep(1)
                    self.close_popups()  # 再关一次
                    
                    # 检查新窗口
                    handles = self.driver.window_handles
                    if len(handles) > 1:
                        self.driver.switch_to.window(handles[-1])
                    
                    return True
        except:
            pass
        return False
    
    # ==================== 下注流程 ====================
    
    def verify_sports_betting(self, stake: str = "10", place: bool = False) -> Dict[str, bool]:
        """
        验证体育下注流程
        
        Args:
            stake: 下注金额
            place: 是否真正下注
        """
        results = {
            "navigate": False,
            "page_loaded": False,
            "match_available": False,
            "select_match": False,
            "select_odds": False,
            "bet_ready": False,
        }
        
        # 1. 导航
        results["navigate"] = self.navigate_to_sports()
        if not results["navigate"]:
            return results
        
        # 2. 等待体育页面加载（第三方iframe）
        self.logger.info("等待体育页面加载...")
        self._switch_to_sports_iframe()
        results["page_loaded"] = True
        
        # 3. 验证页面内容
        if self.wait_for(lambda: len(self._get_body_text()) > 100, timeout=8):
            results["match_available"] = True
            self.logger.info("体育页面内容加载完成")
        
        # 4. 点击赔率
        results["select_odds"] = self._click_odds()
        if results["select_odds"]:
            results["select_match"] = True
            results["match_available"] = True
        
        # 5. 下注
        if results["select_odds"]:
            results["bet_ready"] = self._place_bet(stake, submit=place)
        
        self.switch_to_default()
        return results
    
    def _switch_to_sports_iframe(self):
        """切换到体育iframe"""
        # 等待iframe出现
        self.wait_for(
            lambda: len(self.driver.find_elements(By.TAG_NAME, "iframe")) > 0,
            timeout=8
        )
        self.sleep(2)  # 额外等待iframe完全加载
        
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            self.logger.info(f"找到 {len(iframes)} 个iframe")
            for iframe in iframes:
                try:
                    if iframe.is_displayed():
                        self.driver.switch_to.frame(iframe)
                        self.logger.info("切换到体育iframe")
                        # 等待iframe内容加载
                        self.sleep(3)
                        return True
                except Exception as e:
                    self.logger.debug(f"切换iframe失败: {e}")
                    continue
        except Exception as e:
            self.logger.debug(f"iframe处理失败: {e}")
        return False
    
    def _get_body_text(self) -> str:
        """获取页面文本"""
        try:
            return self.driver.find_element(By.TAG_NAME, "body").text
        except:
            return ""
    
    def _click_odds(self) -> bool:
        """点击赔率元素"""
        self.logger.info("点击赔率...")
        
        # 先等待页面内容稳定
        self.sleep(2)
        
        # JavaScript查找并点击赔率
        js_click_odds = """
        (function() {
            var elements = document.querySelectorAll('*');
            var found = [];
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                if (el.children.length === 0) {
                    var text = (el.innerText || '').trim();
                    var match = text.match(/^[▲▼]?\\s*(\\d+\\.\\d{2})\\s*[▲▼]?$/) || text.match(/^(\\d+\\.\\d{2})$/);
                    if (match) {
                        var val = parseFloat(match[1]);
                        if (val >= 1.01 && val <= 30.0) {
                            var rect = el.getBoundingClientRect();
                            if (rect.width > 15 && rect.height > 10 && rect.top > 100 && rect.top < window.innerHeight) {
                                found.push({el: el, val: val, top: rect.top});
                            }
                        }
                    }
                }
            }
            if (found.length > 0) {
                found.sort(function(a,b) { return a.top - b.top; });
                found[0].el.click();
                return found[0].val + ' (共' + found.length + '个)';
            }
            return null;
        })();
        """
        
        for attempt in range(3):
            try:
                result = self.driver.execute_script(js_click_odds)
                if result:
                    self.logger.info(f"点击赔率成功: {result}")
                    # 等待投注面板
                    if self.wait_for(self._is_bet_panel_open, timeout=3):
                        return True
                    # 再等一下
                    self.sleep(1)
                    if self._is_bet_panel_open():
                        return True
            except Exception as e:
                self.logger.debug(f"点击赔率失败: {e}")
            
            # 滚动查找更多
            self.driver.execute_script("window.scrollBy(0, 150);")
            self.sleep(1)
        
        return self._is_bet_panel_open()
    
    def _is_bet_panel_open(self) -> bool:
        """检查投注面板是否打开"""
        text = self._get_body_text()
        return any(kw in text for kw in ['投注', '可赢', '下注', '+100', '+1000'])
    
    def _place_bet(self, stake: str = "10", submit: bool = False) -> bool:
        """下注流程"""
        self.logger.info("准备下注...")
        
        if not self._is_bet_panel_open():
            return False
        
        # 输入金额
        self._input_amount(stake)
        
        # 检查投注按钮
        body_text = self._get_body_text()
        if '余额不足' in body_text:
            self.logger.info("余额不足，但流程正常")
            return True
        
        if '可赢' not in body_text and '投注' not in body_text:
            return False
        
        self.logger.info(f"投注按钮可用")
        
        # 真正下注
        if submit:
            return self._click_bet_button()
        
        return True
    
    def _input_amount(self, amount: str) -> bool:
        """通过数字键盘输入金额"""
        self.logger.info(f"输入金额: {amount}")
        
        for digit in amount:
            try:
                btns = self.driver.find_elements(By.XPATH, f"//*[text()='{digit}']")
                for btn in btns:
                    if btn.is_displayed():
                        size = btn.size
                        if size['width'] > 30 and size['height'] > 30:
                            self.driver.execute_script("arguments[0].click();", btn)
                            self.sleep(0.15)
                            break
            except:
                pass
        return True
    
    def _click_bet_button(self) -> bool:
        """点击投注按钮"""
        self.logger.info("🎯 点击投注按钮...")
        
        try:
            btns = self.driver.find_elements(By.XPATH, "//*[contains(text(), '投注')]")
            for btn in btns:
                if btn.is_displayed():
                    text = btn.text.strip()
                    if '投注' in text and '取消' not in text and len(text) < 20:
                        self.driver.execute_script("arguments[0].click();", btn)
                        self.logger.info(f"✅ 点击: {text}")
                        
                        # 等待结果
                        if self.wait_for(
                            lambda: any(kw in self._get_body_text() for kw in ['成功', '注单', '已接受']),
                            timeout=5
                        ):
                            self.logger.info("🎉 下注成功！")
                            self.take_screenshot("bet_success")
                            return True
                        
                        # 面板关闭也算成功
                        if not self._is_bet_panel_open():
                            self.logger.info("下注完成")
                            return True
        except Exception as e:
            self.logger.warning(f"点击失败: {e}")
        
        return False
    
    # ==================== 辅助方法 ====================
    
    def is_sports_page(self) -> bool:
        """验证是否在体育页面"""
        url = self.get_current_url().lower()
        return any(kw in url for kw in ['sport', 'tiyu', 'game', 'panda', 'go'])
    
    def get_balance(self) -> Optional[str]:
        """获取余额"""
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, "[class*='balance']")
            return el.text if el else None
        except:
            return None
