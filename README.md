# H5自动化测试框架

> 多站点支持 + 半自动登录 + 缓存复用方案

## 📖 项目简介

本框架支持多站点H5自动化测试，解决了**滑块验证码问题**，采用：
- **首次登录**：自动输入账号密码 → 人工处理滑块 → 保存会话
- **后续测试**：直接加载缓存 → 跳过登录步骤
- **多站点支持**：286、231、1PG、g66 四个站点

## 🌐 支持的站点

| 代号 | 名称 | URL |
|------|------|-----|
| 286 | 286站点 | https://qatwk.zhzhse.com |
| 231 | 231站点 | https://qat266.zhzhse.com |
| 1PG | 1PG站点 | https://qat1pg.zhzhse.com |
| g66 | g66站点 | https://qat196.zhzhse.com |

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /Users/lank/Desktop/h5_auto
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 运行测试

```bash
# 查看可用站点
python main.py --list-sites

# 查看可用测试
python main.py --list-tests

# 指定站点运行存款测试
python main.py --site 286 --test deposit

# 运行多个测试
python main.py --site 286 --test deposit,agent,sports

# 运行所有测试
python main.py --site 286 --test all
```

### 3. 首次登录

首次运行时需要手动处理滑块验证码：
1. 脚本自动打开浏览器并输入账号密码
2. **手动滑动验证码** ← 唯一需要人工操作的步骤
3. 登录成功后自动保存会话
4. 后续运行自动复用缓存

---

## 📚 在UI自动化测试中调用登录

### 方式一：直接使用 LoginHandler（推荐）

```python
from src.login.login_handler import LoginHandler

# 创建登录处理器
handler = LoginHandler()

# 获取已登录的浏览器实例
# - 如果有有效缓存，直接复用
# - 如果没有缓存，会启动半自动登录流程
driver = handler.semi_auto_login()

if driver:
    # ✅ 已登录状态，可以执行业务测试
    driver.get("https://globalwk-h5.kkty1.com/some/page")
    
    # 执行测试操作...
    
    # 测试完成后关闭（可选）
    # handler.close()
else:
    print("登录失败")
```

### 方式二：在 pytest 中使用

```python
# tests/test_my_feature.py
import pytest
from src.login.login_handler import LoginHandler

class TestMyFeature:
    
    @pytest.fixture(scope="class")
    def logged_in_driver(self):
        """提供已登录的浏览器实例"""
        handler = LoginHandler()
        driver = handler.semi_auto_login()
        
        if not driver:
            pytest.fail("登录失败，无法继续测试")
        
        yield driver
        
        # 测试完成后不关闭浏览器（保留缓存）
        # handler.close()
    
    def test_check_balance(self, logged_in_driver):
        """测试：检查余额显示"""
        driver = logged_in_driver
        
        # 已经是登录状态，直接操作
        balance = driver.find_element("css selector", "[class*='balance']")
        assert balance.is_displayed()
    
    def test_navigate_to_game(self, logged_in_driver):
        """测试：进入游戏页面"""
        driver = logged_in_driver
        driver.get("https://globalwk-h5.kkty1.com/game")
        # ...
```

### 方式三：创建通用的测试基类

```python
# src/tests/base_test.py
from src.login.login_handler import LoginHandler
from selenium import webdriver

class BaseTest:
    """测试基类，提供已登录的浏览器"""
    
    driver: webdriver.Chrome = None
    handler: LoginHandler = None
    
    @classmethod
    def setup_class(cls):
        """测试类开始前：获取已登录的浏览器"""
        cls.handler = LoginHandler()
        cls.driver = cls.handler.semi_auto_login()
        
        if not cls.driver:
            raise Exception("登录失败")
    
    @classmethod
    def teardown_class(cls):
        """测试类结束后：可选关闭浏览器"""
        # 保持浏览器打开以复用缓存
        pass


# 使用示例
class TestUserProfile(BaseTest):
    
    def test_view_profile(self):
        """测试：查看用户资料"""
        self.driver.get("https://globalwk-h5.kkty1.com/profile")
        # ...
    
    def test_edit_nickname(self):
        """测试：修改昵称"""
        # self.driver 已经是登录状态
        # ...
```

---

## 📁 项目结构

```
h5_auto/
├── config/
│   ├── config.yaml              # 主配置文件（站点、账号等）
│   └── selectors/               # 页面选择器配置
│       ├── default.yaml         # 默认选择器
│       ├── 286.yaml             # 286站点特有选择器
│       ├── 231.yaml             # 231站点特有选择器
│       ├── 1PG.yaml             # 1PG站点特有选择器
│       └── g66.yaml             # g66站点特有选择器
│
├── src/
│   ├── core/
│   │   ├── browser_manager.py   # 浏览器管理器
│   │   ├── cache_manager.py     # 缓存管理器
│   │   └── base_page.py         # 页面基类
│   │
│   ├── login/
│   │   ├── login_handler.py     # 登录处理器
│   │   └── login_page.py        # 登录页面对象
│   │
│   ├── pages/                   # 业务页面对象
│   │   ├── deposit_page.py      # 存款页面
│   │   ├── agent_page.py        # 代理中心页面
│   │   ├── sports_page.py       # 体育页面
│   │   └── activity_page.py     # 活动/赚钱页面
│   │
│   ├── tests/                   # 测试用例
│   │   ├── test_deposit.py      # 存款功能测试
│   │   ├── test_agent.py        # 代理中心测试
│   │   ├── test_sports.py       # 体育下注测试
│   │   └── test_activity.py     # 活动页面测试
│   │
│   └── utils/
│       ├── config_loader.py     # 配置加载器（支持多站点）
│       ├── constants.py         # 常量定义
│       └── logger.py            # 日志工具
│
├── cache/                       # 缓存目录（自动生成）
├── logs/                        # 日志目录
├── main.py                      # 主入口
├── requirements.txt             # 依赖包
└── README.md                    # 本文档
```

## 🧪 测试模块说明

| 模块 | 说明 | 验证内容 |
|------|------|----------|
| deposit | 存款功能 | 导航到存款页、选择支付方式、输入金额 |
| agent | 代理中心 | 导航到代理页、获取邀请码、推广链接 |
| sports | 体育下注 | 导航到体育页、选择赛事、选择赔率 |
| activity | 活动/赚钱 | 导航到活动页、查看活动列表、进入详情 |

## 🔧 选择器配置

如果某个站点的页面结构与默认不同，可以在对应的配置文件中覆盖选择器：

```yaml
# config/selectors/286.yaml
deposit:
  entry: ".my-custom-deposit-btn"
  amount_input: "#custom-amount-input"
```

---

## ⚙️ 配置说明

编辑 `config/config.yaml`：

```yaml
# 应用配置
app:
  base_url: "https://globalwk-h5.kkty1.com/"
  login_url: "https://globalwk-h5.kkty1.com/"

# 账号配置（可以修改为其他账号）
account:
  username: "honer001"
  password: "Aa123456"

# 浏览器配置
browser:
  headless: false              # 是否无头模式
  mobile_emulation: true       # 移动端模拟

# 登录配置
login:
  timeout: 300                 # 等待手动验证的超时时间（秒）

# 缓存配置
cache:
  enabled: true
  expire_hours: 24             # 缓存过期时间（小时）
```

---

## 🔑 核心API

### LoginHandler

| 方法 | 说明 |
|------|------|
| `semi_auto_login()` | 半自动登录，返回已登录的 WebDriver |
| `get_driver()` | 获取当前 WebDriver 实例 |
| `close()` | 关闭浏览器 |
| `clear_cache()` | 清除会话缓存 |

### 使用示例

```python
from src.login.login_handler import LoginHandler

# 创建处理器
handler = LoginHandler(
    username="test_user",      # 可选，默认读取配置
    password="test_pass",      # 可选，默认读取配置
    session_name="my_session", # 可选，用于多账号隔离
    cache_enabled=True         # 可选，是否启用缓存
)

# 登录并获取driver
driver = handler.semi_auto_login()

# 使用driver进行测试...

# 清除缓存（如果需要重新登录）
handler.clear_cache()
```

---

## 🔄 多账号支持

使用不同的 `session_name` 隔离多个账号：

```python
# 账号1
handler1 = LoginHandler(
    username="user1",
    password="pass1",
    session_name="account_1"
)
driver1 = handler1.semi_auto_login()

# 账号2
handler2 = LoginHandler(
    username="user2", 
    password="pass2",
    session_name="account_2"
)
driver2 = handler2.semi_auto_login()
```

---

## ❓ 常见问题

### Q: 缓存失效了怎么办？
```bash
# 清除缓存，重新登录
rm -rf cache/user_session
python main.py
```

### Q: 如何强制重新登录？
```python
handler = LoginHandler()
handler.clear_cache()  # 清除缓存
driver = handler.semi_auto_login()  # 重新登录
```

### Q: 浏览器启动失败？
确保没有其他程序占用 Chrome 用户数据目录：
```bash
pkill -f chromedriver
rm -rf cache/user_session/default/browser_data
```

### Q: 登录检测不到成功？
本框架通过检测**余额元素**判断登录成功。如果页面变化，需要修改：
```python
# src/core/browser_manager.py 中的 success_selectors
success_selectors = [
    "[class*='balance']",
    "[class*='wallet']",
    # 添加新的选择器...
]
```

---

## 📝 开发新测试用例的步骤

1. **确保有有效缓存**（或首次运行时手动滑动验证码）

2. **在 `src/tests/` 创建测试文件**：
```python
# src/tests/test_my_feature.py
from src.login.login_handler import LoginHandler

def test_my_feature():
    handler = LoginHandler()
    driver = handler.semi_auto_login()
    
    # 测试代码...
    driver.get("https://...")
    assert "expected" in driver.page_source
```

3. **运行测试**：
```bash
pytest src/tests/test_my_feature.py -v
```

---

## 📌 注意事项

1. **`cache/` 目录已加入 `.gitignore`**，不会提交到git
2. **同一个缓存目录不能被多个浏览器同时使用**
3. **缓存默认24小时过期**，可在配置中修改
4. **首次运行需要手动滑动验证码**，后续运行自动复用

---

**Happy Testing! 🎉**
