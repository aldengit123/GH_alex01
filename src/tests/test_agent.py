"""
代理中心功能测试用例
"""
import pytest
import time

from ..login.login_handler import LoginHandler
from ..pages.agent_page import AgentPage
from ..utils.logger import get_logger
from ..utils.config_loader import config


logger = get_logger("test_agent")


class TestAgent:
    """代理中心测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """测试前置：登录"""
        site_code = getattr(request, 'param', None) or config.get_current_site()
        config.set_current_site(site_code)
        
        logger.info(f"测试前置：登录站点 {site_code}...")
        
        self.handler = LoginHandler(session_name=f"agent_test_{site_code}")
        self.driver = self.handler.semi_auto_login()
        
        assert self.driver is not None, "登录失败"
        logger.info("登录成功，开始代理中心测试\n")
        
        self.selectors = config.get_page_selectors('agent')
        
        yield
        
        logger.info("测试完成")
    
    def test_navigate_to_agent(self):
        """测试导航到代理中心"""
        logger.info("测试：导航到代理中心")
        
        agent_page = AgentPage(self.driver, self.selectors)
        
        result = agent_page.navigate_to_agent()
        assert result, "导航到代理中心失败"
        
        is_agent = agent_page.is_agent_page()
        assert is_agent, "当前页面不是代理中心"
        
        logger.info("✅ 导航到代理中心成功")
    
    def test_agent_page_elements(self):
        """测试代理中心页面元素"""
        logger.info("测试：代理中心页面元素")
        
        agent_page = AgentPage(self.driver, self.selectors)
        
        results = agent_page.verify_agent_page()
        
        logger.info(f"验证结果: {results}")
        
        assert results["navigate"], "导航失败"
        assert results["page_loaded"], "页面加载失败"
        
        logger.info("✅ 代理中心页面元素验证通过")
    
    def test_get_agent_code(self):
        """测试获取代理邀请码"""
        logger.info("测试：获取代理邀请码")
        
        agent_page = AgentPage(self.driver, self.selectors)
        
        agent_page.navigate_to_agent()
        time.sleep(2)
        
        code = agent_page.get_agent_code()
        
        if code:
            logger.info(f"✅ 获取邀请码成功: {code}")
        else:
            logger.warning("未能获取邀请码")
    
    def test_get_agent_link(self):
        """测试获取推广链接"""
        logger.info("测试：获取推广链接")
        
        agent_page = AgentPage(self.driver, self.selectors)
        
        agent_page.navigate_to_agent()
        time.sleep(2)
        
        link = agent_page.get_agent_link()
        
        if link:
            logger.info(f"✅ 获取推广链接成功: {link}")
        else:
            logger.warning("未能获取推广链接")


def run_agent_test(site_code: str = None):
    """
    运行代理中心测试（非pytest方式）
    
    Args:
        site_code: 站点代号
    """
    if site_code:
        config.set_current_site(site_code)
    
    site = config.get_current_site()
    logger.info("=" * 60)
    logger.info(f"        代理中心测试 - 站点: {site}")
    logger.info("=" * 60)
    
    handler = LoginHandler(session_name=f"agent_{site}")
    
    try:
        driver = handler.semi_auto_login()
        
        if not driver:
            logger.error("登录失败，无法执行代理中心测试")
            return False
        
        logger.info("\n✅ 登录成功，开始代理中心测试...")
        
        selectors = config.get_page_selectors('agent')
        agent_page = AgentPage(driver, selectors)
        
        results = agent_page.verify_agent_page()
        
        logger.info("\n📋 测试结果:")
        for key, value in results.items():
            status = "✅" if value else "❌"
            logger.info(f"  {status} {key}: {value}")
        
        success = results["navigate"] and results["page_loaded"]
        
        if success:
            logger.info("\n✅ 代理中心测试通过！")
        else:
            logger.error("\n❌ 代理中心测试失败")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return False
    finally:
        handler.close()


if __name__ == "__main__":
    run_agent_test()
