"""
页面工厂
根据当前站点自动创建页面对象并加载对应的选择器
"""
from typing import Optional, Dict, Type
from selenium import webdriver

from ..utils.config_loader import config
from ..utils.logger import get_logger
from ..pages.deposit_page import DepositPage
from ..pages.agent_page import AgentPage
from ..pages.sports_page import SportsPage
from ..pages.activity_page import ActivityPage

logger = get_logger("PageFactory")


class PageFactory:
    """
    页面工厂
    
    自动根据当前站点加载对应的选择器配置
    
    使用示例:
        factory = PageFactory(driver)
        deposit_page = factory.deposit_page()
        activity_page = factory.activity_page()
    """
    
    def __init__(self, driver: webdriver.Chrome, site_code: Optional[str] = None):
        """
        初始化页面工厂
        
        Args:
            driver: WebDriver实例
            site_code: 站点代号，为None时使用当前配置的站点
        """
        self.driver = driver
        self.site_code = site_code or config.get_current_site()
        self._selectors_cache: Optional[Dict] = None
        
        logger.info(f"PageFactory初始化，站点: {self.site_code}")
    
    @property
    def selectors(self) -> Dict:
        """获取当前站点的完整选择器配置（带缓存）"""
        if self._selectors_cache is None:
            self._selectors_cache = config.get_selectors(self.site_code)
        return self._selectors_cache
    
    def get_page_selectors(self, page_name: str) -> Dict:
        """
        获取指定页面的选择器
        
        Args:
            page_name: 页面名称 (deposit, agent, sports, activity, nav, common等)
        
        Returns:
            页面选择器字典
        """
        return self.selectors.get(page_name, {})
    
    def deposit_page(self) -> DepositPage:
        """创建存款页面对象"""
        selectors = self.get_page_selectors('deposit')
        return DepositPage(self.driver, selectors)
    
    def agent_page(self) -> AgentPage:
        """创建代理中心页面对象"""
        selectors = self.get_page_selectors('agent')
        return AgentPage(self.driver, selectors)
    
    def sports_page(self) -> SportsPage:
        """创建体育页面对象"""
        selectors = self.get_page_selectors('sports')
        return SportsPage(self.driver, selectors)
    
    def activity_page(self) -> ActivityPage:
        """创建活动页面对象"""
        selectors = self.get_page_selectors('activity')
        return ActivityPage(self.driver, selectors)
    
    def get_nav_selectors(self) -> Dict:
        """获取导航选择器"""
        return self.get_page_selectors('nav')
    
    def get_common_selectors(self) -> Dict:
        """获取通用选择器"""
        return self.get_page_selectors('common')
    
    def get_site_info(self) -> Dict:
        """获取站点信息"""
        return {
            "site_code": self.site_code,
            "site_config": config.get_site_config(self.site_code),
            "site_url": config.get_site_url(self.site_code),
        }


def create_page_factory(driver: webdriver.Chrome, site_code: Optional[str] = None) -> PageFactory:
    """
    创建页面工厂的便捷函数
    
    Args:
        driver: WebDriver实例
        site_code: 站点代号
    
    Returns:
        PageFactory实例
    """
    return PageFactory(driver, site_code)
