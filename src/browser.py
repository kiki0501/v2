"""
浏览器管理模块 - 有头模式版本
基于 vvv 的实现，修改为可见浏览器窗口
"""

import asyncio
from typing import Optional, Callable
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class HeadfulBrowser:
    """有头浏览器管理器 - 可见窗口版本"""
    
    # Vertex AI Studio URL
    VERTEX_AI_URL = "https://console.cloud.google.com/vertex-ai/studio/multimodal?mode=prompt&model=gemini-2.5-flash-lite-preview-09-2025"
    
    # 用户数据目录 (保存登录态)
    USER_DATA_DIR = "browser_data"
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._is_running = False
    
    @staticmethod
    def check_availability() -> bool:
        """检查 Playwright 是否可用"""
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright 未安装，请运行: pip install playwright && playwright install chromium")
            return False
        return True
    
    async def start(self, headless: bool = False) -> bool:
        """
        启动浏览器 - 有头模式
        
        Args:
            headless: 是否无头模式 (默认 False，显示窗口)
        """
        if not self.check_availability():
            return False
        
        try:
            print(f"🌐 正在启动浏览器 ({'无头' if headless else '有头'}模式)...")
            
            # 确保用户数据目录存在
            user_data_path = Path(self.USER_DATA_DIR)
            user_data_path.mkdir(parents=True, exist_ok=True)
            
            self.playwright = await async_playwright().start()
            
            # 启动参数
            launch_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
            
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_path),
                headless=headless,
                viewport={'width': 1920, 'height': 1080},
                screen={'width': 1920, 'height': 1080},
                device_scale_factor=1.0,
                locale="en-US",
                timezone_id="America/New_York",
                args=launch_args,
            )
            
            # 获取或创建页面
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
            
            self._is_running = True
            print(f"✅ 浏览器已启动 (窗口: 1920x1080)")
            return True
            
        except Exception as e:
            print(f"❌ 浏览器启动失败: {e}")
            return False
    
    async def navigate_to_vertex(self) -> bool:
        """导航到 Vertex AI Studio"""
        if not self.page:
            print("❌ 浏览器未启动")
            return False
        
        try:
            print(f"🔗 正在导航到 Vertex AI Studio...")
            
            # 导航到页面
            await self.page.goto(self.VERTEX_AI_URL, wait_until="domcontentloaded", timeout=30000)
            
            # 检查是否需要登录
            current_url = self.page.url
            if "accounts.google.com" in current_url:
                print("⚠️ 需要登录 Google 账号")
                print("   请在浏览器窗口中完成登录...")
                # 等待用户登录 (最多5分钟)
                try:
                    await self.page.wait_for_url("**/vertex-ai/**", timeout=300000)
                    print("✅ 登录成功")
                except:
                    print("❌ 登录超时")
                    return False
            
            await asyncio.sleep(3)
            
            # 检查并处理条款对话框
            await self._check_and_accept_terms()
            
            # 关闭其他 overlay
            await self._dismiss_overlays()
            
            print("✅ 已到达 Vertex AI Studio")
            return True
            
        except Exception as e:
            print(f"❌ 导航失败: {e}")
            return False
    
    async def _check_and_accept_terms(self) -> bool:
        """
        检测并同意 Google Cloud 服务条款 - 优化版本（基于 vvv）
        
        使用多种选择器策略，提高兼容性和成功率
        
        Returns:
            是否检测到并处理了条款对话框
        """
        if not self.page:
            return False
        
        try:
            # 1. 条款检测选择器（优先级排序）
            TERMS_SELECTORS = [
                'p.notranslate',
                '[role="dialog"] p',
                '.mdc-dialog__content p',
                '[aria-modal="true"] p',
                'text=/terms.*conditions/i',
                'text=/service.*terms/i',
            ]
            
            # 2. 查找条款元素
            terms_element = None
            for selector in TERMS_SELECTORS:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            # 验证是否包含条款关键词
                            text = await element.text_content()
                            if text:
                                text_lower = text.lower()
                                if any(kw in text_lower for kw in ['terms', 'agree', '条款', '同意', 'consent', 'accept']):
                                    terms_element = element
                                    break
                except:
                    continue
            
            if not terms_element:
                return False
            
            print("📜 检测到服务条款对话框，正在自动同意...")
            
            # 3. 智能滚动条款内容到底部
            await self.page.evaluate('''() => {
                // 查找所有可能的滚动容器
                const scrollableSelectors = [
                    '.mdc-dialog__content',
                    '[role="dialog"] [style*="overflow"]',
                    '.terms-content',
                    '.consent-content'
                ];
                
                for (const selector of scrollableSelectors) {
                    const containers = document.querySelectorAll(selector);
                    for (const container of containers) {
                        const style = window.getComputedStyle(container);
                        if (style.overflow === 'auto' || style.overflow === 'scroll' ||
                            style.overflowY === 'auto' || style.overflowY === 'scroll') {
                            // 平滑滚动到底部
                            container.scrollTo({
                                top: container.scrollHeight,
                                behavior: 'smooth'
                            });
                        }
                    }
                }
                
                // 备选：查找条款文本并滚动
                const termsText = document.querySelector('p.notranslate');
                if (termsText) {
                    termsText.scrollIntoView({ block: 'end', behavior: 'smooth' });
                }
            }''')
            
            # 最小等待滚动完成
            await asyncio.sleep(0.1)
            print("   ✓ 已滚动到条款底部")
            
            # 4. 尝试勾选同意复选框（如果存在）
            CHECKBOX_SELECTORS = [
                'input.mdc-checkbox__native-control[type="checkbox"]',
                '[role="dialog"] input[type="checkbox"]',
                '.mdc-checkbox input[type="checkbox"]',
                'input[type="checkbox"][aria-label*="agree"]',
                'input[type="checkbox"][aria-label*="同意"]'
            ]
            
            checkbox = None
            for selector in CHECKBOX_SELECTORS:
                try:
                    checkbox = await self.page.query_selector(selector)
                    if checkbox:
                        is_visible = await checkbox.is_visible()
                        if is_visible:
                            break
                        checkbox = None
                except:
                    continue
            
            if checkbox:
                try:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await checkbox.click()
                        await asyncio.sleep(0.05)
                    print("   ✓ 已勾选同意复选框")
                except:
                    print("   ℹ️ 复选框处理失败（可能不需要）")
            
            # 5. 点击同意按钮（快速版本）
            BUTTON_SELECTORS = [
                'span.mdc-button__label:has-text("同意")',
                'span.mdc-button__label:has-text("Agree")',
                'span.mdc-button__label:has-text("Accept")',
                'button:has-text("同意")',
                'button:has-text("Agree")',
                'button:has-text("Accept")',
                'button:has-text("I agree")',
                '[role="dialog"] button[type="submit"]',
                '.mdc-dialog__actions button:last-child',
                'button[aria-label*="accept"]',
                'button[aria-label*="agree"]',
            ]
            
            agree_button = None
            for selector in BUTTON_SELECTORS:
                try:
                    agree_button = await self.page.query_selector(selector)
                    if agree_button:
                        is_visible = await agree_button.is_visible()
                        is_enabled = await agree_button.is_enabled()
                        if is_visible and is_enabled:
                            break
                        agree_button = None
                except:
                    continue
            
            if agree_button:
                # 直接点击，最小化延迟
                await agree_button.click()
                await asyncio.sleep(0.2)
                print("   ✓ 已点击同意按钮")
                print("✅ 条款已自动同意")
                return True
            else:
                # 备选：尝试按 Enter 键
                print("   ⚠️ 未找到同意按钮，尝试按 Enter...")
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(0.2)
                return True
            
        except Exception as e:
            print(f"   ⚠️ 处理条款对话框时出错: {e}")
            return False
    
    async def _dismiss_overlays(self) -> None:
        """关闭页面上的 overlay 遮罩层"""
        if not self.page:
            return
        
        try:
            await self.page.evaluate('''() => {
                // 1. 点击所有 backdrop 关闭对话框
                const backdrops = document.querySelectorAll('.cdk-overlay-backdrop');
                backdrops.forEach(backdrop => {
                    if (backdrop.offsetParent !== null) {
                        backdrop.click();
                    }
                });
                
                // 2. 按 Escape 键关闭任何模态
                document.dispatchEvent(new KeyboardEvent('keydown', {
                    key: 'Escape',
                    code: 'Escape',
                    keyCode: 27,
                    which: 27,
                    bubbles: true
                }));
                
                // 3. 移除阻挡的 overlay 容器内容
                const overlayContainer = document.querySelector('.cdk-overlay-container');
                if (overlayContainer) {
                    const activeBackdrop = overlayContainer.querySelector('.cdk-overlay-backdrop-showing');
                    if (activeBackdrop) {
                        const closeButtons = overlayContainer.querySelectorAll(
                            'button[aria-label*="close"], button[aria-label*="Close"], ' +
                            'button[aria-label*="关闭"], .mat-dialog-close, ' +
                            'button.close, [mat-dialog-close]'
                        );
                        closeButtons.forEach(btn => btn.click());
                    }
                }
            }''')
            
            await asyncio.sleep(0.3)
            
        except Exception as e:
            print(f"   ⚠️ 关闭 overlay 时出错: {e}")
    
    async def send_test_message(self, max_retries: int = 3) -> bool:
        """发送测试消息触发 API 请求 - 增强版"""
        if not self.page:
            return False
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"💬 重试发送测试消息 ({attempt + 1}/{max_retries})...")
                else:
                    print("💬 正在发送测试消息...")
                
                # 1. 先检查条款，再关闭其他 overlay
                await self._check_and_accept_terms()
                await asyncio.sleep(0.5)
                await self._dismiss_overlays()
                await asyncio.sleep(0.5)
                
                # 2. 等待页面稳定
                await asyncio.sleep(1)
                
                # 3. 使用增强的 JavaScript 输入和发送逻辑
                result = await self.page.evaluate('''() => {
                    // 关闭所有 overlay
                    const overlays = document.querySelectorAll('.cdk-overlay-backdrop');
                    overlays.forEach(el => el.click());
                    
                    // 多种选择器策略查找输入框
                    const selectors = [
                        'div[contenteditable="true"]',
                        'textarea[aria-label*="message"]',
                        'textarea[placeholder*="message"]',
                        'textarea[placeholder*="prompt"]',
                        '[role="textbox"]'
                    ];
                    
                    let input = null;
                    for (const sel of selectors) {
                        const elements = document.querySelectorAll(sel);
                        for (const el of elements) {
                            // 检查元素是否可见
                            if (el.offsetParent !== null &&
                                window.getComputedStyle(el).display !== 'none' &&
                                window.getComputedStyle(el).visibility !== 'hidden') {
                                input = el;
                                break;
                            }
                        }
                        if (input) break;
                    }
                    
                    if (!input) {
                        return { success: false, error: 'Input not found' };
                    }
                    
                    // 聚焦输入框
                    input.focus();
                    input.click();
                    
                    // 设置内容
                    const testMessage = 'hi';
                    if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {
                        input.value = testMessage;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    } else {
                        input.textContent = testMessage;
                        input.innerHTML = testMessage;
                        input.dispatchEvent(new InputEvent('input', { bubbles: true, data: testMessage }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    
                    return { success: true, inputType: input.tagName };
                }''')
                
                if not result.get('success'):
                    if attempt < max_retries - 1:
                        print(f"   ⚠️ {result.get('error', '未知错误')}，重试中...")
                        await asyncio.sleep(1)
                        continue
                    print(f"❌ 发送失败: {result.get('error')}")
                    return False
                
                print(f"   ✍️ 已输入消息到 {result.get('inputType')} 元素")
                await asyncio.sleep(0.3)
                
                # 4. 尝试多种发送方式
                sent = await self.page.evaluate('''() => {
                    // 方法 1: 尝试按 Enter 键（通过事件）
                    const input = document.querySelector('div[contenteditable="true"], textarea[aria-label*="message"], textarea[placeholder*="message"]');
                    if (input) {
                        const enterEvent = new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true,
                            cancelable: true
                        });
                        input.dispatchEvent(enterEvent);
                        
                        // 等待一小段时间检查是否清空
                        return new Promise(resolve => {
                            setTimeout(() => {
                                const cleared = (input.value || input.textContent || '').trim() === '';
                                resolve({ method: 'enter', cleared });
                            }, 500);
                        });
                    }
                    return { method: 'none', cleared: false };
                }''')
                
                if sent.get('cleared'):
                    print(f"   ✅ 消息已通过 {sent.get('method')} 方式发送")
                    return True
                
                # 方法 2: 按 Enter 键（通过 Playwright）
                print("   → 尝试 Playwright keyboard.press...")
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(0.5)
                
                # 检查是否清空
                cleared = await self.page.evaluate('''() => {
                    const input = document.querySelector('div[contenteditable="true"], textarea[aria-label*="message"], textarea[placeholder*="message"]');
                    return input ? (input.value || input.textContent || '').trim() === '' : false;
                }''')
                
                if cleared:
                    print("   ✅ 消息已发送（输入框已清空）")
                    return True
                
                # 方法 3: 查找并点击发送按钮
                print("   → 尝试查找发送按钮...")
                button_clicked = await self.page.evaluate('''() => {
                    const buttonSelectors = [
                        'button[aria-label*="Send"]',
                        'button[aria-label*="send"]',
                        'button[type="submit"]',
                        'button:has(svg)',
                        '[role="button"][aria-label*="send"]'
                    ];
                    
                    for (const sel of buttonSelectors) {
                        const buttons = document.querySelectorAll(sel);
                        for (const btn of buttons) {
                            if (btn.offsetParent !== null && !btn.disabled) {
                                btn.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }''')
                
                if button_clicked:
                    await asyncio.sleep(0.5)
                    cleared = await self.page.evaluate('''() => {
                        const input = document.querySelector('div[contenteditable="true"], textarea[aria-label*="message"], textarea[placeholder*="message"]');
                        return input ? (input.value || input.textContent || '').trim() === '' : false;
                    }''')
                    
                    if cleared:
                        print("   ✅ 消息已通过按钮发送")
                        return True
                
                if attempt < max_retries - 1:
                    print("   ⚠️ 消息未能发送，重试中...")
                    await asyncio.sleep(1)
                    continue
                
                print("❌ 所有发送方式均失败")
                return False
                
            except Exception as e:
                error_msg = str(e)
                if "intercepts pointer events" in error_msg and attempt < max_retries - 1:
                    print(f"   ⚠️ 检测到 overlay 遮挡，尝试关闭...")
                    await self._dismiss_overlays()
                    await asyncio.sleep(0.5)
                    continue
                elif attempt < max_retries - 1:
                    print(f"   ⚠️ 发送失败: {error_msg[:50]}，重试中...")
                    await asyncio.sleep(1)
                    continue
                else:
                    print(f"❌ 发送消息失败: {e}")
                    return False
        
        return False
    
    async def setup_request_interception(self, on_request: Callable) -> None:
        """设置请求拦截"""
        if not self.page:
            return
        
        async def handle_request(request):
            url = request.url
            if "batchGraphql" in url or "StreamGenerateContent" in url:
                await on_request(request)
        
        self.page.on("request", handle_request)
        print("🔍 请求拦截已设置")
    
    async def close(self) -> None:
        """关闭浏览器"""
        self._is_running = False
        
        if self.context:
            await self.context.close()
            self.context = None
            self.page = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        print("🔒 浏览器已关闭")
    
    @property
    def is_running(self) -> bool:
        return self._is_running