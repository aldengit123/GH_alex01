"""
常量定义
"""

# 支持的站点标识
class SiteCode:
    SITE_286 = "286"
    SITE_231 = "231"
    SITE_1PG = "1PG"
    SITE_G66 = "g66"
    
    ALL_SITES = [SITE_286, SITE_231, SITE_1PG, SITE_G66]


# 登录状态
class LoginStatus:
    NOT_LOGGED_IN = "not_logged_in"
    LOGGING_IN = "logging_in"
    WAITING_CAPTCHA = "waiting_captcha"
    LOGGED_IN = "logged_in"
    LOGIN_FAILED = "login_failed"


# 缓存状态
class CacheStatus:
    NOT_FOUND = "not_found"
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"


# 默认超时时间（秒）
DEFAULT_TIMEOUT = 10
MANUAL_LOGIN_TIMEOUT = 300
CHECK_INTERVAL = 2

# 文件名
COOKIES_FILE = "cookies.json"
STORAGE_FILE = "storage.json"
SESSION_INFO_FILE = "session_info.json"
