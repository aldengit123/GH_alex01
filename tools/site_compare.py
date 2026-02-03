#!/usr/bin/env python3
"""
站点对比工具
比较不同站点的采集结果，识别差异点
"""
import sys
import os
import json
from typing import Dict, List, Set
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import get_logger

logger = get_logger("site_compare")


def load_crawl_data(site_code: str) -> Dict:
    """加载站点采集数据"""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    
    # 查找该站点最新的采集文件
    files = []
    for f in os.listdir(output_dir):
        if f.startswith(f"full_crawl_{site_code}_") and f.endswith(".json"):
            files.append(os.path.join(output_dir, f))
    
    if not files:
        return None
    
    # 取最新的
    latest = max(files, key=os.path.getctime)
    
    with open(latest, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_key_selectors(data: Dict) -> Dict:
    """从采集数据中提取关键选择器"""
    result = {
        "nav_items": [],
        "clickable_classes": set(),
        "page_urls": {},
        "page_titles": {},
    }
    
    if not data:
        return result
    
    pages = data.get("pages", {})
    nav_map = data.get("navigation_map", {})
    
    # 提取导航项
    for page_name, nav_items in nav_map.items():
        for item in nav_items:
            text = item.get("text", "").replace("\n", " ")
            if text and text not in [n["text"] for n in result["nav_items"]]:
                result["nav_items"].append({
                    "text": text,
                    "class": item.get("class", ""),
                    "index": item.get("element_index", -1)
                })
    
    # 提取页面URL和标题
    for page_name, page_data in pages.items():
        if isinstance(page_data, dict):
            result["page_urls"][page_name] = page_data.get("url", "")
            result["page_titles"][page_name] = page_data.get("title", "")
            
            # 提取可点击元素的class
            for el in page_data.get("clickables", []):
                cls = el.get("class", "")
                if cls:
                    for c in cls.split():
                        if c and not c.startswith("download"):
                            result["clickable_classes"].add(c)
    
    result["clickable_classes"] = list(result["clickable_classes"])
    return result


def compare_sites(site1_code: str, site2_code: str) -> Dict:
    """比较两个站点的差异"""
    data1 = load_crawl_data(site1_code)
    data2 = load_crawl_data(site2_code)
    
    if not data1:
        print(f"未找到站点 {site1_code} 的采集数据")
        return None
    if not data2:
        print(f"未找到站点 {site2_code} 的采集数据")
        return None
    
    sel1 = extract_key_selectors(data1)
    sel2 = extract_key_selectors(data2)
    
    comparison = {
        "sites": [site1_code, site2_code],
        "nav_diff": {
            "only_in_1": [],
            "only_in_2": [],
            "common": []
        },
        "class_diff": {
            "only_in_1": [],
            "only_in_2": [],
            "common": []
        },
        "url_patterns": {
            site1_code: sel1["page_urls"],
            site2_code: sel2["page_urls"]
        }
    }
    
    # 比较导航项
    texts1 = {n["text"] for n in sel1["nav_items"]}
    texts2 = {n["text"] for n in sel2["nav_items"]}
    
    comparison["nav_diff"]["only_in_1"] = list(texts1 - texts2)
    comparison["nav_diff"]["only_in_2"] = list(texts2 - texts1)
    comparison["nav_diff"]["common"] = list(texts1 & texts2)
    
    # 比较class
    classes1 = set(sel1["clickable_classes"])
    classes2 = set(sel2["clickable_classes"])
    
    comparison["class_diff"]["only_in_1"] = list(classes1 - classes2)
    comparison["class_diff"]["only_in_2"] = list(classes2 - classes1)
    comparison["class_diff"]["common"] = list(classes1 & classes2)
    
    return comparison


def generate_diff_config(comparison: Dict, base_site: str, target_site: str) -> str:
    """根据比较结果生成差异配置"""
    config_lines = [
        f"# {target_site}站点选择器配置",
        f"# 基于与{base_site}站点的对比自动生成",
        f"# 请根据实际情况调整",
        "",
        f'site_name: "{target_site}站点"',
        "",
        "# ============ 差异配置 ============",
        ""
    ]
    
    # 导航差异
    only_in_target = comparison["nav_diff"]["only_in_2"]
    if only_in_target:
        config_lines.append(f"# {target_site}特有的导航项: {only_in_target}")
        config_lines.append("# nav:")
        config_lines.append("#   texts:")
        for text in only_in_target:
            config_lines.append(f'#     custom: "{text}"')
        config_lines.append("")
    
    # class差异
    only_classes = comparison["class_diff"]["only_in_2"][:10]
    if only_classes:
        config_lines.append(f"# {target_site}特有的class: {only_classes}")
        config_lines.append("")
    
    return "\n".join(config_lines)


def print_comparison(comparison: Dict):
    """打印比较结果"""
    site1, site2 = comparison["sites"]
    
    print("\n" + "="*60)
    print(f"        站点对比: {site1} vs {site2}")
    print("="*60)
    
    print("\n【导航项差异】")
    print(f"  共同项: {comparison['nav_diff']['common']}")
    if comparison['nav_diff']['only_in_1']:
        print(f"  仅{site1}: {comparison['nav_diff']['only_in_1']}")
    if comparison['nav_diff']['only_in_2']:
        print(f"  仅{site2}: {comparison['nav_diff']['only_in_2']}")
    
    print("\n【Class差异】")
    print(f"  共同class数: {len(comparison['class_diff']['common'])}")
    print(f"  仅{site1}: {len(comparison['class_diff']['only_in_1'])}个")
    print(f"  仅{site2}: {len(comparison['class_diff']['only_in_2'])}个")
    
    if comparison['class_diff']['only_in_1'][:5]:
        print(f"    示例: {comparison['class_diff']['only_in_1'][:5]}")
    if comparison['class_diff']['only_in_2'][:5]:
        print(f"    示例: {comparison['class_diff']['only_in_2'][:5]}")
    
    print("\n【URL模式】")
    for site, urls in comparison["url_patterns"].items():
        print(f"\n  {site}:")
        for page, url in list(urls.items())[:5]:
            print(f"    {page}: {url[:50]}...")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="站点对比工具")
    parser.add_argument("--site1", "-s1", type=str, required=True, help="第一个站点代号")
    parser.add_argument("--site2", "-s2", type=str, required=True, help="第二个站点代号")
    parser.add_argument("--generate", "-g", action="store_true", help="生成差异配置")
    
    args = parser.parse_args()
    
    comparison = compare_sites(args.site1, args.site2)
    
    if comparison:
        print_comparison(comparison)
        
        if args.generate:
            print("\n" + "="*60)
            print("        生成的差异配置")
            print("="*60)
            config = generate_diff_config(comparison, args.site1, args.site2)
            print(config)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
