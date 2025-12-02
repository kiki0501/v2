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
            await self._dismiss_overlays()
            
            print("✅ 已到达 Vertex AI Studio")
            return True
            
        except Exception as e:
            print(f"❌ 导航失败: {e}")
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
        """发送测试消息触发 API 请求"""
        if not self.page:
            return False
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"💬 重试发送测试消息 ({attempt + 1}/{max_retries})...")
                else:
                    print("💬 正在发送测试消息...")
                
                # 1. 先关闭 overlay
                await self._dismiss_overlays()
                
                # 2. 等待输入框
                input_selector = 'textarea[aria-label*="message"], div[contenteditable="true"], textarea[placeholder*="message"]'
                try:
                    await self.page.wait_for_selector(input_selector, timeout=10000)
                except Exception:
                    if attempt < max_retries - 1:
                        print("   ⚠️ 输入框未出现，刷新页面...")
                        await self.page.reload(wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(2)
                        continue
                    raise
                
                # 3. 使用 JavaScript 直接输入
                success = await self.page.evaluate('''() => {
                    const overlays = document.querySelectorAll('.cdk-overlay-backdrop');
                    overlays.forEach(el => {
                        if (el.classList.contains('cdk-overlay-backdrop')) {
                            el.click();
                        }
                    });
                    
                    const selectors = [
                        'textarea[aria-label*="message"]',
                        'div[contenteditable="true"]',
                        'textarea[placeholder*="message"]'
                    ];
                    
                    let input = null;
                    for (const sel of selectors) {
                        input = document.querySelector(sel);
                        if (input && input.offsetParent !== null) break;
                        input = null;
                    }
                    
                    if (!input) return false;
                    
                    input.focus();
                    
                    if (input.tagName === 'TEXTAREA') {
                        input.value = 'hi';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    } else {
                        input.textContent = 'hi';
                        input.dispatchEvent(new InputEvent('input', { bubbles: true, data: 'hi' }));
                    }
                    
                    return true;
                }''')
                
                if not success:
                    if attempt < max_retries - 1:
                        print("   ⚠️ 无法设置输入内容，重试中...")
                        await asyncio.sleep(1)
                        continue
                    print("❌ 未找到可用的输入框")
                    return False
                
                await asyncio.sleep(0.1)
                
                # 4. 按回车发送
                await self.page.keyboard.press("Enter")
                print("✅ 测试消息已发送")
                return True
                
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