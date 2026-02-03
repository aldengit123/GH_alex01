#!/usr/bin/env python3
"""
交互式页面分析工具
登录后可以手动导航，随时按回车抓取当前页面结构
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.login.login_handler import LoginHandler
from src.utils.logger import get_logger
from src.utils.config_loader import config

logger = get_logger("interactive")


def capture_page(driver) -> dict:
    """抓取当前页面关键信息"""
    
    script = """
    const result = {
        url: window.location.href,
        title: document.title,
        visibleText: [],
        clickables: [],
        inputs: []
    };
    
    // 获取所有可见的文字元素
    document.querySelectorAll('a, button, span, div, p, h1, h2, h3, label').forEach(el => {
        if (el.offsetParent !== null && el.innerText.trim()) {
            const text = el.innerText.trim();
            if (text.length < 50 && text.length > 0) {
                result.visibleText.push({
                    text: text,
                    tag: el.tagName.toLowerCase(),
                    class: el.className.substring(0, 80)
                });
            }
        }
    });
    
    // 获取可点击元素
    document.querySelectorAll('a, button, [role="button"]').forEach(el => {
        if (el.offsetParent !== null) {
            result.clickables.push({
                text: el.innerText.trim().substring(0, 30),
                tag: el.tagName.toLowerCase(),
                class: el.className.substring(0, 80),
                href: el.href || ''
            });
        }
    });
    
    // 获取输入框
    document.querySelectorAll('input, textarea, select').forEach(el => {
        if (el.offsetParent !== null) {
            result.inputs.push({
                type: el.type || el.tagName.toLowerCase(),
                placeholder: el.placeholder || '',
                class: el.className.substring(0, 80),
                id: el.id,
                name: el.name
            });
        }
    });
    
    // 去重
    result.visibleText = result.visibleText.filter((v, i, a) => 
        a.findIndex(t => t.text === v.text) === i
    ).slice(0, 50);
    
    result.clickables = result.clickables.filter((v, i, a) => 
        a.findIndex(t => t.text === v.text && t.class === v.class) === i
    ).slice(0, 30);
    
    return result;
    """
    
    return driver.execute_script(script)


def print_page_info(info: dict):
    """打印页面信息"""
    print("\n" + "="*60)
    print(f"URL: {info['url']}")
    print(f"标题: {info['title']}")
    print("="*60)
    
    print("\n【可点击元素】")
    for i, el in enumerate(info.get('clickables', [])[:15]):
        text = el.get('text', '').replace('\n', ' ')
        if text:
            print(f"  {i+1}. [{el['tag']}] {text}")
            print(f"      class: {el.get('class', '')[:50]}")
    
    print("\n【输入框】")
    for i, el in enumerate(info.get('inputs', [])[:10]):
        print(f"  {i+1}. type={el.get('type', '')} placeholder='{el.get('placeholder', '')}'")
        print(f"      class: {el.get('class', '')[:50]}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="交互式页面分析")
    parser.add_argument("--site", "-s", type=str, default="286", help="站点代号")
    args = parser.parse_args()
    
    try:
        config.set_current_site(args.site)
    except ValueError as e:
        print(f"错误: {e}")
        return 1
    
    site_code = config.get_current_site()
    
    print("\n" + "="*60)
    print("        交互式页面分析工具")
    print("="*60)
    print(f"  站点: {site_code}")
    print("\n  操作说明:")
    print("  - 按 Enter: 抓取当前页面结构")
    print("  - 输入 'save': 保存所有抓取的页面到文件")
    print("  - 输入 'quit': 退出")
    print("="*60 + "\n")
    
    handler = LoginHandler(session_name=f"interactive_{site_code}")
    
    try:
        driver = handler.semi_auto_login()
        
        if not driver:
            print("登录失败")
            return 1
        
        print("\n✅ 登录成功！")
        print("\n现在你可以在浏览器中导航到不同页面。")
        print("每到一个页面，按 Enter 抓取页面结构。\n")
        
        all_captures = []
        
        while True:
            cmd = input("\n[按Enter抓取 / save保存 / quit退出] > ").strip().lower()
            
            if cmd == 'quit' or cmd == 'q':
                break
            elif cmd == 'save' or cmd == 's':
                if all_captures:
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
                    os.makedirs(output_dir, exist_ok=True)
                    filepath = os.path.join(output_dir, f"captures_{site_code}.json")
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(all_captures, f, ensure_ascii=False, indent=2)
                    print(f"\n已保存 {len(all_captures)} 个页面到: {filepath}")
                else:
                    print("还没有抓取任何页面")
            else:
                try:
                    info = capture_page(driver)
                    all_captures.append(info)
                    print_page_info(info)
                    print(f"\n(已抓取 {len(all_captures)} 个页面)")
                except Exception as e:
                    print(f"抓取失败: {e}")
        
        # 退出前自动保存
        if all_captures:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, f"captures_{site_code}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(all_captures, f, ensure_ascii=False, indent=2)
            print(f"\n结果已自动保存到: {filepath}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n用户中断")
        return 1
    finally:
        handler.close()


if __name__ == "__main__":
    sys.exit(main())
