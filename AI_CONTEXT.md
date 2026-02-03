# AI开发上下文文档 - Selenium H5自动化

> 本文档供AI助手理解项目结构和开发规范

## 项目概述

| 属性 | 值 |
|------|-----|
| 项目名称 | h5_auto |
| 项目路径 | /Users/lank/Desktop/h5_auto |
| 测试类型 | 移动端H5页面自动化 |
| 技术栈 | Python + Selenium + Chrome |
| 目标网站 | https://globalwk-h5.kkty1.com/ |

## 核心设计思想

**半自动登录 + 缓存复用**：
1. 首次登录：自动输入账号密码 → 人工处理滑块验证码 → 保存会话
2. 后续运行：加载缓存 → 跳过登录 → 直接执行测试

## 项目结构

```
h5_auto/
├── config/config.yaml       # 配置文件（账号、URL、选择器等）
├── src/
│   ├── core/
│   │   ├── browser_manager.py   # 浏览器管理（创建driver、等待登录）
│   │   ├── cache_manager.py     # 缓存管理（保存/加载session）
│   │   └── base_page.py         # 页面基类（通用操作）
│   ├── login/
│   │   ├── login_handler.py     # 【核心入口】登录处理器
│   │   └── login_page.py        # 登录页面对象
│   ├── tests/                   # 测试用例目录
│   └── utils/
│       ├── config_loader.py     # 配置加载器
│       ├── constants.py         # 常量定义
│       └── logger.py            # 日志工具
├── cache/user_session/          # 会话缓存（gitignore）
├── main.py                      # 主入口
└── requirements.txt             # 依赖包
```

## 核心类和方法

### 1. LoginHandler（登录处理器）- 最常用

```python
from src.login.login_handler import LoginHandler

# 获取已登录的浏览器
handler = LoginHandler()
driver = handler.semi_auto_login()

# driver 就是 Selenium WebDriver，可以直接操作
driver.get("https://xxx")
driver.find_element(By.CSS_SELECTOR, ".xxx").click()
```

### 2. BrowserManager（浏览器管理器）

- `create_driver(user_data_dir)`: 创建Chrome浏览器
- `wait_for_manual_login(driver)`: 等待手动登录完成
- `is_session_valid(driver)`: 检查会话是否有效

### 3. CacheManager（缓存管理器）

- `save_session(driver, session_name)`: 保存会话
- `load_session(driver, session_name)`: 加载会话
- `get_cache_status(session_name)`: 获取缓存状态

## 登录成功检测方式

**重要**：该网站登录成功后URL不变，token不在localStorage中。

检测方式（按优先级）：
1. ✅ 余额元素出现：`[class*='balance']`
2. ✅ 登录按钮消失：`.login-btn`

相关代码位置：
- `src/core/browser_manager.py` → `wait_for_manual_login()`
- `src/login/login_handler.py` → `_verify_login_success()`

## 配置文件说明

`config/config.yaml` 关键配置：

```yaml
app:
  base_url: "https://globalwk-h5.kkty1.com/"
  login_url: "https://globalwk-h5.kkty1.com/"

account:
  username: "honer001"
  password: "Aa123456"

browser:
  headless: false
  mobile_emulation: true

login:
  timeout: 300  # 等待手动验证超时

cache:
  enabled: true
  expire_hours: 24
```

## 开发新测试用例

### 方式1：简单脚本

```python
from src.login.login_handler import LoginHandler
from selenium.webdriver.common.by import By

handler = LoginHandler()
driver = handler.semi_auto_login()

# 测试代码
driver.get("https://globalwk-h5.kkty1.com/some/page")
element = driver.find_element(By.CSS_SELECTOR, ".some-class")
assert element.is_displayed()
```

### 方式2：pytest测试类

```python
# src/tests/test_xxx.py
import pytest
from src.login.login_handler import LoginHandler

class TestXxx:
    @pytest.fixture(scope="class")
    def driver(self):
        handler = LoginHandler()
        return handler.semi_auto_login()
    
    def test_something(self, driver):
        driver.get("https://...")
        # 断言...
```

## 常见问题

### Q: 缓存失效怎么办？
```bash
rm -rf cache/user_session
python main.py  # 重新登录
```

### Q: 如何修改登录成功检测？
修改 `src/core/browser_manager.py` 中的 `success_selectors` 列表

### Q: 如何添加新的页面对象？
1. 在 `src/` 下创建新目录（如 `src/game/`）
2. 创建页面类继承 `BasePage`
3. 使用 `self.driver` 操作元素

## 运行命令

```bash
cd /Users/lank/Desktop/h5_auto
source .venv/bin/activate

# 运行主程序
python main.py

# 运行测试
pytest src/tests/ -v
```

## 依赖版本

- Python 3.9+
- selenium==4.15.2
- webdriver-manager==4.0.1
- PyYAML==6.0.1
- pytest==7.4.3
