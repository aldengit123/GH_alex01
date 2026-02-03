"""
配置加载器
支持多站点配置和选择器管理
"""
import os
import yaml
import json
from typing import Any, Dict, Optional
from copy import deepcopy


class ConfigLoader:
    """配置加载器"""
    
    _instance = None
    _config = None
    _selectors = None
    _current_site = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
            self._load_selectors()
    
    def _get_config_dir(self) -> str:
        """获取配置目录路径"""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config"
        )
    
    def _load_config(self):
        """加载主配置文件"""
        config_path = os.path.join(self._get_config_dir(), "config.yaml")
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = {}
        
        # 设置当前站点
        self._current_site = self._config.get('current_site', '286')
    
    def _load_selectors(self):
        """加载选择器配置"""
        selectors_dir = os.path.join(self._get_config_dir(), "selectors")
        
        # 加载默认选择器
        default_path = os.path.join(selectors_dir, "default.yaml")
        if os.path.exists(default_path):
            with open(default_path, 'r', encoding='utf-8') as f:
                self._selectors = yaml.safe_load(f) or {}
        else:
            self._selectors = {}
    
    def _load_site_selectors(self, site_code: str) -> Dict:
        """
        加载站点特有选择器并与默认选择器合并
        
        Args:
            site_code: 站点代号
        
        Returns:
            合并后的选择器配置
        """
        merged = deepcopy(self._selectors)
        
        selectors_dir = os.path.join(self._get_config_dir(), "selectors")
        site_path = os.path.join(selectors_dir, f"{site_code}.yaml")
        
        if os.path.exists(site_path):
            with open(site_path, 'r', encoding='utf-8') as f:
                site_selectors = yaml.safe_load(f) or {}
            
            # 深度合并
            self._deep_merge(merged, site_selectors)
        
        return merged
    
    def _deep_merge(self, base: Dict, override: Dict):
        """
        深度合并字典
        
        Args:
            base: 基础字典（会被修改）
            override: 覆盖字典
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套key
        
        例如: config.get("app.base_url")
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict:
        """获取配置节"""
        return self._config.get(section, {})
    
    # ========== 站点相关方法 ==========
    
    def get_current_site(self) -> str:
        """获取当前站点代号"""
        return self._current_site
    
    def _normalize_site_key(self, site_code: str, sites: Dict) -> Optional[str]:
        """
        标准化站点代号（处理YAML可能把数字解析为int的情况）
        
        Args:
            site_code: 输入的站点代号
            sites: 站点配置字典
        
        Returns:
            匹配的站点key或None
        """
        # 直接匹配
        if site_code in sites:
            return site_code
        
        # 尝试整数匹配（YAML可能把286解析为整数286）
        try:
            int_code = int(site_code)
            if int_code in sites:
                return int_code
        except ValueError:
            pass
        
        # 尝试字符串匹配
        str_code = str(site_code)
        if str_code in sites:
            return str_code
        
        return None
    
    def set_current_site(self, site_code: str):
        """
        设置当前站点
        
        Args:
            site_code: 站点代号 (286, 231, 1PG, g66)
        """
        sites = self._config.get('sites', {})
        normalized_key = self._normalize_site_key(site_code, sites)
        
        if normalized_key is not None:
            self._current_site = str(site_code)  # 保存为字符串
        else:
            available = [str(k) for k in sites.keys()]
            raise ValueError(f"未知站点: {site_code}，可用站点: {available}")
    
    def get_site_config(self, site_code: Optional[str] = None) -> Dict:
        """
        获取站点配置
        
        Args:
            site_code: 站点代号，为None时使用当前站点
        
        Returns:
            站点配置字典
        """
        site = site_code or self._current_site
        sites = self._config.get('sites', {})
        
        normalized_key = self._normalize_site_key(site, sites)
        if normalized_key is not None:
            return sites.get(normalized_key, {})
        return {}
    
    def get_site_url(self, site_code: Optional[str] = None) -> str:
        """
        获取站点URL
        
        Args:
            site_code: 站点代号
        
        Returns:
            站点base_url
        """
        site_config = self.get_site_config(site_code)
        return site_config.get('base_url', self.app.get('base_url', ''))
    
    def get_all_sites(self) -> Dict:
        """获取所有站点配置"""
        return self._config.get('sites', {})
    
    # ========== 选择器相关方法 ==========
    
    def get_selectors(self, site_code: Optional[str] = None) -> Dict:
        """
        获取站点选择器配置
        
        Args:
            site_code: 站点代号，为None时使用当前站点
        
        Returns:
            合并后的选择器配置
        """
        site = site_code or self._current_site
        return self._load_site_selectors(site)
    
    def get_page_selectors(self, page: str, site_code: Optional[str] = None) -> Dict:
        """
        获取指定页面的选择器
        
        Args:
            page: 页面名称 (deposit, agent, sports, activity)
            site_code: 站点代号
        
        Returns:
            页面选择器配置
        """
        selectors = self.get_selectors(site_code)
        return selectors.get(page, {})
    
    def get_common_selectors(self, site_code: Optional[str] = None) -> Dict:
        """
        获取通用选择器
        
        Args:
            site_code: 站点代号
        
        Returns:
            通用选择器配置
        """
        selectors = self.get_selectors(site_code)
        return selectors.get('common', {})
    
    # ========== 属性 ==========
    
    @property
    def app(self) -> Dict:
        return self.get_section('app')
    
    @property
    def account(self) -> Dict:
        return self.get_section('account')
    
    @property
    def browser(self) -> Dict:
        return self.get_section('browser')
    
    @property
    def login(self) -> Dict:
        return self.get_section('login')
    
    @property
    def cache(self) -> Dict:
        return self.get_section('cache')
    
    @property
    def token(self) -> Dict:
        return self.get_section('token')
    
    @property
    def sites(self) -> Dict:
        return self.get_section('sites')
    
    @property
    def current_site(self) -> str:
        return self._current_site
    
    def reload(self):
        """重新加载配置"""
        self._config = None
        self._selectors = None
        self._load_config()
        self._load_selectors()


# 全局配置实例
config = ConfigLoader()
