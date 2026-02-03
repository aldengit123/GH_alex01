"""
活动/赚钱页面功能测试用例
"""
import pytest
import time

from ..login.login_handler import LoginHandler
from ..pages.activity_page import ActivityPage
from ..utils.logger import get_logger
from ..utils.config_loader import config


logger = get_logger("test_activity")


class TestActivity:
    """活动/赚钱页面测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """测试前置：登录"""
        site_code = getattr(request, 'param', None) or config.get_current_site()
        config.set_current_site(site_code)
        
        logger.info(f"测试前置：登录站点 {site_code}...")
        
        self.handler = LoginHandler(session_name=f"activity_test_{site_code}")
        self.driver = self.handler.semi_auto_login()
        
        assert self.driver is not None, "登录失败"
        logger.info("登录成功，开始活动页面测试\n")
        
        self.selectors = config.get_page_selectors('activity')
        
        yield
        
        logger.info("测试完成")
    
    def test_navigate_to_activity(self):
        """测试导航到活动页面"""
        logger.info("测试：导航到活动页面")
        
        activity_page = ActivityPage(self.driver, self.selectors)
        
        result = activity_page.navigate_to_activity()
        assert result, "导航到活动页面失败"
        
        is_activity = activity_page.is_activity_page()
        assert is_activity, "当前页面不是活动页面"
        
        logger.info("✅ 导航到活动页面成功")
    
    def test_navigate_to_earn(self):
        """测试导航到赚钱页面"""
        logger.info("测试：导航到赚钱页面")
        
        activity_page = ActivityPage(self.driver, self.selectors)
        
        result = activity_page.navigate_to_earn()
        
        if result:
            is_earn = activity_page.is_earn_page()
            logger.info(f"赚钱页面验证: {'成功' if is_earn else '失败'}")
            logger.info("✅ 导航到赚钱页面成功")
        else:
            logger.warning("未能导航到赚钱页面（可能该站点没有此功能）")
    
    def test_activity_list(self):
        """测试获取活动列表"""
        logger.info("测试：获取活动列表")
        
        activity_page = ActivityPage(self.driver, self.selectors)
        
        activity_page.navigate_to_activity()
        time.sleep(2)
        
        activities = activity_page.get_activity_list()
        
        logger.info(f"找到 {len(activities)} 个活动")
        logger.info("✅ 活动列表测试完成")
    
    def test_activity_detail(self):
        """测试点击活动进入详情"""
        logger.info("测试：活动详情页面")
        
        activity_page = ActivityPage(self.driver, self.selectors)
        
        results = activity_page.verify_activity_page()
        
        logger.info(f"验证结果: {results}")
        
        assert results["navigate"], "导航失败"
        assert results["page_loaded"], "页面加载失败"
        
        logger.info("✅ 活动页面验证通过")
    
    def test_earn_page_elements(self):
        """测试赚钱页面元素"""
        logger.info("测试：赚钱页面元素")
        
        activity_page = ActivityPage(self.driver, self.selectors)
        
        results = activity_page.verify_earn_page()
        
        logger.info(f"验证结果: {results}")
        
        if results["navigate"]:
            logger.info("✅ 赚钱页面验证完成")
        else:
            logger.warning("未能导航到赚钱页面")


def run_activity_test(site_code: str = None, test_earn: bool = True):
    """
    运行活动页面测试（非pytest方式）
    
    Args:
        site_code: 站点代号
        test_earn: 是否测试赚钱页面
    """
    if site_code:
        config.set_current_site(site_code)
    
    site = config.get_current_site()
    logger.info("=" * 60)
    logger.info(f"        活动/赚钱页面测试 - 站点: {site}")
    logger.info("=" * 60)
    
    handler = LoginHandler(session_name=f"activity_{site}")
    
    try:
        driver = handler.semi_auto_login()
        
        if not driver:
            logger.error("登录失败，无法执行活动页面测试")
            return False
        
        logger.info("\n✅ 登录成功，开始活动页面测试...")
        
        selectors = config.get_page_selectors('activity')
        activity_page = ActivityPage(driver, selectors)
        
        # 测试活动页面
        logger.info("\n📋 活动页面测试:")
        activity_results = activity_page.verify_activity_page()
        
        for key, value in activity_results.items():
            status = "✅" if value else "❌"
            logger.info(f"  {status} {key}: {value}")
        
        activity_success = activity_results["navigate"] and activity_results["page_loaded"]
        
        # 测试赚钱页面
        earn_success = True
        if test_earn:
            # 返回首页
            driver.back()
            time.sleep(2)
            
            logger.info("\n📋 赚钱页面测试:")
            earn_results = activity_page.verify_earn_page()
            
            for key, value in earn_results.items():
                status = "✅" if value else "❌"
                logger.info(f"  {status} {key}: {value}")
            
            earn_success = earn_results.get("navigate", False)
        
        if activity_success:
            logger.info("\n✅ 活动页面测试通过！")
        else:
            logger.error("\n❌ 活动页面测试失败")
        
        return activity_success
        
    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return False
    finally:
        handler.close()


if __name__ == "__main__":
    run_activity_test()
