"""
体育页面功能测试用例
"""
import pytest
import time

from ..login.login_handler import LoginHandler
from ..pages.sports_page import SportsPage
from ..utils.logger import get_logger
from ..utils.config_loader import config


logger = get_logger("test_sports")


class TestSports:
    """体育页面测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """测试前置：登录"""
        site_code = getattr(request, 'param', None) or config.get_current_site()
        config.set_current_site(site_code)
        
        logger.info(f"测试前置：登录站点 {site_code}...")
        
        self.handler = LoginHandler(session_name=f"sports_test_{site_code}")
        self.driver = self.handler.semi_auto_login()
        
        assert self.driver is not None, "登录失败"
        logger.info("登录成功，开始体育页面测试\n")
        
        self.selectors = config.get_page_selectors('sports')
        
        yield
        
        logger.info("测试完成")
    
    def test_navigate_to_sports(self):
        """测试导航到体育页面"""
        logger.info("测试：导航到体育页面")
        
        sports_page = SportsPage(self.driver, self.selectors)
        
        result = sports_page.navigate_to_sports()
        assert result, "导航到体育页面失败"
        
        is_sports = sports_page.is_sports_page()
        assert is_sports, "当前页面不是体育页面"
        
        logger.info("✅ 导航到体育页面成功")
    
    def test_match_list(self):
        """测试获取赛事列表"""
        logger.info("测试：获取赛事列表")
        
        sports_page = SportsPage(self.driver, self.selectors)
        
        sports_page.navigate_to_sports()
        time.sleep(3)
        
        matches = sports_page.get_match_list()
        
        logger.info(f"找到 {len(matches)} 场赛事")
        logger.info("✅ 赛事列表测试完成")
    
    def test_betting_flow_navigation(self):
        """测试下注流程 - 仅导航验证"""
        logger.info("测试：下注流程（仅导航）")
        
        sports_page = SportsPage(self.driver, self.selectors)
        
        results = sports_page.verify_sports_betting(stake="10", place=False)
        
        logger.info(f"验证结果: {results}")
        
        assert results["navigate"], "导航失败"
        assert results["page_loaded"], "页面加载失败"
        
        logger.info("✅ 体育下注流程导航验证通过")
    
    def test_select_match_and_odds(self):
        """测试选择赛事和赔率"""
        logger.info("测试：选择赛事和赔率")
        
        sports_page = SportsPage(self.driver, self.selectors)
        
        sports_page.navigate_to_sports()
        time.sleep(3)
        
        # 选择赛事
        match_result = sports_page.select_match(0)
        logger.info(f"选择赛事: {'成功' if match_result else '失败'}")
        
        # 选择赔率
        odds_result = sports_page.select_odds(0)
        logger.info(f"选择赔率: {'成功' if odds_result else '失败'}")
        
        logger.info("✅ 赛事和赔率选择测试完成")
    
    def test_check_balance(self):
        """测试获取余额"""
        logger.info("测试：获取余额")
        
        sports_page = SportsPage(self.driver, self.selectors)
        
        sports_page.navigate_to_sports()
        time.sleep(2)
        
        balance = sports_page.get_balance()
        
        if balance:
            logger.info(f"✅ 获取余额成功: {balance}")
        else:
            logger.warning("未能获取余额")


def run_sports_test(site_code: str = None, place_bet: bool = False):
    """
    运行体育页面测试（非pytest方式）
    
    Args:
        site_code: 站点代号
        place_bet: 是否实际下注（谨慎使用）
    """
    if site_code:
        config.set_current_site(site_code)
    
    site = config.get_current_site()
    logger.info("=" * 60)
    logger.info(f"        体育页面测试 - 站点: {site}")
    logger.info("=" * 60)
    
    handler = LoginHandler(session_name=f"sports_{site}")
    
    try:
        driver = handler.semi_auto_login()
        
        if not driver:
            logger.error("登录失败，无法执行体育页面测试")
            return False
        
        logger.info("\n✅ 登录成功，开始体育页面测试...")
        
        selectors = config.get_page_selectors('sports')
        sports_page = SportsPage(driver, selectors)
        
        results = sports_page.verify_sports_betting(stake="10", place=place_bet)
        
        logger.info("\n📋 测试结果:")
        for key, value in results.items():
            status = "✅" if value else "❌"
            logger.info(f"  {status} {key}: {value}")
        
        success = results["navigate"] and results["page_loaded"]
        
        if success:
            logger.info("\n✅ 体育页面测试通过！")
        else:
            logger.error("\n❌ 体育页面测试失败")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return False
    finally:
        handler.close()


if __name__ == "__main__":
    run_sports_test()
