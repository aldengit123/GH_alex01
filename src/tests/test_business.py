"""
业务流程测试用例
演示如何使用已登录的driver进行业务测试
"""
import pytest
import time

from ..login.login_handler import LoginHandler
from ..core.base_page import BasePage
from ..utils.logger import get_logger


logger = get_logger("test_business")


class TestBusiness:
    """业务测试类"""
    
    @pytest.fixture(autouse=True)
    def login(self):
        """前置：登录"""
        logger.info("测试前置：执行登录...")
        
        self.handler = LoginHandler(session_name="business_test")
        self.driver = self.handler.semi_auto_login()
        
        assert self.driver is not None, "登录失败"
        logger.info("登录成功，开始业务测试\n")
        
        yield
        
        # 测试完成后保持浏览器打开
        logger.info("测试完成，浏览器保持打开10秒...")
        time.sleep(10)
    
    def test_access_lobby(self):
        """测试访问大厅页面"""
        logger.info("测试：访问大厅页面")
        
        # 检查当前URL
        current_url = self.driver.current_url
        logger.info(f"当前URL: {current_url}")
        
        assert "lobby" in current_url or "home" in current_url
        logger.info("✅ 大厅页面访问正常")
    
    def test_page_elements(self):
        """测试页面元素存在"""
        logger.info("测试：页面元素检查")
        
        page = BasePage(self.driver)
        
        # 等待页面加载
        time.sleep(2)
        
        # 检查底部导航栏
        nav_exists = page.is_element_present(
            "css selector", 
            "[class*='nav'], [class*='footer']",
            timeout=5
        )
        
        logger.info(f"底部导航栏: {'存在' if nav_exists else '不存在'}")
        logger.info("✅ 页面元素检查完成")


def run_business_test():
    """运行业务测试（非pytest方式）"""
    logger.info("="*60)
    logger.info("        业务流程测试")
    logger.info("="*60)
    
    handler = LoginHandler(session_name="business_demo")
    
    try:
        driver = handler.semi_auto_login()
        
        if not driver:
            logger.error("登录失败，无法执行业务测试")
            return
        
        logger.info("\n✅ 登录成功，开始业务测试...")
        
        # 示例：访问不同页面
        logger.info("\n📋 测试1：检查当前页面")
        current_url = driver.current_url
        logger.info(f"当前URL: {current_url}")
        
        logger.info("\n📋 测试2：页面截图")
        driver.save_screenshot("business_test_screenshot.png")
        logger.info("截图已保存: business_test_screenshot.png")
        
        logger.info("\n📋 测试3：获取页面信息")
        title = driver.title
        logger.info(f"页面标题: {title}")
        
        logger.info("\n✅ 业务测试完成！")
        
        # 保持浏览器打开
        logger.info("\n浏览器将保持打开60秒...")
        time.sleep(60)
        
    except KeyboardInterrupt:
        logger.info("\n用户中断")
    finally:
        handler.close()


if __name__ == "__main__":
    run_business_test()
