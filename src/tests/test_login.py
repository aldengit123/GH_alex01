"""
登录测试用例
演示如何使用LoginHandler进行半自动化登录
"""
import pytest
import time

from ..login.login_handler import LoginHandler
from ..utils.logger import get_logger


logger = get_logger("test_login")


class TestLogin:
    """登录测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前置"""
        self.handler = None
        yield
        # 测试后不自动关闭浏览器，方便调试
    
    def test_semi_auto_login(self):
        """测试半自动登录"""
        logger.info("开始测试：半自动登录")
        
        # 创建登录处理器
        self.handler = LoginHandler(
            username="honer001",
            password="Aa123456",
            session_name="test_user"
        )
        
        # 执行半自动登录
        driver = self.handler.semi_auto_login()
        
        # 验证登录成功
        assert driver is not None, "登录失败，driver为None"
        
        current_url = driver.current_url
        logger.info(f"当前URL: {current_url}")
        
        assert "lobby" in current_url or "home" in current_url, \
            f"未跳转到登录成功页面: {current_url}"
        
        logger.info("✅ 登录测试通过")
        
        # 保持浏览器打开一段时间
        logger.info("浏览器将保持打开30秒...")
        time.sleep(30)
    
    def test_cached_login(self):
        """测试缓存登录（需要先执行一次完整登录）"""
        logger.info("开始测试：缓存登录")
        
        # 创建登录处理器（使用相同的session_name）
        self.handler = LoginHandler(
            username="honer001",
            password="Aa123456",
            session_name="test_user"
        )
        
        # 执行登录（应该使用缓存）
        driver = self.handler.semi_auto_login()
        
        assert driver is not None, "缓存登录失败"
        
        logger.info("✅ 缓存登录测试通过")
        
        # 保持浏览器打开
        time.sleep(10)


def run_quick_test():
    """快速测试（非pytest方式）"""
    logger.info("="*60)
    logger.info("        快速登录测试")
    logger.info("="*60)
    
    handler = LoginHandler(
        session_name="quick_test"
    )
    
    try:
        driver = handler.semi_auto_login()
        
        if driver:
            logger.info("\n✅ 登录成功！")
            logger.info(f"当前URL: {driver.current_url}")
            
            # 保持浏览器打开
            logger.info("\n浏览器将保持打开60秒，您可以继续操作...")
            time.sleep(60)
        else:
            logger.error("\n❌ 登录失败")
            
    except KeyboardInterrupt:
        logger.info("\n用户中断")
    finally:
        handler.close()


if __name__ == "__main__":
    run_quick_test()
