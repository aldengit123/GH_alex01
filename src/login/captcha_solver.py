"""
滑块验证码自动处理模块
使用 AntiCAP 进行缺口位置识别
"""
import base64
import time
import random
from typing import Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ..utils.logger import get_logger


class CaptchaSolver:
    """滑块验证码自动处理器"""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.logger = get_logger("CaptchaSolver")
        self.handler = None
        self.captured_images = []  # 存储抓取的图片
        self._init_anticap()
        self._enable_network_capture()
    
    def _init_anticap(self):
        """初始化AntiCAP"""
        try:
            from AntiCAP import Handler
            self.handler = Handler(show_banner=False)
            self.logger.info("AntiCAP 初始化成功")
        except Exception as e:
            self.logger.warning(f"AntiCAP 初始化失败: {e}")
            self.handler = None
    
    def _enable_network_capture(self):
        """启用网络请求捕获"""
        try:
            # 启用CDP网络监听
            self.driver.execute_cdp_cmd('Network.enable', {})
            self.logger.debug("网络请求捕获已启用")
        except Exception as e:
            self.logger.debug(f"启用网络捕获失败: {e}")
    
    def _capture_captcha_from_network(self) -> Tuple[Optional[str], Optional[str]]:
        """从网络请求中捕获验证码图片"""
        try:
            # 直接从DOM获取botion验证码的图片URL（更准确）
            js_get_botion_images = """
            var result = {bg: null, slice: null};
            
            // 查找botion验证码的背景图和滑块图
            var bgEl = document.querySelector('[class*="botion_bg"]');
            var sliceEl = document.querySelector('[class*="botion_slice_bg"]');
            
            if (bgEl) {
                var bgStyle = bgEl.style.backgroundImage || '';
                var bgMatch = bgStyle.match(/url\\(['"]*([^'"\\)]+)['"]*\\)/);
                if (bgMatch) result.bg = bgMatch[1];
            }
            
            if (sliceEl) {
                var sliceStyle = sliceEl.style.backgroundImage || '';
                var sliceMatch = sliceStyle.match(/url\\(['"]*([^'"\\)]+)['"]*\\)/);
                if (sliceMatch) result.slice = sliceMatch[1];
            }
            
            return result;
            """
            
            botion_result = self.driver.execute_script(js_get_botion_images)
            
            if botion_result and (botion_result.get('bg') or botion_result.get('slice')):
                self.logger.info("从botion DOM获取验证码图片URL")
                bg_base64 = None
                slice_base64 = None
                
                import requests
                
                # 添加缓存绕过参数
                cache_buster = f"_t={int(time.time() * 1000)}"
                
                if botion_result.get('bg'):
                    try:
                        bg_url = botion_result['bg']
                        # 添加缓存绕过
                        if '?' in bg_url:
                            bg_url = f"{bg_url}&{cache_buster}"
                        else:
                            bg_url = f"{bg_url}?{cache_buster}"
                        resp = requests.get(bg_url, timeout=5, headers={'Cache-Control': 'no-cache'})
                        if resp.status_code == 200:
                            bg_base64 = base64.b64encode(resp.content).decode()
                            self.logger.info(f"获取背景图成功 ({len(resp.content)} bytes)")
                    except Exception as e:
                        self.logger.debug(f"下载背景图失败: {e}")
                
                if botion_result.get('slice'):
                    try:
                        slice_url = botion_result['slice']
                        if '?' in slice_url:
                            slice_url = f"{slice_url}&{cache_buster}"
                        else:
                            slice_url = f"{slice_url}?{cache_buster}"
                        resp = requests.get(slice_url, timeout=5, headers={'Cache-Control': 'no-cache'})
                        if resp.status_code == 200:
                            slice_base64 = base64.b64encode(resp.content).decode()
                            self.logger.info(f"获取滑块图成功 ({len(resp.content)} bytes)")
                    except Exception as e:
                        self.logger.debug(f"下载滑块图失败: {e}")
                
                if bg_base64 and slice_base64:
                    return bg_base64, slice_base64
            
            # 回退到Performance API
            js_get_requests = """
            var entries = performance.getEntriesByType('resource');
            var images = [];
            for (var i = 0; i < entries.length; i++) {
                var url = entries[i].name.toLowerCase();
                if ((url.includes('captcha') || url.includes('verify') || 
                     url.includes('slider') || url.includes('jigsaw') ||
                     url.includes('puzzle') || url.includes('slide')) &&
                    (url.includes('.png') || url.includes('.jpg') || 
                     url.includes('.jpeg') || url.includes('.webp') ||
                     url.includes('image') || url.includes('pic'))) {
                    images.push(entries[i].name);
                }
            }
            return images;
            """
            
            image_urls = self.driver.execute_script(js_get_requests)
            
            if image_urls:
                self.logger.info(f"从网络请求捕获到 {len(image_urls)} 个验证码相关图片")
                for url in image_urls:
                    self.logger.debug(f"  - {url}")
                
                # 下载图片
                import requests
                bg_base64 = None
                slice_base64 = None
                
                for url in image_urls:
                    try:
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            img_base64 = base64.b64encode(resp.content).decode()
                            img_size = len(resp.content)
                            
                            # 根据大小判断是背景还是滑块
                            # 背景图通常更大
                            if img_size > 10000 and not bg_base64:
                                bg_base64 = img_base64
                                self.logger.info(f"捕获背景图: {url[:80]}... ({img_size} bytes)")
                            elif img_size > 1000 and not slice_base64:
                                slice_base64 = img_base64
                                self.logger.info(f"捕获滑块图: {url[:80]}... ({img_size} bytes)")
                    except Exception as e:
                        self.logger.debug(f"下载图片失败: {e}")
                
                return bg_base64, slice_base64
            
            return None, None
            
        except Exception as e:
            self.logger.debug(f"网络捕获失败: {e}")
            return None, None
    
    def calibrate_offset(self) -> None:
        """
        校准模式：分析验证码但不滑动，让人工操作后捕获实际滑动距离
        用于计算准确的偏移量
        """
        self.logger.info("=" * 50)
        self.logger.info("🔧 进入校准模式")
        self.logger.info("=" * 50)
        
        try:
            # 等待验证码出现
            if not self._wait_for_captcha(timeout=10):
                self.logger.warning("未检测到验证码")
                return
            
            # 清除之前的网络日志
            try:
                self.driver.get_log('performance')
            except:
                pass
            
            # 获取验证码图片并计算距离
            bg_base64, slice_base64 = self._capture_captcha_from_network()
            if not bg_base64 or not slice_base64:
                bg_base64, slice_base64 = self._get_captcha_images()
            
            if not bg_base64:
                self.logger.error("无法获取验证码图片")
                return
            
            # 保存图片
            self._save_captcha_images(bg_base64, slice_base64)
            
            # 计算距离
            distance = self._calculate_distance(bg_base64, slice_base64)
            if not distance:
                self.logger.error("无法计算滑块距离")
                return
            
            # 获取显示尺寸
            js_get_dims = """
            var result = {bgWidth: 280, naturalWidth: 340};
            var bgEl = document.querySelector('[class*="botion_bg"]');
            if (bgEl) result.bgWidth = bgEl.offsetWidth || 280;
            return result;
            """
            dims = self.driver.execute_script(js_get_dims)
            bg_width = dims.get('bgWidth', 280)
            natural_width = 340
            scale = bg_width / natural_width
            
            # 计算预期滑动距离（不含补偿）
            expected_distance = int(distance * scale)
            
            self.logger.info(f"\n📊 计算结果:")
            self.logger.info(f"  原图缺口位置: {distance}px")
            self.logger.info(f"  显示宽度: {bg_width}px, 缩放比: {scale:.3f}")
            self.logger.info(f"  预期滑动距离(无补偿): {expected_distance}px")
            
            self.logger.info("\n👉 请手动滑动验证码完成验证...")
            self.logger.info("   系统将从网络请求捕获实际滑动距离\n")
            
            # 等待人工操作完成（最多60秒）
            actual_distance = None
            for i in range(120):
                time.sleep(0.5)
                
                # 尝试从网络请求获取滑动距离
                result = self._get_slide_distance_from_network()
                if result:
                    actual_distance = result
                    self.logger.info(f"✅ 从网络请求捕获到滑动距离: {actual_distance}px")
                    break
                
                # 检查验证码是否消失
                if not self._wait_for_captcha(timeout=0.3):
                    self.logger.info("验证码已消失")
                    # 最后再检查一次网络请求
                    time.sleep(0.5)
                    result = self._get_slide_distance_from_network()
                    if result:
                        actual_distance = result
                    break
            else:
                self.logger.warning("等待超时")
            
            if actual_distance:
                offset = actual_distance - expected_distance
                offset_percent = (offset / bg_width) * 100
                
                self.logger.info(f"\n" + "=" * 50)
                self.logger.info(f"📈 校准结果:")
                self.logger.info(f"=" * 50)
                self.logger.info(f"  原图缺口位置: {distance}px")
                self.logger.info(f"  预期距离(无补偿): {expected_distance}px")
                self.logger.info(f"  实际滑动距离: {actual_distance}px")
                self.logger.info(f"  偏移量: {offset}px")
                self.logger.info(f"  偏移百分比: {offset_percent:.2f}%")
                self.logger.info(f"\n💡 建议: 将补偿值设为显示宽度的 {offset_percent:.1f}%")
                self.logger.info(f"   即 base_offset = bg_width * {offset_percent/100:.3f}")
            else:
                self.logger.warning("未能自动捕获滑动距离，打印所有网络请求...")
                self._dump_all_network_requests()
                self.logger.info("\n请查看上方网络请求，找到包含滑动距离的请求")
                
        except Exception as e:
            self.logger.error(f"校准失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_slide_distance_from_network(self, debug: bool = False) -> Optional[int]:
        """从网络请求中获取滑动距离"""
        try:
            import json
            import re
            
            logs = self.driver.get_log('performance')
            
            if debug and logs:
                self.logger.info(f"  [调试] 获取到 {len(logs)} 条日志")
            
            for log in reversed(logs):
                try:
                    message = json.loads(log.get('message', '{}'))
                    msg = message.get('message', {})
                    method = msg.get('method', '')
                    
                    # 查找Network请求事件
                    if method in ['Network.requestWillBeSent', 'Network.responseReceived']:
                        params = msg.get('params', {})
                        request = params.get('request', {})
                        url = request.get('url', '') or params.get('response', {}).get('url', '')
                        post_data = request.get('postData', '')
                        
                        # 打印所有POST请求用于调试
                        if debug and post_data:
                            self.logger.info(f"  [POST] {url[:80]}")
                            self.logger.info(f"         data: {post_data[:200]}")
                        
                        # 检查是否包含滑动相关数据
                        data_to_check = post_data + url
                        
                        # 查找各种可能的距离字段模式
                        patterns = [
                            r'"x"\s*:\s*(\d+)',
                            r'"distance"\s*:\s*(\d+)',
                            r'"slide"\s*:\s*(\d+)',
                            r'"offset"\s*:\s*(\d+)',
                            r'"left"\s*:\s*(\d+)',
                            r'"moveX"\s*:\s*(\d+)',
                            r'"dragX"\s*:\s*(\d+)',
                            r'[&?]x=(\d+)',
                            r'[&?]distance=(\d+)',
                            r'[&?]offset=(\d+)',
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, data_to_check)
                            if match:
                                val = int(match.group(1))
                                if 10 < val < 300:
                                    if debug:
                                        self.logger.info(f"  [匹配] pattern={pattern}, value={val}")
                                    return val
                                    
                except Exception as e:
                    if debug:
                        self.logger.debug(f"解析日志失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.debug(f"获取网络日志失败: {e}")
        
        return None
    
    def calibrate_offset_with_cdp(self) -> None:
        """
        使用CDP监听网络请求的校准模式
        """
        self.logger.info("=" * 50)
        self.logger.info("🔧 进入校准模式 (CDP)")
        self.logger.info("=" * 50)
        
        try:
            # 保存当前页面截图
            self._save_debug_screenshot("calibrate_page")
            
            # 等待验证码出现（延长等待时间）
            self.logger.info("等待验证码出现...")
            if not self._wait_for_captcha(timeout=15):
                self.logger.warning("未检测到验证码，保存截图...")
                self._save_debug_screenshot("no_captcha")
                return
            
            # 获取验证码图片并计算距离
            bg_base64, slice_base64 = self._capture_captcha_from_network()
            if not bg_base64 or not slice_base64:
                bg_base64, slice_base64 = self._get_captcha_images()
            
            if not bg_base64:
                self.logger.error("无法获取验证码图片")
                return
            
            # 保存图片
            self._save_captcha_images(bg_base64, slice_base64)
            
            # 计算距离
            distance = self._calculate_distance(bg_base64, slice_base64)
            if not distance:
                self.logger.error("无法计算滑块距离")
                return
            
            # 获取显示尺寸
            js_get_dims = """
            var result = {bgWidth: 280, naturalWidth: 340};
            var bgEl = document.querySelector('[class*="botion_bg"]');
            if (bgEl) result.bgWidth = bgEl.offsetWidth || 280;
            return result;
            """
            dims = self.driver.execute_script(js_get_dims)
            bg_width = dims.get('bgWidth', 280)
            natural_width = 340
            scale = bg_width / natural_width
            
            # 计算预期滑动距离（不含补偿）
            expected_distance = int(distance * scale)
            
            self.logger.info(f"\n📊 计算结果:")
            self.logger.info(f"  原图缺口位置: {distance}px")
            self.logger.info(f"  显示宽度: {bg_width}px, 缩放比: {scale:.3f}")
            self.logger.info(f"  预期滑动距离(无补偿): {expected_distance}px")
            
            self.logger.info("\n👉 请手动滑动验证码完成验证...")
            self.logger.info("   系统将实时监测滑块位置\n")
            
            # 等待验证码完全显示
            time.sleep(1)
            
            # 截图看看当前状态
            self._save_debug_screenshot("calibrate_start")
            
            # 获取滑块并高亮显示
            initial_btn_x = self._get_slider_btn_x()
            slider_btn = self._find_and_highlight_slider()
            
            if slider_btn:
                initial_btn_x = slider_btn.rect['x']
                self.logger.info(f"  ✅ 找到滑块并已高亮，初始位置: x={initial_btn_x:.1f}px")
            else:
                self.logger.warning("  ⚠️ 未找到滑块元素")
            
            # 等待人工操作完成
            actual_distance = None
            max_moved = 0
            last_log_moved = 0
            
            for i in range(120):
                time.sleep(0.2)
                
                # 检测滑块位置
                current_btn_x = self._get_slider_btn_x()
                if current_btn_x and initial_btn_x:
                    moved = current_btn_x - initial_btn_x
                    if moved > max_moved:
                        max_moved = moved
                    # 只在移动超过5px时打印
                    if abs(moved - last_log_moved) > 5 and moved > 5:
                        self.logger.info(f"  滑块位移: {moved:.0f}px")
                        last_log_moved = moved
                
                # 检查验证码是否消失（表示验证完成）
                if not self._wait_for_captcha(timeout=0.2):
                    self.logger.info("✅ 验证码已消失，验证完成！")
                    actual_distance = max_moved
                    break
            else:
                self.logger.warning("等待超时")
                if max_moved > 10:
                    actual_distance = max_moved
            
            if actual_distance:
                offset = actual_distance - expected_distance
                offset_percent = (offset / bg_width) * 100
                
                self.logger.info(f"\n" + "=" * 50)
                self.logger.info(f"📈 校准结果:")
                self.logger.info(f"=" * 50)
                self.logger.info(f"  原图缺口位置: {distance}px")
                self.logger.info(f"  预期距离(无补偿): {expected_distance}px")
                self.logger.info(f"  实际滑动距离: {actual_distance}px")
                self.logger.info(f"  偏移量: {offset}px")
                self.logger.info(f"  偏移百分比: {offset_percent:.2f}%")
                self.logger.info(f"\n💡 建议: 将补偿值设为显示宽度的 {offset_percent:.1f}%")
            else:
                self.logger.warning("无法获取实际滑动距离")
                
        except Exception as e:
            self.logger.error(f"校准失败: {e}")
            import traceback
            traceback.print_exc()

    def _dump_all_network_requests(self):
        """打印所有网络请求用于调试"""
        try:
            import json
            logs = self.driver.get_log('performance')
            
            self.logger.info(f"\n📡 网络请求日志 (共{len(logs)}条):")
            
            count = 0
            for log in logs:
                try:
                    message = json.loads(log.get('message', '{}'))
                    msg = message.get('message', {})
                    method = msg.get('method', '')
                    
                    if method == 'Network.requestWillBeSent':
                        params = msg.get('params', {})
                        request = params.get('request', {})
                        url = request.get('url', '')
                        req_method = request.get('method', 'GET')
                        post_data = request.get('postData', '')
                        
                        # 只显示非资源请求
                        if not any(ext in url for ext in ['.png', '.jpg', '.gif', '.css', '.js', '.woff']):
                            count += 1
                            self.logger.info(f"\n  [{count}] {req_method} {url[:100]}")
                            if post_data:
                                self.logger.info(f"      POST: {post_data[:300]}")
                except:
                    continue
                    
            self.logger.info(f"\n  共 {count} 个API请求")
            
        except Exception as e:
            self.logger.error(f"打印网络请求失败: {e}")
    
    def _get_slider_btn_x(self) -> Optional[float]:
        """获取滑块按钮的X坐标"""
        try:
            selectors = [
                ".botion_track .botion_btn",
                "[class*='botion_btn']",
                "[class*='slider_btn']",
                "[class*='slide-btn']",
            ]
            for selector in selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn and btn.is_displayed():
                        return btn.rect['x']
                except:
                    continue
        except:
            pass
        return None
    
    def _find_and_highlight_slider(self):
        """查找滑块并用红框高亮"""
        try:
            # botion滑块的特定选择器
            selectors = [
                "[class*='botion_btn']",
                ".botion_track .botion_btn",
                "[class*='botion'] [class*='btn']",
                "[class*='captcha'] [class*='slider']",
                "[class*='slider_btn']",
                "[class*='slide-btn']",
                "[class*='drag-btn']",
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in elements:
                        if btn and btn.is_displayed():
                            rect = btn.rect
                            # 滑块按钮通常较小
                            if 20 < rect['width'] < 80 and 20 < rect['height'] < 80:
                                # 用红框高亮
                                self.driver.execute_script("""
                                    arguments[0].style.outline = '3px solid red';
                                    arguments[0].style.outlineOffset = '2px';
                                    arguments[0].style.boxShadow = '0 0 10px red';
                                """, btn)
                                self.logger.info(f"  找到滑块: {selector}, 尺寸: {rect['width']:.0f}x{rect['height']:.0f}")
                                return btn
                except:
                    continue
            
            # 用JS在botion容器内查找
            js_find_botion = """
            // 查找botion验证码内的滑块 - 查找track内的按钮
            var track = document.querySelector('[class*="botion_track"]');
            if (track) {
                var btn = track.querySelector('[class*="btn"]');
                if (btn) {
                    var rect = btn.getBoundingClientRect();
                    btn.style.outline = '3px solid red';
                    btn.style.boxShadow = '0 0 10px red';
                    return {
                        found: true,
                        className: btn.className,
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    };
                }
            }
            
            // 直接查找botion_btn
            var allBtns = document.querySelectorAll('[class*="botion_btn"]');
            for (var i = 0; i < allBtns.length; i++) {
                var btn = allBtns[i];
                var rect = btn.getBoundingClientRect();
                if (rect.width > 0) {
                    btn.style.outline = '3px solid red';
                    btn.style.boxShadow = '0 0 10px red';
                    return {
                        found: true,
                        className: btn.className,
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    };
                }
            }
            
            // 查找所有botion元素并显示可见性信息
            var all = document.querySelectorAll('[class*="botion"]');
            var info = [];
            for (var i = 0; i < all.length; i++) {
                var el = all[i];
                var rect = el.getBoundingClientRect();
                var style = window.getComputedStyle(el);
                info.push({
                    className: el.className.substring(0, 60),
                    width: rect.width,
                    height: rect.height,
                    display: style.display,
                    visibility: style.visibility
                });
                if (el.className.indexOf('btn') > -1) {
                    el.style.outline = '2px dashed orange';
                }
            }
            return {found: false, elements: info};
            """
            result = self.driver.execute_script(js_find_botion)
            
            if result and result.get('found'):
                self.logger.info(f"  JS找到滑块: {result.get('className', '')[:50]}")
                # 重新获取元素
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, f".{result['className'].split()[0]}")
                    return btn
                except:
                    pass
            elif result and result.get('elements'):
                self.logger.info(f"  botion元素列表:")
                for el in result['elements'][:8]:
                    self.logger.info(f"    - {el['className']} ({el['width']:.0f}x{el['height']:.0f})")
            
            return None
        except Exception as e:
            self.logger.debug(f"查找滑块失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_actual_distance_from_request(self) -> Optional[float]:
        """尝试从网络请求中获取实际滑动距离"""
        try:
            # 获取性能日志
            logs = self.driver.get_log('performance')
            for log in reversed(logs):
                message = log.get('message', '')
                if 'botion' in message.lower() and ('verify' in message.lower() or 'check' in message.lower()):
                    self.logger.debug(f"Found request: {message[:200]}")
                    # 解析请求中的距离参数
                    import re
                    match = re.search(r'"x"\s*:\s*(\d+)', message)
                    if match:
                        return float(match.group(1))
        except Exception as e:
            self.logger.debug(f"获取请求失败: {e}")
        return None

    def solve_slider_captcha(self, max_retries: int = 5) -> bool:
        """
        自动处理滑块验证码（支持重试）
        
        Args:
            max_retries: 最大重试次数
        
        Returns:
            True 如果成功处理，False 否则
        """
        if not self.handler:
            self.logger.warning("AntiCAP 未初始化，无法自动处理验证码")
            return False
        
        try:
            # 1. 等待验证码出现
            if not self._wait_for_captcha():
                self.logger.info("未检测到验证码")
                return True  # 没有验证码也算成功
            
            self.logger.info("检测到滑块验证码，开始处理...")
            
            for attempt in range(max_retries):
                self.logger.info(f"--- 第 {attempt + 1}/{max_retries} 次尝试 ---")
                
                # 等待验证码图片加载（失败后图片会更换）
                time.sleep(1)
                
                # 清除之前的网络请求缓存，获取新图片
                success = self._single_attempt()
                
                if success:
                    return True
                
                # 检查验证码是否还存在（可能已经成功或被关闭）
                if not self._wait_for_captcha(timeout=2):
                    self.logger.info("验证码已消失，可能已成功")
                    return True
                
                # 等待新图片自动加载
                self.logger.info("等待新验证码图片加载...")
                old_bg_url = self._get_current_bg_url()
                for wait_i in range(10):
                    time.sleep(0.5)
                    new_bg_url = self._get_current_bg_url()
                    if new_bg_url and old_bg_url and new_bg_url != old_bg_url:
                        self.logger.info("检测到新验证码图片")
                        time.sleep(0.3)
                        break
                else:
                    self.logger.debug("等待新图片超时，继续重试")
            
            self.logger.warning(f"已尝试 {max_retries} 次，验证码处理失败")
            return False
            
        except Exception as e:
            self.logger.error(f"处理验证码失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _single_attempt(self) -> bool:
        """单次验证码处理尝试"""
        try:
            # 获取验证码图片（优先从网络请求抓取）
            background_base64, target_base64 = self._capture_captcha_from_network()
            
            # 如果网络抓取失败，尝试DOM获取
            if not background_base64 or not target_base64:
                self.logger.info("网络抓取未找到，尝试DOM获取...")
                bg2, target2 = self._get_captcha_images()
                background_base64 = background_base64 or bg2
                target_base64 = target_base64 or target2
            
            if not background_base64 or not target_base64:
                self.logger.warning("无法获取验证码图片")
                return False
            
            # 保存图片用于调试分析
            self._save_captcha_images(background_base64, target_base64)
            
            # 计算滑块位置
            distance = self._calculate_distance(target_base64, background_base64)
            if distance <= 0:
                self.logger.warning("无法计算滑块距离")
                return False
            
            self.logger.info(f"计算得到滑块距离: {distance}px")
            
            # 执行滑动
            return self._perform_slide(distance)
            
        except Exception as e:
            self.logger.error(f"单次尝试失败: {e}")
            return False
    
    def _refresh_captcha(self):
        """点击刷新按钮获取新验证码"""
        try:
            # 先获取当前背景图URL
            old_bg_url = self._get_current_bg_url()
            
            # 查找刷新按钮（botion验证码的刷新按钮通常是第二个svg图标）
            refresh_selectors = [
                "[class*='botion_refresh']",
                "[class*='botion_icons'] svg:last-child",  # botion图标区域的最后一个svg
                "[class*='botion_icons'] > *:last-child",  # 图标区域的最后一个子元素
                "[class*='captcha'] svg[class*='refresh']",
                "[class*='refresh']",
                ".captcha-refresh",
            ]
            
            clicked = False
            for selector in refresh_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn and btn.is_displayed():
                        btn.click()
                        self.logger.info("点击刷新按钮")
                        clicked = True
                        break
                except:
                    continue
            
            # 等待新图片加载（URL变化）
            if old_bg_url:
                for _ in range(10):  # 最多等待2秒
                    time.sleep(0.2)
                    new_bg_url = self._get_current_bg_url()
                    if new_bg_url and new_bg_url != old_bg_url:
                        self.logger.info("检测到新验证码图片")
                        return
                self.logger.debug("等待新图片超时")
            else:
                time.sleep(0.5)
                
        except Exception as e:
            self.logger.debug(f"刷新验证码失败: {e}")
    
    def _get_current_bg_url(self) -> Optional[str]:
        """获取当前验证码背景图URL"""
        try:
            js = """
            var bgEl = document.querySelector('[class*="botion_bg"]');
            if (bgEl) {
                var bgStyle = bgEl.style.backgroundImage || '';
                var match = bgStyle.match(/url\\(['"]*([^'"\\)]+)['"]*\\)/);
                return match ? match[1] : null;
            }
            return null;
            """
            return self.driver.execute_script(js)
        except:
            return None
    
    def _wait_for_captcha(self, timeout: int = 5) -> bool:
        """等待验证码出现"""
        # 常见验证码容器选择器
        captcha_selectors = [
            "[class*='botion_captcha']",  # botion验证码（优先）
            "[class*='botion_box']",
            "[class*='captcha']",
            "[class*='slider']",
            "[class*='verify']",
            "[class*='geetest']",
            "[id*='captcha']",
            ".nc-container",  # 阿里云滑块
            ".JDJRV-slide",   # 京东滑块
        ]
        
        for selector in captcha_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        return True
            except:
                continue
        
        return False
    
    def _save_captcha_images(self, bg_base64: str, slice_base64: str):
        """保存验证码图片用于调试分析"""
        try:
            import os
            from datetime import datetime
            
            debug_dir = "./cache/captcha_debug"
            os.makedirs(debug_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%H%M%S")
            
            # 保存背景图
            if bg_base64:
                bg_path = f"{debug_dir}/bg_{timestamp}.png"
                with open(bg_path, 'wb') as f:
                    f.write(base64.b64decode(bg_base64))
                self.logger.info(f"背景图已保存: {bg_path}")
            
            # 保存滑块图
            if slice_base64:
                slice_path = f"{debug_dir}/slice_{timestamp}.png"
                with open(slice_path, 'wb') as f:
                    f.write(base64.b64decode(slice_base64))
                self.logger.info(f"滑块图已保存: {slice_path}")
                
        except Exception as e:
            self.logger.debug(f"保存验证码图片失败: {e}")
    
    def _save_debug_screenshot(self, name: str = "captcha_page"):
        """保存调试截图和验证码DOM信息"""
        try:
            import os
            from datetime import datetime
            debug_dir = "./cache/captcha_debug"
            os.makedirs(debug_dir, exist_ok=True)
            
            # 保存整页截图
            timestamp = datetime.now().strftime("%H%M%S")
            screenshot_path = f"{debug_dir}/{name}_{timestamp}.png"
            self.driver.save_screenshot(screenshot_path)
            self.logger.info(f"调试截图已保存: {screenshot_path}")
            
            # 保存验证码区域的HTML和可能的滑块按钮信息
            js_get_captcha_info = """
            var result = {html: '', buttons: []};
            var captchaEls = document.querySelectorAll('[class*="captcha"], [class*="verify"], [class*="slider"], [class*="tcaptcha"]');
            
            for (var i = 0; i < captchaEls.length; i++) {
                result.html += captchaEls[i].outerHTML + '\\n\\n---\\n\\n';
                
                // 查找可能的滑块按钮
                var elements = captchaEls[i].querySelectorAll('*');
                for (var j = 0; j < elements.length; j++) {
                    var el = elements[j];
                    var rect = el.getBoundingClientRect();
                    if (rect.width >= 20 && rect.width <= 100 && rect.height >= 20 && rect.height <= 100) {
                        result.buttons.push({
                            tag: el.tagName,
                            class: el.className,
                            id: el.id,
                            width: rect.width,
                            height: rect.height,
                            left: rect.left,
                            top: rect.top
                        });
                    }
                }
            }
            
            return result;
            """
            captcha_info = self.driver.execute_script(js_get_captcha_info)
            
            # 保存HTML
            html_path = f"{debug_dir}/captcha_dom.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(captcha_info.get('html', '未找到验证码元素'))
            
            # 保存可能的按钮信息
            buttons_path = f"{debug_dir}/possible_buttons.txt"
            with open(buttons_path, 'w', encoding='utf-8') as f:
                f.write("可能的滑块按钮元素:\n\n")
                for btn in captcha_info.get('buttons', []):
                    f.write(f"Tag: {btn.get('tag')}\n")
                    f.write(f"Class: {btn.get('class')}\n")
                    f.write(f"ID: {btn.get('id')}\n")
                    f.write(f"Size: {btn.get('width')}x{btn.get('height')}\n")
                    f.write(f"Position: ({btn.get('left')}, {btn.get('top')})\n")
                    f.write("-" * 40 + "\n")
            
            self.logger.info(f"验证码DOM和按钮信息已保存")
            
        except Exception as e:
            self.logger.debug(f"保存调试信息失败: {e}")
    
    def _get_captcha_images(self) -> Tuple[Optional[str], Optional[str]]:
        """
        获取验证码的背景图和滑块图的base64
        
        Returns:
            (background_base64, target_base64)
        """
        # 先保存调试信息
        self._save_debug_screenshot()
        
        background_base64 = None
        target_base64 = None
        
        # 常见背景图选择器（添加更多）
        bg_selectors = [
            "[class*='captcha-bg']",
            "[class*='bg-img']",
            "[class*='slider-bg']",
            "[class*='geetest_canvas_bg']",
            "canvas.geetest_canvas_bg",
            ".verify-img-panel img",
            "[class*='verify'] img:first-child",
            # 腾讯验证码
            "#slideBg",
            "[class*='tc-bg-img']",
            ".tc-fg-item",
            # 阿里验证码
            ".nc-lang-cnt img",
            # 通用
            "[class*='puzzle'] img",
            "[class*='jigsaw'] img",
        ]
        
        # 常见滑块图选择器（添加更多）
        target_selectors = [
            "[class*='captcha-slice']",
            "[class*='slider-img']",
            "[class*='geetest_canvas_slice']",
            "canvas.geetest_canvas_slice",
            "[class*='verify-sub-block'] img",
            "[class*='slider'] img",
            # 腾讯验证码
            "#slideBlock",
            "[class*='tc-slider']",
            # 通用
            "[class*='puzzle-piece']",
            "[class*='jigsaw-piece']",
        ]
        
        # 尝试获取背景图
        for selector in bg_selectors:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if elem.is_displayed():
                    background_base64 = self._element_to_base64(elem)
                    if background_base64:
                        self.logger.info(f"获取背景图成功: {selector}")
                        break
            except:
                continue
        
        # 尝试获取滑块图
        for selector in target_selectors:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if elem.is_displayed():
                    target_base64 = self._element_to_base64(elem)
                    if target_base64:
                        self.logger.info(f"获取滑块图成功: {selector}")
                        break
            except:
                continue
        
        # 如果通过选择器没找到，尝试通过canvas获取
        if not background_base64 or not target_base64:
            bg, target = self._get_canvas_images()
            background_base64 = background_base64 or bg
            target_base64 = target_base64 or target
        
        # 最后尝试：智能查找所有img标签
        if not background_base64 or not target_base64:
            bg, target = self._find_captcha_images_smart()
            background_base64 = background_base64 or bg
            target_base64 = target_base64 or target
        
        return background_base64, target_base64
    
    def _find_captcha_images_smart(self) -> Tuple[Optional[str], Optional[str]]:
        """智能查找验证码图片"""
        try:
            # 查找验证码容器内的所有图片
            js_find_images = """
            // 查找所有可能的验证码容器
            var containers = document.querySelectorAll(
                '[class*="captcha"], [class*="verify"], [class*="slider"], ' +
                '[class*="tcaptcha"], [id*="captcha"], [id*="verify"]'
            );
            
            var result = {bg: null, slice: null, bgSize: 0, sliceSize: 0};
            
            for (var c = 0; c < containers.length; c++) {
                var imgs = containers[c].querySelectorAll('img');
                for (var i = 0; i < imgs.length; i++) {
                    var img = imgs[i];
                    if (!img.src || !img.offsetWidth) continue;
                    
                    var area = img.offsetWidth * img.offsetHeight;
                    
                    // 大图可能是背景，小图可能是滑块
                    if (area > result.bgSize && area > 5000) {
                        result.bg = img.src;
                        result.bgSize = area;
                    } else if (area > result.sliceSize && area > 500 && area < 10000) {
                        result.slice = img.src;
                        result.sliceSize = area;
                    }
                }
                
                // 也检查canvas
                var canvases = containers[c].querySelectorAll('canvas');
                for (var j = 0; j < canvases.length; j++) {
                    var canvas = canvases[j];
                    var area = canvas.width * canvas.height;
                    try {
                        var dataUrl = canvas.toDataURL('image/png');
                        if (area > result.bgSize && area > 5000) {
                            result.bg = dataUrl;
                            result.bgSize = area;
                        } else if (area > result.sliceSize && area > 500) {
                            result.slice = dataUrl;
                            result.sliceSize = area;
                        }
                    } catch(e) {}
                }
            }
            
            return result;
            """
            
            result = self.driver.execute_script(js_find_images)
            
            bg_base64 = None
            slice_base64 = None
            
            if result:
                if result.get('bg'):
                    bg_src = result['bg']
                    if bg_src.startswith('data:image'):
                        bg_base64 = bg_src.split(',')[1]
                    else:
                        # 下载图片
                        import requests
                        resp = requests.get(bg_src, timeout=5)
                        bg_base64 = base64.b64encode(resp.content).decode()
                    self.logger.info(f"智能查找背景图成功，大小: {result.get('bgSize')}")
                
                if result.get('slice'):
                    slice_src = result['slice']
                    if slice_src.startswith('data:image'):
                        slice_base64 = slice_src.split(',')[1]
                    else:
                        import requests
                        resp = requests.get(slice_src, timeout=5)
                        slice_base64 = base64.b64encode(resp.content).decode()
                    self.logger.info(f"智能查找滑块图成功，大小: {result.get('sliceSize')}")
            
            return bg_base64, slice_base64
            
        except Exception as e:
            self.logger.debug(f"智能查找图片失败: {e}")
            return None, None
    
    def _element_to_base64(self, element) -> Optional[str]:
        """将元素转换为base64"""
        try:
            # 如果是img标签
            tag_name = element.tag_name.lower()
            if tag_name == 'img':
                src = element.get_attribute('src')
                if src and src.startswith('data:image'):
                    # 已经是base64
                    return src.split(',')[1]
                elif src:
                    # 需要下载图片
                    import requests
                    response = requests.get(src)
                    return base64.b64encode(response.content).decode()
            
            # 如果是canvas
            elif tag_name == 'canvas':
                # 通过JavaScript获取canvas内容
                return self.driver.execute_script(
                    "return arguments[0].toDataURL('image/png').split(',')[1];",
                    element
                )
            
            # 其他元素，截图
            screenshot = element.screenshot_as_base64
            return screenshot
            
        except Exception as e:
            self.logger.debug(f"元素转base64失败: {e}")
            return None
    
    def _get_canvas_images(self) -> Tuple[Optional[str], Optional[str]]:
        """从canvas获取验证码图片"""
        try:
            # GeeTest类型验证码
            js_get_geetest = """
            var bg = document.querySelector('canvas.geetest_canvas_bg');
            var slice = document.querySelector('canvas.geetest_canvas_slice');
            if (bg && slice) {
                return {
                    bg: bg.toDataURL('image/png').split(',')[1],
                    slice: slice.toDataURL('image/png').split(',')[1]
                };
            }
            return null;
            """
            result = self.driver.execute_script(js_get_geetest)
            if result:
                return result.get('bg'), result.get('slice')
        except:
            pass
        
        return None, None
    
    def _calculate_distance(self, target_base64: str, background_base64: str) -> int:
        """计算滑块需要移动的距离，使用双引擎识别"""
        results = {}
        
        # 引擎1: ddddocr（优先）
        try:
            import ddddocr
            det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
            bg_bytes = base64.b64decode(background_base64)
            sl_bytes = base64.b64decode(target_base64)
            result = det.slide_match(sl_bytes, bg_bytes, simple_target=True)
            if result and 'target' in result:
                distance = result['target'][0]
                results['ddddocr'] = distance
                self.logger.info(f"ddddocr识别结果: {result['target']}")
        except Exception as e:
            self.logger.debug(f"ddddocr识别失败: {e}")
        
        # 引擎2: AntiCAP
        try:
            result = self.handler.Slider_Match(
                target_base64=target_base64,
                background_base64=background_base64
            )
            if result and 'target' in result:
                distance = result['target'][0]
                results['anticap'] = distance
                self.logger.info(f"AntiCAP识别结果: {result['target']}")
        except Exception as e:
            self.logger.debug(f"AntiCAP识别失败: {e}")
        
        if not results:
            self.logger.error("所有识别引擎均失败")
            return 0
        
        # 如果两个引擎都有结果，取平均值；否则用有结果的那个
        if len(results) == 2:
            avg = (results['ddddocr'] + results['anticap']) / 2
            diff = abs(results['ddddocr'] - results['anticap'])
            self.logger.info(f"双引擎: ddddocr={results['ddddocr']}, AntiCAP={results['anticap']}, 差值={diff}, 使用均值={int(avg)}")
            # 如果差异大于10px，说明有一个不准，取ddddocr
            if diff > 10:
                self.logger.warning(f"两引擎差异较大({diff}px)，优先使用ddddocr")
                return results['ddddocr']
            return int(avg)
        else:
            engine = list(results.keys())[0]
            distance = results[engine]
            self.logger.info(f"单引擎({engine}): {distance}px")
            return distance
    
    def _perform_slide(self, distance: int) -> bool:
        """执行滑动操作"""
        try:
            # 找到滑块按钮
            slider_btn = self._find_slider_button()
            if not slider_btn:
                self.logger.warning("未找到滑块按钮")
                return False
            
            self.logger.info("找到滑块按钮，开始滑动...")
            
            # 获取滑块轨道宽度来计算实际滑动距离
            actual_distance = self._calculate_actual_distance(distance, slider_btn)
            self.logger.info(f"原始距离: {distance}px, 实际滑动距离: {actual_distance}px")
            
            # 使用ActionChains进行真实拖动（不能中断）
            success = self._drag_slider(slider_btn, actual_distance)
            
            # 等待验证结果
            time.sleep(1.5)
            
            # 检查是否成功
            if self._check_success():
                self.logger.info("✅ 滑块验证成功！")
                return True
            else:
                self.logger.warning("滑块验证可能失败，需要重试")
                return False
                
        except Exception as e:
            self.logger.error(f"滑动执行失败: {e}")
            return False
    
    def _drag_slider(self, slider_btn, distance: int) -> bool:
        """使用ActionChains拖动滑块（保持按住状态）"""
        try:
            # 生成模拟人类的滑动轨迹
            tracks = self._generate_human_track(distance)
            total_distance = sum(tracks)
            
            self.logger.info(f"滑动轨迹: {len(tracks)} 步, 总距离: {total_distance}px")
            
            # 记录滑块初始位置
            btn_rect = slider_btn.rect
            self.logger.info(f"滑块初始位置: x={btn_rect['x']}, y={btn_rect['y']}")
            
            # 创建ActionChains - 一次性执行所有操作
            actions = ActionChains(self.driver)
            
            # 移动到滑块中心
            actions.move_to_element(slider_btn)
            
            # 按住滑块
            actions.click_and_hold()
            
            # 分步移动（模拟人类）
            for x_offset in tracks:
                # 添加微小的y轴抖动
                y_offset = random.randint(-1, 1)
                actions.move_by_offset(x_offset, y_offset)
            
            # 暂停让页面响应
            actions.pause(0.2)
            
            # 一次性执行移动
            actions.perform()
            
            # 滑动完成后截图（鼠标仍按住）
            self._save_slide_screenshot(f"slide_{distance}px")
            
            # 获取滑块当前位置
            try:
                new_rect = slider_btn.rect
                actual_move = new_rect['x'] - btn_rect['x']
                self.logger.info(f"滑块当前位置: x={new_rect['x']}, 实际移动: {actual_move}px")
            except:
                pass
            
            # 释放滑块
            time.sleep(0.1)
            release_action = ActionChains(self.driver)
            release_action.release()
            release_action.perform()
            
            self.logger.info("拖动完成")
            return True
            
        except Exception as e:
            self.logger.error(f"拖动滑块失败: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False
    
    def _save_slide_screenshot(self, name: str):
        """保存滑动截图"""
        try:
            import os
            from datetime import datetime
            
            debug_dir = "./cache/captcha_debug"
            os.makedirs(debug_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%H%M%S")
            path = f"{debug_dir}/slide_{name}_{timestamp}.png"
            self.driver.save_screenshot(path)
            self.logger.info(f"滑动截图已保存: {path}")
        except Exception as e:
            self.logger.debug(f"保存截图失败: {e}")
    
    def _generate_human_track(self, distance: int) -> list:
        """生成模拟人类的滑动轨迹"""
        tracks = []
        current = 0
        
        # 先快后慢
        mid = distance * 0.7
        
        while current < distance:
            if current < mid:
                # 加速阶段
                step = random.randint(8, 15)
            else:
                # 减速阶段
                step = random.randint(2, 5)
            
            if current + step > distance:
                step = distance - current
            
            tracks.append(step)
            current += step
        
        # 可能会有微小的过冲和回调
        if random.random() > 0.5:
            tracks.append(random.randint(1, 3))  # 过冲
            tracks.append(-random.randint(1, 3))  # 回调
        
        return tracks
    
    def _calculate_actual_distance(self, img_distance: int, slider_btn) -> int:
        """根据图片坐标计算实际滑动距离"""
        try:
            # 获取显示尺寸
            js_get_dims = """
            var bgEl = document.querySelector('[class*="botion_bg"]');
            return bgEl ? bgEl.offsetWidth : 280;
            """
            bg_width = self.driver.execute_script(js_get_dims) or 280
            
            # 原图宽度固定340
            natural_width = 340
            scale = bg_width / natural_width
            
            # 缩放 + 固定补偿22px（校准值）
            scaled = img_distance * scale
            offset = 22  # 校准测得固定偏移约22px
            actual_distance = int(scaled + offset + random.randint(-2, 2))
            actual_distance = max(10, actual_distance)
            
            self.logger.info(f"计算: 显示宽={bg_width}, 缩放={scale:.3f}, 缺口x={img_distance}, 缩放后={scaled:.0f}, +偏移{offset}, 最终={actual_distance}px")
            
            return actual_distance
            
        except Exception as e:
            self.logger.debug(f"计算失败: {e}")
            return img_distance
    
    def _slide_with_js(self, slider_btn, distance: int) -> bool:
        """使用JavaScript执行滑动"""
        try:
            js_slide = """
            var slider = arguments[0];
            var distance = arguments[1];
            
            // 模拟mousedown
            var rect = slider.getBoundingClientRect();
            var startX = rect.left + rect.width / 2;
            var startY = rect.top + rect.height / 2;
            
            var mousedown = new MouseEvent('mousedown', {
                bubbles: true, cancelable: true, view: window,
                clientX: startX, clientY: startY
            });
            slider.dispatchEvent(mousedown);
            
            // 分步移动
            var steps = 20;
            var stepDistance = distance / steps;
            var currentX = startX;
            
            for (var i = 0; i < steps; i++) {
                currentX += stepDistance;
                var mousemove = new MouseEvent('mousemove', {
                    bubbles: true, cancelable: true, view: window,
                    clientX: currentX, clientY: startY + Math.random() * 2
                });
                document.dispatchEvent(mousemove);
            }
            
            // 模拟mouseup
            var mouseup = new MouseEvent('mouseup', {
                bubbles: true, cancelable: true, view: window,
                clientX: currentX, clientY: startY
            });
            document.dispatchEvent(mouseup);
            
            return true;
            """
            
            self.driver.execute_script(js_slide, slider_btn, distance)
            time.sleep(0.5)
            return True
            
        except Exception as e:
            self.logger.debug(f"JS滑动失败: {e}")
            return False
    
    def _slide_with_actions(self, slider_btn, distance: int) -> bool:
        """使用ActionChains执行滑动"""
        try:
            # 计算安全的滑动轨迹
            tracks = self._generate_track(distance)
            
            # 确保每步移动不会太大
            safe_tracks = []
            for t in tracks:
                if abs(t) > 50:
                    # 分解大步骤
                    steps = abs(t) // 20 + 1
                    step_size = t / steps
                    safe_tracks.extend([int(step_size)] * steps)
                else:
                    safe_tracks.append(t)
            
            actions = ActionChains(self.driver)
            actions.click_and_hold(slider_btn)
            actions.pause(0.1)
            
            for x in safe_tracks:
                actions.move_by_offset(x, random.randint(-1, 1))
                actions.pause(0.01)
            
            actions.pause(0.2)
            actions.release()
            actions.perform()
            
            return True
            
        except Exception as e:
            self.logger.debug(f"ActionChains滑动失败: {e}")
            return False
    
    def _find_slider_button(self):
        """找到验证码弹窗中的滑块按钮"""
        
        # 等待验证码弹窗完全加载
        time.sleep(0.5)
        
        # botion验证码的滑块选择器（优先级从高到低）
        botion_selectors = [
            # 精确匹配botion滑块按钮（在轨道内的btn）
            ".botion_track .botion_btn",
            "[class*='botion_track'] [class*='botion_btn']",
            ".botion_slider .botion_btn",
            "[class*='botion_slider'] [class*='botion_btn']",
            # 直接匹配botion_btn
            "div.botion_btn",
            "[class*='botion_btn']",
        ]
        
        for selector in botion_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        # 确认是滑块按钮（排除关闭按钮等）
                        class_name = elem.get_attribute('class') or ''
                        if 'close' not in class_name and 'refresh' not in class_name:
                            self.logger.info(f"找到botion滑块按钮: {selector}, class={class_name[:50]}")
                            return elem
            except Exception as e:
                self.logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        
        # 使用JavaScript查找（作为备用）
        js_find_botion = """
        // 查找botion_track内的botion_btn
        var tracks = document.querySelectorAll('[class*="botion_track"]');
        for (var t = 0; t < tracks.length; t++) {
            var btns = tracks[t].querySelectorAll('[class*="botion_btn"]');
            for (var b = 0; b < btns.length; b++) {
                var btn = btns[b];
                var rect = btn.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    return btn;
                }
            }
        }
        
        // 直接查找所有botion_btn
        var allBtns = document.querySelectorAll('[class*="botion_btn"]');
        for (var i = 0; i < allBtns.length; i++) {
            var btn = allBtns[i];
            var className = btn.className || '';
            // 排除关闭和刷新按钮
            if (!className.includes('close') && !className.includes('refresh')) {
                var rect = btn.getBoundingClientRect();
                if (rect.width > 30 && rect.height > 30) {
                    return btn;
                }
            }
        }
        return null;
        """
        
        try:
            elem = self.driver.execute_script(js_find_botion)
            if elem:
                self.logger.info("JS查找到botion滑块按钮")
                return elem
        except Exception as e:
            self.logger.debug(f"JS查找botion滑块失败: {e}")
        
        # 首先找到验证码弹窗容器（通常是新弹出的模态框）
        js_find_captcha_slider = """
        // 查找验证码弹窗（通常是最上层的模态框）
        var modals = document.querySelectorAll('[class*="modal"], [class*="dialog"], [class*="popup"], [class*="overlay"]');
        var captchaModal = null;
        
        // 找到包含"滑块"或"验证"文字的弹窗
        for (var i = 0; i < modals.length; i++) {
            var modal = modals[i];
            var text = modal.innerText || '';
            var style = window.getComputedStyle(modal);
            
            if ((text.includes('滑') || text.includes('拖动') || text.includes('验证') || text.includes('拼图')) 
                && style.display !== 'none' && style.visibility !== 'hidden') {
                captchaModal = modal;
                break;
            }
        }
        
        // 如果没找到，查找包含验证码图片的容器
        if (!captchaModal) {
            var imgs = document.querySelectorAll('img');
            for (var j = 0; j < imgs.length; j++) {
                var img = imgs[j];
                var src = img.src || '';
                if (src.includes('slide') || src.includes('captcha') || src.includes('verify')) {
                    // 找到图片的父容器
                    var parent = img.parentElement;
                    for (var k = 0; k < 5 && parent; k++) {
                        var rect = parent.getBoundingClientRect();
                        if (rect.width > 200 && rect.height > 150) {
                            captchaModal = parent;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    if (captchaModal) break;
                }
            }
        }
        
        if (!captchaModal) {
            console.log('未找到验证码弹窗');
            return null;
        }
        
        console.log('找到验证码容器:', captchaModal.className);
        
        // 在验证码容器中查找滑块按钮
        // 滑块按钮特征：在底部轨道上，可拖动，通常有箭头图标
        var allElements = captchaModal.querySelectorAll('*');
        var candidates = [];
        
        for (var e = 0; e < allElements.length; e++) {
            var el = allElements[e];
            var rect = el.getBoundingClientRect();
            var className = (el.className || '').toLowerCase();
            var tagName = el.tagName.toLowerCase();
            
            // 滑块按钮特征：宽40-100，高30-60，位于容器下部
            if (rect.width >= 40 && rect.width <= 100 && 
                rect.height >= 30 && rect.height <= 60 &&
                rect.top > 400) {  // 通常在屏幕下半部分
                
                // 检查是否像滑块按钮
                var hasSlideKeyword = className.includes('slide') || className.includes('btn') || 
                                      className.includes('drag') || className.includes('handler');
                var hasIcon = el.querySelector('svg, i, [class*="icon"]') !== null;
                var isSvgOrDiv = tagName === 'div' || tagName === 'span' || tagName === 'button';
                
                if (hasSlideKeyword || hasIcon || isSvgOrDiv) {
                    candidates.push({
                        el: el,
                        score: (hasSlideKeyword ? 10 : 0) + (hasIcon ? 5 : 0),
                        width: rect.width,
                        height: rect.height,
                        top: rect.top,
                        class: className
                    });
                }
            }
        }
        
        // 按分数排序，取最可能的
        candidates.sort(function(a, b) { return b.score - a.score; });
        
        console.log('候选滑块:', candidates.length);
        for (var c = 0; c < Math.min(5, candidates.length); c++) {
            console.log('  ', candidates[c].class, candidates[c].width + 'x' + candidates[c].height);
        }
        
        if (candidates.length > 0) {
            return candidates[0].el;
        }
        
        return null;
        """
        
        try:
            elem = self.driver.execute_script(js_find_captcha_slider)
            if elem:
                try:
                    class_name = elem.get_attribute('class') or ''
                    self.logger.info(f"在验证码弹窗中找到滑块: class='{class_name}'")
                except:
                    self.logger.info("在验证码弹窗中找到滑块")
                return elem
        except Exception as e:
            self.logger.debug(f"查找验证码滑块失败: {e}")
        
        # 回退到旧方法
        slider_selectors = [
            "[class*='slider-btn']",
            "[class*='slider-button']",
            "[class*='slide-btn']",
            "[class*='geetest_slider_button']",
            ".nc_iconfont.btn_slide",
            "[class*='verify-move-block']",
        ]
        
        for selector in slider_selectors:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if elem.is_displayed():
                    self.logger.info(f"找到滑块按钮: {selector}")
                    return elem
            except:
                continue
        
        # 智能查找：打印所有可能的滑块元素用于调试
        try:
            js_find_all_sliders = """
            var result = [];
            var containers = document.querySelectorAll('[class*="captcha"], [class*="verify"], [class*="slide"]');
            
            for (var c = 0; c < containers.length; c++) {
                var container = containers[c];
                var elements = container.querySelectorAll('*');
                
                for (var i = 0; i < elements.length; i++) {
                    var el = elements[i];
                    var rect = el.getBoundingClientRect();
                    
                    // 查找可能是滑块的元素
                    if (rect.width >= 30 && rect.width <= 120 && 
                        rect.height >= 30 && rect.height <= 80 &&
                        rect.top > 0) {
                        result.push({
                            tag: el.tagName,
                            class: el.className || '',
                            id: el.id || '',
                            width: rect.width,
                            height: rect.height,
                            left: rect.left,
                            top: rect.top
                        });
                    }
                }
            }
            return result;
            """
            
            all_sliders = self.driver.execute_script(js_find_all_sliders)
            self.logger.info(f"找到 {len(all_sliders)} 个可能的滑块元素:")
            for s in all_sliders[:10]:
                self.logger.info(f"  {s['tag']} class='{s['class'][:50]}' size={s['width']:.0f}x{s['height']:.0f}")
            
            # 尝试找到真正的滑块（蓝色圆角按钮，有箭头图标）
            js_find_real_slider = """
            // 查找滑块容器
            var slideContainers = document.querySelectorAll('[class*="slide"]');
            
            for (var c = 0; c < slideContainers.length; c++) {
                var container = slideContainers[c];
                var className = (container.className || '').toLowerCase();
                
                // 查找滑动条/轨道上的按钮
                if (className.includes('bar') || className.includes('track') || className.includes('rail')) {
                    var children = container.children;
                    for (var i = 0; i < children.length; i++) {
                        var child = children[i];
                        var rect = child.getBoundingClientRect();
                        if (rect.width >= 40 && rect.width <= 100 && rect.height >= 30) {
                            return child;
                        }
                    }
                }
                
                // 查找class包含btn的元素
                var btns = container.querySelectorAll('[class*="btn"]');
                for (var b = 0; b < btns.length; b++) {
                    var btn = btns[b];
                    var rect = btn.getBoundingClientRect();
                    if (rect.width >= 40 && rect.width <= 100 && rect.height >= 30 && rect.height <= 60) {
                        return btn;
                    }
                }
            }
            
            // 直接查找包含箭头图标的按钮
            var allBtns = document.querySelectorAll('[class*="slide"][class*="btn"], [class*="slider"] [class*="btn"]');
            for (var i = 0; i < allBtns.length; i++) {
                var btn = allBtns[i];
                var rect = btn.getBoundingClientRect();
                if (rect.width >= 40 && rect.height >= 30) {
                    return btn;
                }
            }
            
            return null;
            """
            
            elem = self.driver.execute_script(js_find_real_slider)
            if elem:
                try:
                    class_name = elem.get_attribute('class') or ''
                    self.logger.info(f"智能查找到滑块按钮: class='{class_name}'")
                except:
                    self.logger.info("智能查找到滑块按钮")
                return elem
                
        except Exception as e:
            self.logger.debug(f"智能查找滑块失败: {e}")
        
        return None
    
    def _generate_track(self, distance: int) -> list:
        """
        生成滑动轨迹
        模拟人类滑动：先加速后减速
        """
        tracks = []
        current = 0
        mid = distance * 0.7  # 减速点
        
        # 初始速度和加速度
        v = 0
        t = 0.3
        
        while current < distance:
            if current < mid:
                a = 2  # 加速
            else:
                a = -3  # 减速
            
            v0 = v
            v = v0 + a * t
            v = max(v, 1)  # 最小速度
            
            move = v0 * t + 0.5 * a * t * t
            move = max(1, int(move))
            
            current += move
            tracks.append(move)
        
        # 微调：如果超过了，回退一点
        overshoot = current - distance
        if overshoot > 0:
            tracks.append(-overshoot)
        
        return tracks
    
    def _check_success(self) -> bool:
        """检查验证是否成功"""
        # 检查验证码是否消失
        if not self._wait_for_captcha(timeout=1):
            return True
        
        # 检查是否有成功标识
        success_selectors = [
            "[class*='success']",
            "[class*='geetest_success']",
            ".nc_iconfont.icon-ok",
        ]
        
        for selector in success_selectors:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if elem.is_displayed():
                    return True
            except:
                continue
        
        return False
