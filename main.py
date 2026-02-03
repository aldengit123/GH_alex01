#!/usr/bin/env python3
"""
UI自动化测试框架 - 主入口
支持多站点、多测试模块的自动化测试
"""
import sys
import time
import argparse

from src.login.login_handler import LoginHandler
from src.utils.logger import get_logger
from src.utils.config_loader import config
from src.utils.constants import SiteCode


logger = get_logger("main")


# 可用的测试模块
AVAILABLE_TESTS = {
    "deposit": "存款功能测试",
    "agent": "代理中心测试",
    "sports": "体育下注测试",
    "activity": "活动页面测试",
    "all": "运行所有测试",
}


def run_tests(driver, tests: list, nav_only: bool = True) -> dict:
    """
    运行指定的测试模块
    
    Args:
        driver: WebDriver实例
        tests: 测试模块列表
        nav_only: 是否仅验证导航
    
    Returns:
        测试结果字典
    """
    from src.core.page_factory import PageFactory
    
    results = {}
    
    # 创建页面工厂（自动加载当前站点的选择器）
    factory = PageFactory(driver)
    site_info = factory.get_site_info()
    logger.info(f"当前站点: {site_info['site_code']} - {site_info['site_config'].get('name', '')}")
    
    if "all" in tests:
        tests = ["deposit", "agent", "sports", "activity"]
    
    for test_name in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"运行测试: {AVAILABLE_TESTS.get(test_name, test_name)}")
        logger.info("="*50)
        
        try:
            if test_name == "deposit":
                page = factory.deposit_page()
                results["deposit"] = page.verify_deposit_flow(submit=not nav_only)
                
            elif test_name == "agent":
                page = factory.agent_page()
                results["agent"] = page.verify_agent_page()
                
            elif test_name == "sports":
                page = factory.sports_page()
                results["sports"] = page.verify_sports_betting(place=not nav_only)
                
            elif test_name == "activity":
                page = factory.activity_page()
                results["activity"] = page.verify_activity_page()
            
            # 返回首页准备下一个测试
            try:
                # 先关闭可能的弹窗
                from src.core.base_page import BasePage
                base_page = BasePage(driver)
                base_page.close_popups()
                time.sleep(0.5)
                
                # 切换回主文档（可能在 iframe 中）
                try:
                    driver.switch_to.default_content()
                except:
                    pass
                
                # 直接导航到首页URL（最可靠的方式）
                site_url = config.get_site_url()
                logger.info(f"返回首页: {site_url}")
                driver.get(site_url)
                time.sleep(3)
                
                # 关闭可能的弹窗
                base_page.close_popups()
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"返回首页失败: {e}")
                # 最后备用：直接导航
                try:
                    driver.get(config.get_site_url())
                    time.sleep(3)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"测试 {test_name} 出错: {e}")
            results[test_name] = {"error": str(e)}
    
    return results


def print_results(results: dict):
    """打印测试结果"""
    logger.info("\n" + "="*60)
    logger.info("                    测试结果汇总")
    logger.info("="*60)
    
    total_pass = 0
    total_fail = 0
    
    for test_name, test_results in results.items():
        logger.info(f"\n📋 {AVAILABLE_TESTS.get(test_name, test_name)}:")
        
        if isinstance(test_results, dict):
            if "error" in test_results:
                logger.error(f"  ❌ 错误: {test_results['error']}")
                total_fail += 1
            else:
                for key, value in test_results.items():
                    status = "✅" if value else "❌"
                    logger.info(f"  {status} {key}: {value}")
                    if value:
                        total_pass += 1
                    else:
                        total_fail += 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"总计: ✅ 通过 {total_pass} 项, ❌ 失败 {total_fail} 项")
    logger.info("="*60)


def list_sites():
    """列出可用站点"""
    print("\n可用站点:")
    print("-" * 40)
    for code, site_config in config.get_all_sites().items():
        name = site_config.get('name', code)
        url = site_config.get('base_url', '')
        current = " (当前)" if code == config.current_site else ""
        print(f"  {code}: {name} - {url}{current}")
    print()


def list_tests():
    """列出可用测试"""
    print("\n可用测试模块:")
    print("-" * 40)
    for test_id, desc in AVAILABLE_TESTS.items():
        print(f"  {test_id}: {desc}")
    print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="UI自动化测试框架 - 支持多站点多模块测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --site 286 --test deposit
  python main.py --site 231 --test deposit,agent
  python main.py --site 1PG --test all
  python main.py --list-sites
  python main.py --list-tests
        """
    )
    
    parser.add_argument(
        "--site", "-s",
        type=str,
        help=f"站点代号 ({', '.join(SiteCode.ALL_SITES)})"
    )
    parser.add_argument(
        "--test", "-t",
        type=str,
        help="测试模块，多个用逗号分隔 (deposit,agent,sports,activity,all)"
    )
    parser.add_argument(
        "--nav-only",
        action="store_true",
        default=True,
        help="仅验证导航，不执行实际操作 (默认)"
    )
    parser.add_argument(
        "--full-test",
        action="store_true",
        help="完整测试，包括实际操作"
    )
    parser.add_argument(
        "--clear-cache", 
        action="store_true", 
        help="清除缓存，强制重新登录"
    )
    parser.add_argument(
        "--session", 
        type=str, 
        default=None,
        help="会话名称（用于多账号管理）"
    )
    parser.add_argument(
        "--keep-open",
        type=int,
        default=30,
        help="测试完成后保持浏览器打开的秒数"
    )
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="列出所有可用站点"
    )
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="列出所有可用测试模块"
    )
    
    args = parser.parse_args()
    
    # 处理列表命令
    if args.list_sites:
        list_sites()
        return 0
    
    if args.list_tests:
        list_tests()
        return 0
    
    # 设置站点
    if args.site:
        try:
            config.set_current_site(args.site)
        except ValueError as e:
            logger.error(str(e))
            list_sites()
            return 1
    
    site_code = config.get_current_site()
    site_config = config.get_site_config()
    site_name = site_config.get('name', site_code)
    site_url = site_config.get('base_url', '')
    
    print("\n" + "="*60)
    print("        🚀 H5自动化测试框架")
    print("="*60)
    print(f"  站点: {site_name} ({site_code})")
    print(f"  URL: {site_url}")
    
    # 确定测试模块
    tests = []
    if args.test:
        tests = [t.strip() for t in args.test.split(",")]
        print(f"  测试: {', '.join(tests)}")
    
    nav_only = not args.full_test
    print(f"  模式: {'仅导航验证' if nav_only else '完整测试'}")
    print("="*60 + "\n")
    
    # 会话名称
    session_name = args.session or f"{site_code}_test"
    
    # 创建登录处理器
    handler = LoginHandler(session_name=session_name)
    
    # 是否清除缓存
    if args.clear_cache:
        logger.info("清除缓存...")
        handler.clear_cache()
    
    try:
        # 执行登录
        driver = handler.semi_auto_login()
        
        if not driver:
            logger.error("\n❌ 登录失败")
            return 1
        
        logger.info("\n✅ 登录成功！")
        logger.info(f"当前URL: {driver.current_url}")
        
        # 执行测试
        if tests:
            results = run_tests(driver, tests, nav_only)
            print_results(results)
        else:
            logger.info("\n未指定测试模块，仅完成登录")
            logger.info("使用 --test 参数指定测试，如: --test deposit")
        
        # 保持浏览器打开
        if args.keep_open > 0:
            logger.info(f"\n浏览器将保持打开 {args.keep_open} 秒...")
            logger.info("按 Ctrl+C 可以提前退出\n")
            
            try:
                time.sleep(args.keep_open)
            except KeyboardInterrupt:
                logger.info("\n用户中断")
        
        return 0
            
    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return 1
    except Exception as e:
        logger.error(f"\n❌ 程序出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        handler.close()


if __name__ == "__main__":
    sys.exit(main())
