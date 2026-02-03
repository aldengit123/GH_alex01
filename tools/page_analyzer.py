#!/usr/bin/env python3
"""
页面结构分析工具
使用本地浏览器抓取页面元素，用于确定选择器
"""
import sys
import os
import json
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.login.login_handler import LoginHandler
from src.utils.logger import get_logger
from src.utils.config_loader import config

logger = get_logger("page_analyzer")


def analyze_page(driver, page_name: str) -> dict:
    """
    分析当前页面结构
    
    Args:
        driver: WebDriver实例
        page_name: 页面名称
    
    Returns:
        页面元素信息
    """
    logger.info(f"\n分析页面: {page_name}")
    logger.info(f"URL: {driver.current_url}")
    
    result = {
        "page_name": page_name,
        "url": driver.current_url,
        "title": driver.title,
        "elements": {}
    }
    
    # 获取所有可点击元素
    clickable_script = """
    const elements = [];
    
    // 获取所有链接
    document.querySelectorAll('a').forEach((el, i) => {
        if (el.offsetParent !== null) {  // 可见元素
            elements.push({
                type: 'link',
                tag: 'a',
                text: el.innerText.trim().substring(0, 50),
                href: el.href,
                class: el.className,
                id: el.id
            });
        }
    });
    
    // 获取所有按钮
    document.querySelectorAll('button, [role="button"], [class*="btn"]').forEach((el, i) => {
        if (el.offsetParent !== null) {
            elements.push({
                type: 'button',
                tag: el.tagName.toLowerCase(),
                text: el.innerText.trim().substring(0, 50),
                class: el.className,
                id: el.id
            });
        }
    });
    
    // 获取底部导航
    document.querySelectorAll('[class*="nav"], [class*="tab"], [class*="footer"], [class*="menu"]').forEach((el, i) => {
        if (el.offsetParent !== null && el.children.length > 0) {
            const items = [];
            el.querySelectorAll('a, div, span').forEach(child => {
                if (child.innerText.trim()) {
                    items.push(child.innerText.trim().substring(0, 30));
                }
            });
            if (items.length > 0) {
                elements.push({
                    type: 'navigation',
                    tag: el.tagName.toLowerCase(),
                    class: el.className,
                    items: [...new Set(items)].slice(0, 10)
                });
            }
        }
    });
    
    // 获取输入框
    document.querySelectorAll('input, textarea').forEach((el, i) => {
        if (el.offsetParent !== null) {
            elements.push({
                type: 'input',
                tag: 'input',
                inputType: el.type,
                placeholder: el.placeholder,
                class: el.className,
                id: el.id,
                name: el.name
            });
        }
    });
    
    return elements;
    """
    
    try:
        elements = driver.execute_script(clickable_script)
        result["elements"] = elements
        logger.info(f"找到 {len(elements)} 个元素")
    except Exception as e:
        logger.error(f"分析失败: {e}")
    
    return result


def find_nav_entries(driver) -> dict:
    """
    专门查找导航入口
    """
    script = """
    const entries = {
        deposit: [],
        agent: [],
        sports: [],
        activity: [],
        earn: [],
        other: []
    };
    
    // 关键词映射
    const keywords = {
        deposit: ['存款', '充值', '入金', 'deposit', 'recharge', 'payment'],
        agent: ['代理', '推广', '合营', 'agent', 'affiliate', 'proxy'],
        sports: ['体育', '竞技', 'sport', 'game', '足球', '篮球'],
        activity: ['活动', '优惠', '红利', 'promo', 'bonus', 'activity'],
        earn: ['赚钱', '福利', '任务', 'earn', 'task', 'mission']
    };
    
    // 遍历所有可见的可点击元素
    document.querySelectorAll('a, button, [role="button"], div[class*="item"], span[class*="item"]').forEach(el => {
        if (el.offsetParent === null) return;  // 跳过不可见元素
        
        const text = el.innerText.trim().toLowerCase();
        const className = (el.className || '').toLowerCase();
        const href = (el.href || '').toLowerCase();
        
        const info = {
            text: el.innerText.trim().substring(0, 30),
            class: el.className.substring(0, 100),
            tag: el.tagName.toLowerCase(),
            href: el.href || ''
        };
        
        let matched = false;
        for (const [category, words] of Object.entries(keywords)) {
            for (const word of words) {
                if (text.includes(word) || className.includes(word) || href.includes(word)) {
                    entries[category].push(info);
                    matched = true;
                    break;
                }
            }
            if (matched) break;
        }
    });
    
    return entries;
    """
    
    try:
        return driver.execute_script(script)
    except Exception as e:
        logger.error(f"查找入口失败: {e}")
        return {}


def save_results(results: dict, filename: str):
    """保存结果到文件"""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n结果已保存到: {filepath}")
    return filepath


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="页面结构分析工具")
    parser.add_argument("--site", "-s", type=str, default="286", help="站点代号")
    args = parser.parse_args()
    
    # 设置站点
    try:
        config.set_current_site(args.site)
    except ValueError as e:
        logger.error(str(e))
        return 1
    
    site_code = config.get_current_site()
    site_config = config.get_site_config()
    
    print("\n" + "="*60)
    print("        页面结构分析工具")
    print("="*60)
    print(f"  站点: {site_config.get('name', site_code)}")
    print(f"  URL: {site_config.get('base_url', '')}")
    print("="*60)
    print("\n请在浏览器中登录，登录成功后脚本会自动分析页面结构。\n")
    
    handler = LoginHandler(session_name=f"analyzer_{site_code}")
    
    try:
        driver = handler.semi_auto_login()
        
        if not driver:
            logger.error("登录失败")
            return 1
        
        logger.info("\n✅ 登录成功！开始分析页面结构...\n")
        
        all_results = {
            "site": site_code,
            "base_url": driver.current_url,
            "pages": {}
        }
        
        # 分析首页
        time.sleep(2)
        all_results["pages"]["home"] = analyze_page(driver, "首页")
        
        # 查找各入口
        logger.info("\n" + "="*50)
        logger.info("查找页面入口...")
        logger.info("="*50)
        
        entries = find_nav_entries(driver)
        all_results["entries"] = entries
        
        # 打印找到的入口
        print("\n" + "="*60)
        print("                 找到的页面入口")
        print("="*60)
        
        for category, items in entries.items():
            if items:
                print(f"\n【{category.upper()}】找到 {len(items)} 个可能的入口:")
                for i, item in enumerate(items[:3]):  # 只显示前3个
                    print(f"  {i+1}. 文字: {item.get('text', 'N/A')}")
                    print(f"     class: {item.get('class', 'N/A')[:60]}")
                    if item.get('href'):
                        print(f"     href: {item.get('href', '')[:60]}")
        
        # 保存结果
        filename = f"page_structure_{site_code}.json"
        filepath = save_results(all_results, filename)
        
        print("\n" + "="*60)
        print("                    分析完成")
        print("="*60)
        print(f"\n结果已保存到: {filepath}")
        print("\n请将此文件内容发送给AI，以便更新选择器配置。")
        print("\n浏览器将保持打开30秒，你可以手动浏览其他页面...")
        
        time.sleep(30)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return 1
    finally:
        handler.close()


if __name__ == "__main__":
    sys.exit(main())
