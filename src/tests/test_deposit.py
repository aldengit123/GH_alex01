"""
存款功能测试用例
"""
import pytest
import time

from ..login.login_handler import LoginHandler
from ..pages.deposit_page import DepositPage
from ..utils.logger import get_logger
from ..utils.config_loader import config


logger = get_logger("test_deposit")


class TestDeposit:
    """存款功能测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """测试前置：登录"""
        # 获取站点参数
        site_code = getattr(request, 'param', None) or config.get_current_site()
        config.set_current_site(site_code)
        
        logger.info(f"测试前置：登录站点 {site_code}...")
        
        self.handler = LoginHandler(session_name=f"deposit_test_{site_code}")
        self.driver = self.handler.semi_auto_login()
        
        assert self.driver is not None, "登录失败"
        logger.info("登录成功，开始存款测试\n")
        
        # 获取选择器
        self.selectors = config.get_page_selectors('deposit')
        
        yield
        
        logger.info("测试完成")
    
    def test_navigate_to_deposit(self):
        """测试导航到存款页面"""
        logger.info("测试：导航到存款页面")
        
        deposit_page = DepositPage(self.driver, self.selectors)
        
        result = deposit_page.navigate_to_deposit()
        assert result, "导航到存款页面失败"
        
        is_deposit = deposit_page.is_deposit_page()
        assert is_deposit, "当前页面不是存款页面"
        
        logger.info("✅ 导航到存款页面成功")
    
    def test_deposit_flow_navigation_only(self):
        """测试存款流程 - 仅导航验证"""
        logger.info("测试：存款流程（仅导航）")
        
        deposit_page = DepositPage(self.driver, self.selectors)
        
        results = deposit_page.verify_deposit_flow(amount="100", submit=False)
        
        logger.info(f"验证结果: {results}")
        
        assert results["navigate"], "导航失败"
        assert results["page_loaded"], "页面加载失败"
        
        logger.info("✅ 存款流程导航验证通过")
    
    def test_select_payment_method(self):
        """测试选择支付方式"""
        logger.info("测试：选择支付方式")
        
        deposit_page = DepositPage(self.driver, self.selectors)
        
        # 先导航
        deposit_page.navigate_to_deposit()
        time.sleep(2)
        
        # 选择支付方式
        result = deposit_page.select_payment_method(0)
        
        logger.info(f"选择支付方式: {'成功' if result else '失败'}")
        logger.info("✅ 支付方式测试完成")
    
    def test_input_amount(self):
        """测试输入金额"""
        logger.info("测试：输入存款金额")
        
        deposit_page = DepositPage(self.driver, self.selectors)
        
        # 先导航
        deposit_page.navigate_to_deposit()
        time.sleep(2)
        
        # 输入金额
        result = deposit_page.input_amount("100")
        
        logger.info(f"输入金额: {'成功' if result else '失败'}")
        logger.info("✅ 输入金额测试完成")


def run_deposit_test(site_code: str = None, nav_only: bool = True):
    """
    运行存款测试（非pytest方式）
    
    Args:
        site_code: 站点代号
        nav_only: 是否仅验证导航
    """
    if site_code:
        config.set_current_site(site_code)
    
    site = config.get_current_site()
    logger.info("=" * 60)
    logger.info(f"        存款功能测试 - 站点: {site}")
    logger.info("=" * 60)
    
    handler = LoginHandler(session_name=f"deposit_{site}")
    
    try:
        driver = handler.semi_auto_login()
        
        if not driver:
            logger.error("登录失败，无法执行存款测试")
            return False
        
        logger.info("\n✅ 登录成功，开始存款测试...")
        
        # 获取选择器
        selectors = config.get_page_selectors('deposit')
        deposit_page = DepositPage(driver, selectors)
        
        # 执行测试
        results = deposit_page.verify_deposit_flow(amount="100", submit=False)
        
        logger.info("\n📋 测试结果:")
        for key, value in results.items():
            status = "✅" if value else "❌"
            logger.info(f"  {status} {key}: {value}")
        
        success = results["navigate"] and results["page_loaded"]
        
        if success:
            logger.info("\n✅ 存款测试通过！")
        else:
            logger.error("\n❌ 存款测试失败")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return False
    finally:
        handler.close()


if __name__ == "__main__":
    run_deposit_test()
