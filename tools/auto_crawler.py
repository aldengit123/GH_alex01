#!/usr/bin/env python3
"""
自动采集脚本
自动遍历网站所有页面，采集完整的页面结构信息
"""
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Set

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.login.login_handler import LoginHandler
from src.utils.logger import get_logger
from src.utils.config_loader import config

logger = get_logger("auto_crawler")


class AutoCrawler:
    """自动采集器"""
    
    def __init__(self, driver):
        self.driver = driver
        self.visited_urls: Set[str] = set()
        self.all_pages: List[Dict] = []
        self.all_elements: Dict = {
            "nav_items": [],
            "buttons": [],
            "links": [],
            "inputs": [],
            "games": [],
            "unique_classes": set(),
        }
        self.base_url = driver.current_url.split('?')[0].rstrip('/')
        self.home_url = driver.current_url
        self.page_load_timeout = 10  # 页面加载超时时间
        self.errors: List[Dict] = []  # 记录错误
    
    def wait_for_page_load(self, timeout: int = None) -> bool:
        """
        等待页面加载完成
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            是否加载成功
        """
        timeout = timeout or self.page_load_timeout
        
        try:
            # 等待document.readyState为complete
            start_time = time.time()
            while time.time() - start_time < timeout:
                ready_state = self.driver.execute_script("return document.readyState")
                if ready_state == "complete":
                    # 额外等待一下动态内容
                    time.sleep(1)
                    return True
                time.sleep(0.5)
            
            logger.warning(f"页面加载超时 ({timeout}秒)")
            return False
            
        except Exception as e:
            logger.error(f"等待页面加载失败: {e}")
            return False
    
    def wait_for_url_change(self, original_url: str, timeout: int = 10) -> bool:
        """
        等待URL变化（说明跳转成功）
        
        Args:
            original_url: 原始URL
            timeout: 超时时间
        
        Returns:
            URL是否变化
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            if current_url != original_url:
                self.wait_for_page_load()
                return True
            time.sleep(0.5)
        return False
    
    def safe_click(self, script: str, wait_for_navigation: bool = True) -> bool:
        """
        安全点击（带异常处理和等待）
        
        Args:
            script: 点击脚本
            wait_for_navigation: 是否等待页面跳转
        
        Returns:
            是否成功
        """
        original_url = self.driver.current_url
        
        try:
            result = self.driver.execute_script(script)
            if result:
                if wait_for_navigation:
                    # 等待URL变化或页面加载
                    time.sleep(1)
                    if self.driver.current_url != original_url:
                        self.wait_for_page_load()
                    else:
                        # URL没变，等待可能的内容变化
                        time.sleep(2)
                else:
                    time.sleep(1)
                return True
            return False
        except Exception as e:
            logger.error(f"点击失败: {e}")
            return False
    
    def safe_go_back(self) -> bool:
        """安全返回上一页"""
        try:
            self.driver.back()
            self.wait_for_page_load()
            return True
        except Exception as e:
            logger.error(f"返回失败: {e}")
            # 尝试直接回首页
            return self.go_home()
    
    def safe_capture(self, page_name: str) -> Dict:
        """
        安全采集（带异常处理）
        
        Args:
            page_name: 页面名称
        
        Returns:
            采集结果
        """
        try:
            data = self.capture_page_full()
            data["page_name"] = page_name
            return data
        except Exception as e:
            error_info = {
                "page_name": page_name,
                "error": str(e),
                "url": self.driver.current_url
            }
            self.errors.append(error_info)
            logger.error(f"采集 {page_name} 失败: {e}")
            return error_info
    
    def capture_page_full(self) -> Dict:
        """完整采集当前页面"""
        script = """
        const result = {
            url: window.location.href,
            title: document.title,
            timestamp: new Date().toISOString(),
            
            // 底部/顶部导航
            navigation: [],
            
            // 所有可点击元素
            clickables: [],
            
            // 所有输入框
            inputs: [],
            
            // 所有文字元素
            texts: [],
            
            // 所有图片
            images: [],
            
            // 所有class名（用于分析）
            allClasses: new Set(),
            
            // iframe列表
            iframes: []
        };
        
        // 采集导航元素
        document.querySelectorAll('.item, [class*="nav-item"], [class*="tab-item"], [class*="menu-item"]').forEach(el => {
            if (el.offsetParent !== null) {
                result.navigation.push({
                    text: el.innerText.trim().substring(0, 50),
                    class: el.className,
                    tag: el.tagName.toLowerCase(),
                    isActive: el.className.includes('active'),
                    rect: el.getBoundingClientRect()
                });
            }
        });
        
        // 采集所有可点击元素
        document.querySelectorAll('a, button, [role="button"], [onclick], .btn, [class*="btn"]').forEach(el => {
            if (el.offsetParent !== null) {
                const rect = el.getBoundingClientRect();
                result.clickables.push({
                    text: el.innerText.trim().substring(0, 100),
                    tag: el.tagName.toLowerCase(),
                    class: el.className.substring(0, 150),
                    id: el.id,
                    href: el.href || '',
                    type: el.type || '',
                    position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                });
                
                // 收集class
                el.className.split(' ').forEach(c => {
                    if (c.trim()) result.allClasses.add(c.trim());
                });
            }
        });
        
        // 采集可点击的div（游戏入口等）
        document.querySelectorAll('.game, .helf, [class*="game-item"], [class*="play"]').forEach(el => {
            if (el.offsetParent !== null) {
                const rect = el.getBoundingClientRect();
                result.clickables.push({
                    text: el.innerText.trim().substring(0, 100),
                    tag: el.tagName.toLowerCase(),
                    class: el.className.substring(0, 150),
                    id: el.id,
                    isGame: true,
                    position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                });
            }
        });
        
        // 采集输入框
        document.querySelectorAll('input, textarea, select').forEach(el => {
            if (el.offsetParent !== null) {
                result.inputs.push({
                    type: el.type || el.tagName.toLowerCase(),
                    name: el.name,
                    id: el.id,
                    class: el.className.substring(0, 100),
                    placeholder: el.placeholder || '',
                    value: el.value || '',
                    required: el.required
                });
            }
        });
        
        // 采集主要文字区块
        document.querySelectorAll('h1, h2, h3, .title, [class*="title"], [class*="header"], label').forEach(el => {
            if (el.offsetParent !== null && el.innerText.trim()) {
                result.texts.push({
                    text: el.innerText.trim().substring(0, 100),
                    tag: el.tagName.toLowerCase(),
                    class: el.className.substring(0, 100)
                });
            }
        });
        
        // 采集iframe
        document.querySelectorAll('iframe').forEach(el => {
            result.iframes.push({
                src: el.src,
                id: el.id,
                class: el.className,
                width: el.width,
                height: el.height
            });
        });
        
        // 转换Set为Array
        result.allClasses = [...result.allClasses];
        
        // 去重
        result.clickables = result.clickables.filter((v, i, a) => 
            a.findIndex(t => t.text === v.text && t.class === v.class) === i
        );
        
        result.navigation = result.navigation.filter((v, i, a) => 
            a.findIndex(t => t.text === v.text) === i
        );
        
        return result;
        """
        
        try:
            return self.driver.execute_script(script)
        except Exception as e:
            logger.error(f"采集失败: {e}")
            return {"error": str(e), "url": self.driver.current_url}
    
    def find_all_nav_entries(self) -> List[Dict]:
        """查找所有导航入口"""
        script = """
        const entries = [];
        
        // 底部导航项
        document.querySelectorAll('.item').forEach(el => {
            if (el.offsetParent !== null && el.innerText.trim()) {
                entries.push({
                    type: 'bottom_nav',
                    text: el.innerText.trim().replace(/\\n/g, ' ').substring(0, 30),
                    class: el.className,
                    element_index: [...el.parentElement.children].indexOf(el)
                });
            }
        });
        
        // 游戏入口
        document.querySelectorAll('.helf, .game').forEach(el => {
            if (el.offsetParent !== null) {
                const text = el.querySelector('.play-name, .text, .icon')?.innerText?.trim() || el.innerText.trim();
                if (text) {
                    entries.push({
                        type: 'game_entry',
                        text: text.substring(0, 30),
                        class: el.className
                    });
                }
            }
        });
        
        // 顶部按钮
        document.querySelectorAll('.recharge-btn, .day-water-icon, [class*="btn"]').forEach(el => {
            if (el.offsetParent !== null && el.innerText.trim()) {
                entries.push({
                    type: 'top_button',
                    text: el.innerText.trim().substring(0, 30),
                    class: el.className
                });
            }
        });
        
        return entries;
        """
        
        try:
            return self.driver.execute_script(script)
        except Exception as e:
            logger.error(f"查找入口失败: {e}")
            return []
    
    def click_by_text(self, text: str, selector: str = ".item", wait_nav: bool = True) -> bool:
        """通过文字点击元素"""
        script = f"""
        const elements = document.querySelectorAll('{selector}');
        for (let el of elements) {{
            if (el.innerText.includes('{text}')) {{
                el.click();
                return true;
            }}
        }}
        return false;
        """
        return self.safe_click(script, wait_for_navigation=wait_nav)
    
    def click_by_class(self, class_name: str, wait_nav: bool = True) -> bool:
        """通过class点击元素"""
        script = f"""
        const el = document.querySelector('.{class_name}');
        if (el) {{
            el.click();
            return true;
        }}
        return false;
        """
        return self.safe_click(script, wait_for_navigation=wait_nav)
    
    def go_back(self) -> bool:
        """返回上一页"""
        return self.safe_go_back()
    
    def go_home(self) -> bool:
        """返回首页"""
        try:
            # 方式1: 尝试点击首页导航
            script = """
            const items = document.querySelectorAll('.item');
            for (let el of items) {
                if (el.innerText.includes('首页')) {
                    el.click();
                    return true;
                }
            }
            return false;
            """
            if self.safe_click(script):
                logger.info("通过导航返回首页")
                return True
            
            # 方式2: 直接导航到首页URL
            logger.info("直接导航到首页URL")
            self.driver.get(self.home_url)
            self.wait_for_page_load()
            return True
            
        except Exception as e:
            logger.error(f"返回首页失败: {e}")
            # 最后尝试：刷新并导航
            try:
                self.driver.get(self.base_url)
                self.wait_for_page_load()
                return True
            except:
                return False
    
    def crawl_all(self, max_depth: int = 2) -> Dict:
        """
        自动采集所有页面
        
        Args:
            max_depth: 最大深度
        
        Returns:
            采集结果
        """
        logger.info("="*60)
        logger.info("开始自动采集...")
        logger.info("="*60)
        
        results = {
            "site": config.get_current_site(),
            "base_url": self.base_url,
            "home_url": self.home_url,
            "crawl_time": datetime.now().isoformat(),
            "pages": {},
            "navigation_map": {},
            "all_classes": set(),
            "errors": [],
            "summary": {}
        }
        
        # 1. 采集首页
        logger.info("\n[1/6] 采集首页...")
        try:
            self.wait_for_page_load()
            home_data = self.safe_capture("home")
            results["pages"]["home"] = home_data
            self.visited_urls.add(self.driver.current_url)
            
            # 获取所有导航入口
            nav_entries = self.find_all_nav_entries()
            results["navigation_map"]["home"] = nav_entries
            logger.info(f"找到 {len(nav_entries)} 个导航入口")
        except Exception as e:
            logger.error(f"采集首页失败: {e}")
            self.errors.append({"page": "home", "error": str(e)})
        
        # 2. 遍历底部导航
        logger.info("\n[2/6] 采集底部导航页面...")
        bottom_nav_texts = ["赚钱", "活动", "存款", "我的"]
        
        for nav_text in bottom_nav_texts:
            try:
                # 确保回到首页
                if not self.go_home():
                    logger.error("无法返回首页，跳过此导航")
                    continue
                
                logger.info(f"  → 进入: {nav_text}")
                if self.click_by_text(nav_text, ".item"):
                    page_key = f"nav_{nav_text}"
                    page_data = self.safe_capture(page_key)
                    results["pages"][page_key] = page_data
                    
                    # 查找该页面的子入口
                    sub_entries = self.find_all_nav_entries()
                    results["navigation_map"][page_key] = sub_entries
                    logger.info(f"    ✓ 采集完成: {page_data.get('url', '')[:60]}")
                else:
                    logger.warning(f"    ✗ 未找到: {nav_text}")
                    
            except Exception as e:
                logger.error(f"    ✗ 采集 {nav_text} 失败: {e}")
                self.errors.append({"page": f"nav_{nav_text}", "error": str(e)})
                # 尝试恢复
                self.go_home()
        
        # 3. 采集存款页面（从首页顶部按钮进入）
        logger.info("\n[3/6] 采集存款页面（顶部入口）...")
        try:
            if not self.go_home():
                logger.error("无法返回首页")
            else:
                if self.click_by_class("recharge-btn"):
                    # 存款页可能跳转到外部页面，多等待一下
                    self.wait_for_page_load(timeout=15)
                    page_data = self.safe_capture("deposit_top")
                    results["pages"]["deposit_top"] = page_data
                    logger.info(f"  ✓ 存款页采集完成: {page_data.get('url', '')[:60]}")
                else:
                    logger.warning("  ✗ 未找到顶部存款按钮")
        except Exception as e:
            logger.error(f"  ✗ 存款页采集失败: {e}")
            self.errors.append({"page": "deposit_top", "error": str(e)})
        
        # 4. 采集游戏入口页面（采样几个）
        logger.info("\n[4/6] 采集游戏入口页面...")
        game_samples = ["熊猫体育", "麻将胡了", "PA视讯", "开元棋牌"]
        
        for game_name in game_samples:
            try:
                if not self.go_home():
                    logger.error("无法返回首页，跳过游戏采集")
                    break
                
                logger.info(f"  → 进入游戏: {game_name}")
                
                # 尝试通过文字点击游戏
                script = f"""
                const elements = document.querySelectorAll('.helf, .play-name, .game, [class*="game"]');
                for (let el of elements) {{
                    if (el.innerText.includes('{game_name}')) {{
                        el.click();
                        return true;
                    }}
                }}
                return false;
                """
                
                if self.safe_click(script, wait_for_navigation=True):
                    # 游戏页可能加载较慢或有iframe
                    self.wait_for_page_load(timeout=10)
                    page_data = self.safe_capture(f"game_{game_name}")
                    results["pages"][f"game_{game_name}"] = page_data
                    logger.info(f"    ✓ 游戏页采集完成: {game_name}")
                    
                    # 检查是否有iframe（游戏通常在iframe中）
                    iframes = page_data.get("iframes", [])
                    if iframes:
                        logger.info(f"    发现 {len(iframes)} 个iframe")
                else:
                    logger.warning(f"    ✗ 未找到游戏入口: {game_name}")
                    
            except Exception as e:
                logger.error(f"    ✗ 游戏 {game_name} 采集失败: {e}")
                self.errors.append({"page": f"game_{game_name}", "error": str(e)})
                # 尝试返回
                self.go_home()
        
        # 5. 采集"我的"页面内的子页面
        logger.info("\n[5/6] 采集'我的'页面子入口...")
        try:
            if not self.go_home():
                logger.error("无法返回首页")
            else:
                if self.click_by_text("我的", ".item"):
                    # 采集我的页面的所有可点击元素
                    my_page_data = self.safe_capture("my_page_full")
                    results["pages"]["my_page_full"] = my_page_data
                    
                    # 查找我的页面内的所有可点击项
                    my_clickables = my_page_data.get("clickables", [])
                    logger.info(f"  '我的'页面有 {len(my_clickables)} 个可点击元素")
                    
                    # 寻找并采集子页面
                    sub_pages_to_crawl = ["代理", "推广", "邀请", "设置", "账户", "银行卡", "提款", "记录"]
                    
                    for keyword in sub_pages_to_crawl:
                        # 先回到我的页面
                        self.go_home()
                        self.click_by_text("我的", ".item")
                        
                        # 尝试找到并点击
                        found = False
                        for el in my_clickables:
                            if keyword in el.get("text", ""):
                                logger.info(f"  → 尝试进入: {keyword}")
                                if self.click_by_text(keyword):
                                    page_data = self.safe_capture(f"my_{keyword}")
                                    results["pages"][f"my_{keyword}"] = page_data
                                    logger.info(f"    ✓ 子页面采集完成: {keyword}")
                                    found = True
                                break
                        
                        if not found:
                            # 直接尝试点击
                            if self.click_by_text(keyword):
                                page_data = self.safe_capture(f"my_{keyword}")
                                results["pages"][f"my_{keyword}"] = page_data
                                logger.info(f"    ✓ 子页面采集完成: {keyword}")
                                
        except Exception as e:
            logger.error(f"  ✗ '我的'页面采集失败: {e}")
            self.errors.append({"page": "my_page", "error": str(e)})
        
        # 6. 返回首页，最终确认
        logger.info("\n[6/6] 最终确认...")
        self.go_home()
        
        # 汇总统计
        results["all_classes"] = list(results["all_classes"]) if isinstance(results["all_classes"], set) else results["all_classes"]
        results["errors"] = self.errors
        results["summary"] = {
            "total_pages": len(results["pages"]),
            "pages_list": list(results["pages"].keys()),
            "error_count": len(self.errors),
            "success_rate": f"{(len(results['pages']) / (len(results['pages']) + len(self.errors)) * 100):.1f}%" if results["pages"] else "0%"
        }
        
        logger.info("\n" + "="*60)
        logger.info(f"采集完成！")
        logger.info(f"  成功采集: {len(results['pages'])} 个页面")
        logger.info(f"  采集失败: {len(self.errors)} 个")
        logger.info(f"  成功率: {results['summary']['success_rate']}")
        logger.info("="*60)
        
        return results


def save_results(results: Dict, site_code: str) -> str:
    """保存采集结果"""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 处理set类型
    def convert_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets(i) for i in obj]
        return obj
    
    results = convert_sets(results)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"full_crawl_{site_code}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存到: {filepath}")
    return filepath


def generate_selectors_from_crawl(results: Dict) -> Dict:
    """从采集结果生成选择器建议"""
    selectors = {
        "deposit": {},
        "agent": {},
        "sports": {},
        "activity": {},
        "common": {}
    }
    
    # 分析首页
    home = results.get("pages", {}).get("home", {})
    
    # 查找存款入口
    for el in home.get("clickables", []):
        if "存款" in el.get("text", "") or "recharge" in el.get("class", "").lower():
            selectors["deposit"]["entry"] = f".{el['class'].split()[0]}" if el.get("class") else ""
            break
    
    # 查找导航
    for nav in home.get("navigation", []):
        text = nav.get("text", "")
        if "活动" in text:
            selectors["activity"]["nav_text"] = "活动"
        elif "赚钱" in text:
            selectors["activity"]["earn_text"] = "赚钱"
    
    return selectors


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="自动采集脚本")
    parser.add_argument("--site", "-s", type=str, default="286", help="站点代号")
    parser.add_argument("--depth", "-d", type=int, default=2, help="采集深度")
    args = parser.parse_args()
    
    try:
        config.set_current_site(args.site)
    except ValueError as e:
        print(f"错误: {e}")
        return 1
    
    site_code = config.get_current_site()
    site_config = config.get_site_config()
    
    print("\n" + "="*60)
    print("        自动采集脚本")
    print("="*60)
    print(f"  站点: {site_config.get('name', site_code)}")
    print(f"  URL: {site_config.get('base_url', '')}")
    print(f"  采集深度: {args.depth}")
    print("="*60)
    print("\n请在浏览器中完成登录，登录成功后将自动开始采集...\n")
    
    handler = LoginHandler(session_name=f"crawler_{site_code}")
    
    try:
        driver = handler.semi_auto_login()
        
        if not driver:
            logger.error("登录失败")
            return 1
        
        logger.info("\n✅ 登录成功！等待2秒后开始采集...\n")
        time.sleep(2)
        
        # 创建采集器并执行采集
        crawler = AutoCrawler(driver)
        results = crawler.crawl_all(max_depth=args.depth)
        
        # 保存结果
        filepath = save_results(results, site_code)
        
        # 生成选择器建议
        suggested_selectors = generate_selectors_from_crawl(results)
        
        print("\n" + "="*60)
        print("                 采集结果摘要")
        print("="*60)
        print(f"\n采集页面数: {results['summary']['total_pages']}")
        print(f"页面列表: {', '.join(results['summary']['pages_list'])}")
        print(f"\n结果文件: {filepath}")
        print("\n请将结果文件发送给AI以更新选择器配置。")
        print("="*60)
        
        # 保持浏览器打开一会
        print("\n浏览器将保持打开10秒...")
        time.sleep(10)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return 1
    finally:
        handler.close()


if __name__ == "__main__":
    sys.exit(main())
