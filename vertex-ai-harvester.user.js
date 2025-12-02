// ==UserScript==
// @name         Vertex AI Credential Harvester v1.0
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Intercepts request headers and bodies to enable Headful Proxying.
// @author       Roo
// @match        https://console.cloud.google.com/*
// @grant        GM_xmlhttpRequest
// @run-at       document-start
// @connect      127.0.0.1
// @noframes
// ==/UserScript==

(function() {
    'use strict';

    console.log('Harvester: Initializing...');

    // --- UI Logger (Mac Style) ---
    let logContainer = null;
    let logContent = null;

    function createUI() {
        if (logContainer) return;

        // Main Container (Glassmorphism)
        logContainer = document.createElement('div');
        Object.assign(logContainer.style, {
            position: 'fixed',
            bottom: '20px',
            left: '20px',
            width: '380px',
            height: '240px',
            backgroundColor: 'rgba(28, 28, 30, 0.85)', // Dark macOS theme
            backdropFilter: 'blur(12px)',
            webkitBackdropFilter: 'blur(12px)',
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            zIndex: '999999',
            display: 'flex',
            flexDirection: 'column',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            overflow: 'hidden',
            transition: 'opacity 0.3s ease'
        });

        // Title Bar
        const titleBar = document.createElement('div');
        Object.assign(titleBar.style, {
            height: '28px',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 10px',
            cursor: 'move' // Placeholder for drag logic if needed
        });

        // Traffic Lights
        const trafficLights = document.createElement('div');
        Object.assign(trafficLights.style, {
            display: 'flex',
            gap: '6px'
        });
        
        ['#ff5f56', '#ffbd2e', '#27c93f'].forEach(color => {
            const dot = document.createElement('div');
            Object.assign(dot.style, {
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: color,
                boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.1)'
            });
            trafficLights.appendChild(dot);
        });

        // Title Text
        const title = document.createElement('span');
        title.textContent = 'Vertex AI Harvester';
        Object.assign(title.style, {
            marginLeft: '12px',
            color: 'rgba(255, 255, 255, 0.6)',
            fontSize: '12px',
            fontWeight: '500',
            letterSpacing: '0.3px'
        });

        titleBar.appendChild(trafficLights);
        titleBar.appendChild(title);

        // Log Content Area
        logContent = document.createElement('div');
        Object.assign(logContent.style, {
            flex: '1',
            padding: '10px',
            overflowY: 'auto',
            color: '#e0e0e0',
            fontSize: '11px',
            fontFamily: '"Menlo", "Monaco", "Courier New", monospace',
            lineHeight: '1.4',
            whiteSpace: 'pre-wrap'
        });

        // Custom Scrollbar CSS
        const style = document.createElement('style');
        style.textContent = `
            .harvester-log::-webkit-scrollbar { width: 8px; }
            .harvester-log::-webkit-scrollbar-track { background: transparent; }
            .harvester-log::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
            .harvester-log::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.3); }
        `;
        logContent.classList.add('harvester-log');

        logContainer.appendChild(style);
        logContainer.appendChild(titleBar);
        logContainer.appendChild(logContent);
        document.body.appendChild(logContainer);
    }

    function logToScreen(message) {
        console.log(message);
        createUI();
        
        const entry = document.createElement('div');
        Object.assign(entry.style, {
            marginBottom: '4px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
            paddingBottom: '2px'
        });

        const time = document.createElement('span');
        time.textContent = `[${new Date().toLocaleTimeString()}] `;
        time.style.color = 'rgba(255, 255, 255, 0.4)';
        
        const text = document.createElement('span');
        text.textContent = message;
        
        // Color coding based on message type
        if (message.includes('✅')) text.style.color = '#4cd964';
        else if (message.includes('❌') || message.includes('⚠️')) text.style.color = '#ff3b30';
        else if (message.includes('🔄') || message.includes('🚀')) text.style.color = '#0a84ff';
        else text.style.color = '#e0e0e0';

        entry.appendChild(time);
        entry.appendChild(text);
        
        logContent.appendChild(entry);
        logContent.scrollTop = logContent.scrollHeight;
    }

    // --- WebSocket Communication ---
    let socket = null;
    const WEBSOCKET_URL = 'ws://127.0.0.1:28881';
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 10;

    function connect() {
        try {
            socket = new WebSocket(WEBSOCKET_URL);
            
            socket.onopen = () => {
                logToScreen(`✅ Connected to ${WEBSOCKET_URL}`);
                reconnectAttempts = 0; // 重置重连计数
                // Identify as harvester
                socket.send(JSON.stringify({ type: 'identify', client: 'harvester' }));
            };
            
            socket.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'refresh_token') {
                        logToScreen('🔄 Received refresh request from backend.');
                        attemptRefresh().catch(err => {
                            logToScreen(`❌ Refresh failed: ${err}`);
                        });
                    } else if (msg.type === 'ping') {
                        // 响应心跳
                        socket.send(JSON.stringify({ type: 'pong' }));
                    }
                } catch (e) {
                    console.error('WS Parse Error', e);
                    logToScreen(`⚠️ WebSocket message parse error: ${e}`);
                }
            };

            socket.onclose = (event) => {
                logToScreen(`🔌 WebSocket disconnected (Code: ${event.code})`);
                reconnectAttempts++;
                
                if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
                    const delay = Math.min(2000 * reconnectAttempts, 30000); // 最多等待 30 秒
                    logToScreen(`🔄 Reconnecting in ${delay/1000}s... (Attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
                    setTimeout(connect, delay);
                } else {
                    logToScreen(`❌ Max reconnection attempts reached. Please refresh the page.`);
                }
            };
            
            socket.onerror = (err) => {
                console.error('WS Error', err);
                logToScreen(`⚠️ WebSocket error occurred`);
            };
        } catch (e) {
            logToScreen(`❌ WebSocket connection failed: ${e}`);
            reconnectAttempts++;
            if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
                setTimeout(connect, 2000);
            }
        }
    }

    function findSiteKey() {
        // Try to find SiteKey in DOM if not yet captured
        if (window.__LAST_RECAPTCHA_SITEKEY__) return window.__LAST_RECAPTCHA_SITEKEY__;

        // Method 1: Look for .g-recaptcha elements
        const el = document.querySelector('.g-recaptcha, [data-sitekey]');
        if (el && el.getAttribute('data-sitekey')) {
            const key = el.getAttribute('data-sitekey');
            logToScreen(`🔍 Found SiteKey in DOM: ${key}`);
            window.__LAST_RECAPTCHA_SITEKEY__ = key;
            return key;
        }
        
        // Method 2: Look for common Google Cloud Console config objects
        // This is harder as it's minified, but sometimes exposed.
        
        return null;
    }

    const TARGET_REFRESH_URL = 'https://console.cloud.google.com/vertex-ai/studio/multimodal?mode=prompt&model=gemini-2.5-flash-lite-preview-09-2025';
    const TARGET_MODEL_PARAM = 'model=gemini-2.5-flash-lite-preview-09-2025';
    const REFRESH_FLAG_KEY = '__HARVESTER_REFRESH_PENDING__';

    async function attemptRefresh() {
        logToScreen('🤖 Starting Auto-Refresh Sequence...');
        
        try {
            // Check if we are on the correct URL (looser check)
            // We check if the URL contains the specific model parameter
            if (!window.location.href.includes(TARGET_MODEL_PARAM)) {
                logToScreen(`🔄 Redirecting to target model URL for refresh...`);
                logToScreen(`   Current: ${window.location.href}`);
                logToScreen(`   Target:  ${TARGET_REFRESH_URL}`);
                
                sessionStorage.setItem(REFRESH_FLAG_KEY, 'true');
                window.location.href = TARGET_REFRESH_URL;
                return;
            }

            // 等待页面完全加载
            await waitForPageReady();
            
            // If we are already on the URL, proceed to send message
            await sendDummyMessage();
            logToScreen('✅ Auto-refresh sequence completed.');
            
            // Notify backend that the UI is stable and ready for retries
            // Add a small delay to ensure the model has responded and the token is validated
            setTimeout(() => {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({ type: 'refresh_complete' }));
                    logToScreen('👍 Sent refresh completion signal to backend (after delay).');
                }
            }, 1500); // 1.5 second delay
        } catch (e) {
            logToScreen(`❌ Auto-refresh failed: ${e}`);
            // 通知后端刷新失败
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: 'refresh_failed', error: e.toString() }));
            }
        }
    }

    // 等待页面完全加载就绪
    async function waitForPageReady() {
        const MAX_WAIT = 10000; // 10 秒超时
        const startTime = Date.now();
        
        logToScreen('⏳ Waiting for page to be ready...');
        
        while (Date.now() - startTime < MAX_WAIT) {
            // 检查页面是否加载完成
            if (document.readyState === 'complete') {
                // 检查是否能找到编辑器
                const editor = await findEditor();
                if (editor) {
                    logToScreen('✅ Page is ready.');
                    await new Promise(r => setTimeout(r, 500)); // 额外等待一点时间
                    return;
                }
            }
            await new Promise(r => setTimeout(r, 500));
        }
        
        logToScreen('⚠️ Page ready timeout, proceeding anyway...');
    }

    // 关闭页面上的 overlay 遮罩层
    async function dismissOverlays() {
        try {
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
            
            // 3. 移除阻挡的 overlay 容器内容（最后手段）
            const overlayContainer = document.querySelector('.cdk-overlay-container');
            if (overlayContainer) {
                // 检查是否有活跃的 backdrop
                const activeBackdrop = overlayContainer.querySelector('.cdk-overlay-backdrop-showing');
                if (activeBackdrop) {
                    // 尝试找到并点击关闭按钮
                    const closeButtons = overlayContainer.querySelectorAll(
                        'button[aria-label*="close"], button[aria-label*="Close"], ' +
                        'button[aria-label*="关闭"], .mat-dialog-close, ' +
                        'button.close, [mat-dialog-close]'
                    );
                    closeButtons.forEach(btn => btn.click());
                }
            }
            
            // 等待 overlay 动画完成
            await new Promise(r => setTimeout(r, 300));
            
        } catch (e) {
            logToScreen(`⚠️ 关闭 overlay 时出错: ${e}`);
        }
    }

    async function sendDummyMessage() {
        const MAX_RETRIES = 5;
        let attempts = 0;

        while (attempts < MAX_RETRIES) {
            attempts++;
            try {
                // 先关闭任何可能存在的 overlay 遮罩层
                await dismissOverlays();
                
                // 智能查找编辑器 - 多种选择器策略
                const editor = await findEditor();
                
                if (!editor) {
                    logToScreen(`⚠️ Editor not found (Attempt ${attempts}/${MAX_RETRIES}). Waiting...`);
                    await new Promise(r => setTimeout(r, 1000));
                    continue;
                }

                logToScreen(`✍️ Entering "Hello" (Attempt ${attempts})...`);
                
                // 确保编辑器获得焦点
                await ensureFocus(editor);
                
                // 设置文本内容
                await setEditorContent(editor, 'Hello');
                
                // 触发输入事件
                editor.dispatchEvent(new Event('input', { bubbles: true }));
                editor.dispatchEvent(new Event('change', { bubbles: true }));
                await new Promise(r => setTimeout(r, 500));

                logToScreen('🚀 Attempting to send message...');
                
                // 尝试多种发送方法
                const sent = await trySendMessage(editor);
                
                if (sent) {
                    logToScreen('✅ Message sent successfully.');
                    return;
                }
                
                logToScreen(`⚠️ Send failed on attempt ${attempts}. Retrying...`);
                
            } catch (e) {
                // 检查是否是 overlay 遮挡错误
                if (e.toString().includes('intercepts pointer events') ||
                    e.toString().includes('not clickable')) {
                    logToScreen(`⚠️ 检测到 overlay 遮挡，尝试关闭...`);
                    await dismissOverlays();
                    await new Promise(r => setTimeout(r, 500));
                } else {
                    logToScreen(`❌ Error in send attempt: ${e}`);
                }
            }
            
            await new Promise(r => setTimeout(r, 1000));
        }
        throw "Failed to send message after multiple attempts";
    }

    // 智能查找编辑器元素
    async function findEditor() {
        const selectors = [
            'textarea[aria-label*="message"]',
            'div[contenteditable="true"]',
            'textarea[placeholder*="message" i]',
            'textarea[placeholder*="prompt" i]',
            'textarea[placeholder*="消息"]',
            'div[role="textbox"]',
            'div.input-field[contenteditable="true"]',
            '[data-placeholder][contenteditable="true"]'
        ];
        
        for (const selector of selectors) {
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {
                // 检查元素是否可见且可编辑
                if (isElementVisible(el) && !el.disabled && !el.readOnly) {
                    logToScreen(`🔍 Found editor using: ${selector}`);
                    return el;
                }
            }
        }
        return null;
    }

    // 检查元素是否可见
    function isElementVisible(el) {
        if (!el) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' &&
               style.visibility !== 'hidden' &&
               style.opacity !== '0' &&
               el.offsetParent !== null;
    }

    // 确保编辑器获得焦点
    async function ensureFocus(editor) {
        editor.focus();
        editor.click();
        
        // 尝试将光标移到末尾
        if (window.getSelection && document.createRange) {
            const range = document.createRange();
            range.selectNodeContents(editor);
            range.collapse(false);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        }
        
        await new Promise(r => setTimeout(r, 200));
    }

    // 设置编辑器内容
    async function setEditorContent(editor, text) {
        if (editor.tagName.toLowerCase() === 'textarea' || editor.tagName.toLowerCase() === 'input') {
            editor.value = text;
        } else {
            editor.textContent = text;
            // 尝试设置 innerHTML 以防某些框架需要
            if (editor.innerHTML !== text) {
                editor.innerHTML = text;
            }
        }
    }

    // 尝试发送消息 - 多种策略
    async function trySendMessage(editor) {
        // 策略 0: 使用 JavaScript 直接操作（绕过 overlay）
        const jsSent = await tryJavaScriptSend(editor);
        if (jsSent) return true;
        
        // 策略 1: Enter 键
        const enterSent = await tryEnterKey(editor);
        if (enterSent) return true;
        
        // 策略 2: Ctrl+Enter 组合键
        const ctrlEnterSent = await tryCtrlEnter(editor);
        if (ctrlEnterSent) return true;
        
        // 策略 3: 点击发送按钮
        const buttonSent = await tryClickSendButton(editor);
        if (buttonSent) return true;
        
        return false;
    }

    // 尝试使用 JavaScript 直接发送（绕过 overlay 问题）
    async function tryJavaScriptSend(editor) {
        logToScreen('   → Trying JavaScript direct send...');
        try {
            // 使用 JavaScript 直接聚焦和输入
            const success = (() => {
                // 关闭所有 overlay
                const overlays = document.querySelectorAll('.cdk-overlay-backdrop, .cdk-overlay-container > *');
                overlays.forEach(el => {
                    if (el.classList.contains('cdk-overlay-backdrop')) {
                        el.click();  // 点击背景关闭
                    }
                });
                
                // 查找输入框
                const selectors = [
                    'textarea[aria-label*="message"]',
                    'div[contenteditable="true"]',
                    'textarea[placeholder*="message"]',
                    'textarea[placeholder*="消息"]'
                ];
                
                let input = null;
                for (const sel of selectors) {
                    input = document.querySelector(sel);
                    if (input && input.offsetParent !== null) break;
                    input = null;
                }
                
                if (!input) return false;
                
                // 聚焦输入框
                input.focus();
                
                // 设置内容
                if (input.tagName === 'TEXTAREA') {
                    input.value = 'Hello';
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                } else {
                    // contenteditable
                    input.textContent = 'Hello';
                    input.dispatchEvent(new InputEvent('input', { bubbles: true, data: 'Hello' }));
                }
                
                return true;
            })();
            
            if (!success) {
                return false;
            }
            
            await new Promise(r => setTimeout(r, 100));
            
            // 按回车发送
            const enterEvent = new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            editor.dispatchEvent(enterEvent);
            
            await new Promise(r => setTimeout(r, 1000));
            return isEditorCleared(editor);
            
        } catch (e) {
            logToScreen(`   ⚠️ JavaScript send failed: ${e}`);
            return false;
        }
    }

    // 尝试 Enter 键发送
    async function tryEnterKey(editor) {
        logToScreen('   → Trying Enter key...');
        const enterEvent = new KeyboardEvent('keydown', {
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true,
            cancelable: true
        });
        editor.dispatchEvent(enterEvent);
        
        await new Promise(r => setTimeout(r, 1000));
        return isEditorCleared(editor);
    }

    // 尝试 Ctrl+Enter 组合键
    async function tryCtrlEnter(editor) {
        logToScreen('   → Trying Ctrl+Enter...');
        const ctrlEnterEvent = new KeyboardEvent('keydown', {
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            ctrlKey: true,
            bubbles: true,
            cancelable: true
        });
        editor.dispatchEvent(ctrlEnterEvent);
        
        await new Promise(r => setTimeout(r, 1000));
        return isEditorCleared(editor);
    }

    // 尝试点击发送按钮
    async function tryClickSendButton(editor) {
        logToScreen('   → Trying send button...');
        
        const buttonSelectors = [
            'button[aria-label*="Send" i]',
            'button[aria-label*="发送" i]',
            'button[type="submit"]',
            'button:has(svg[data-icon="send"])',
            'button:has(.send-icon)',
            '[role="button"][aria-label*="send" i]'
        ];
        
        for (const selector of buttonSelectors) {
            const buttons = document.querySelectorAll(selector);
            for (const btn of buttons) {
                if (isElementVisible(btn) && !btn.disabled) {
                    logToScreen(`   → Found button: ${selector}`);
                    btn.click();
                    await new Promise(r => setTimeout(r, 1000));
                    if (isEditorCleared(editor)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    // 检查编辑器是否已清空
    function isEditorCleared(editor) {
        const content = (editor.value || editor.textContent || editor.innerText || '').trim();
        return content === '';
    }

    // --- Auto-Keepalive ---
    // Once we have the SiteKey, refresh automatically every 4 minutes
    setInterval(() => {
        if (window.__LAST_RECAPTCHA_SITEKEY__) {
            logToScreen('⏰ Auto-refreshing token (Keepalive)...');
            attemptRefresh();
        }
    }, 4 * 60 * 1000); // 4 minutes

    function sendCredentials(data) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: 'credentials_harvested',
                data: data
            }));
            logToScreen(`📤 Sent captured request data to backend.`);
        }
    }

    // --- reCAPTCHA Hook ---
    function hookRecaptcha() {
        // Hook into window.grecaptcha to capture site keys and potentially trigger executions
        let originalExecute = null;
        
        const hook = (grecaptchaInstance) => {
             if (grecaptchaInstance && grecaptchaInstance.execute && !grecaptchaInstance._hooked) {
                logToScreen('🎣 reCAPTCHA detected. Hooking execute...');
                originalExecute = grecaptchaInstance.execute;
                grecaptchaInstance.execute = function(siteKey, options) {
                    logToScreen(`🔑 reCAPTCHA execute called. SiteKey: ${siteKey}`);
                    // Store for potential reuse/refresh logic
                    window.__LAST_RECAPTCHA_SITEKEY__ = siteKey;
                    window.__LAST_RECAPTCHA_OPTIONS__ = options;
                    return originalExecute.apply(this, arguments);
                };
                grecaptchaInstance._hooked = true;
            }
        };

        if (window.grecaptcha) {
            hook(window.grecaptcha);
        }

        // Also define a setter on window in case it loads later
        let _grecaptcha = window.grecaptcha;
        Object.defineProperty(window, 'grecaptcha', {
            configurable: true,
            get: function() { return _grecaptcha; },
            set: function(val) {
                _grecaptcha = val;
                hook(val);
            }
        });
    }

    // --- Interceptor ---
    function intercept() {
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;
        const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;

        XMLHttpRequest.prototype.open = function(method, url) {
            this._url = url;
            this._method = method;
            this._headers = {};
            originalOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
            this._headers[header] = value;
            originalSetRequestHeader.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function(body) {
            // Filter for the target request
            // We look for 'batchGraphql' which usually carries the chat payload
            if (this._url && this._url.includes('batchGraphql')) {
                try {
                    // Log ALL batchGraphql requests to console for debugging
                    console.log('🔍 Intercepted batchGraphql:', body);

                    // Only capture if it looks like a chat generation request
                    // This avoids capturing billing/monitoring requests
                    // Added 'Predict' and 'Image' to catch more variations
                    if (body && (body.includes('StreamGenerateContent') || body.includes('generateContent') || body.includes('Predict') || body.includes('Image'))) {
                        logToScreen(`🎯 Captured Target Request: ${this._url.substring(0, 50)}...`);
                        
                        // Pretty print the body to screen for user inspection
                        try {
                            const parsedBody = JSON.parse(body);
                            // Try to extract variables for cleaner display
                            const variables = parsedBody.variables || parsedBody;
                            logToScreen(`📦 Payload: ${JSON.stringify(variables, null, 2)}`);
                        } catch (e) {
                            logToScreen(`📦 Payload (Raw): ${body.substring(0, 200)}...`);
                        }

                        // Merge captured headers with browser defaults that XHR adds automatically
                        const finalHeaders = {
                            ...this._headers,
                            'Cookie': document.cookie,
                            'User-Agent': navigator.userAgent,
                            'Origin': window.location.origin,
                            'Referer': window.location.href
                        };

                        const harvestData = {
                            url: this._url,
                            method: this._method,
                            headers: finalHeaders,
                            body: body
                        };

                        // --- DEBUG: Log Captured Parameters to Screen ---
                        try {
                            const jsonBody = JSON.parse(body);
                            if (jsonBody.variables && jsonBody.variables.generationConfig) {
                                const genConfig = jsonBody.variables.generationConfig;
                                logToScreen(`🔍 Captured Generation Config:\n${JSON.stringify(genConfig, null, 2)}`);
                            } else {
                                logToScreen(`⚠️ Captured request but no generationConfig found.`);
                            }
                        } catch (parseErr) {
                            logToScreen(`⚠️ Could not parse request body for logging: ${parseErr}`);
                        }
                        // ------------------------------------------------
                        
                        // Send immediately
                        sendCredentials(harvestData);
                    }
                } catch (e) {
                    console.error('Error analyzing request:', e);
                }
            }
            originalSend.apply(this, arguments);
        };
    }

    // --- Init ---
    function initialize() {
        try {
            connect();
            intercept();
            hookRecaptcha();
            logToScreen('✅ Harvester Armed. Please send a message in Vertex AI Studio.');

            // Check for pending refresh
            if (sessionStorage.getItem(REFRESH_FLAG_KEY) === 'true') {
                logToScreen('🔄 Resuming refresh sequence after redirect...');
                sessionStorage.removeItem(REFRESH_FLAG_KEY);
                // Wait a bit for the editor to be ready
                setTimeout(() => {
                    attemptRefresh().catch(err => {
                        logToScreen(`❌ Resume refresh failed: ${err}`);
                    });
                }, 5000); // 5 seconds delay to ensure page load
            }
        } catch (e) {
            logToScreen(`❌ Initialization failed: ${e}`);
            console.error('Harvester Init Error:', e);
        }
    }

    // 监听 DOM 加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        // DOM 已经加载完成
        initialize();
    }

    // 页面可见性变化时重新连接（如果断开）
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                logToScreen('👀 Page became visible, checking connection...');
                setTimeout(() => {
                    if (!socket || socket.readyState !== WebSocket.OPEN) {
                        logToScreen('🔄 Reconnecting WebSocket...');
                        connect();
                    }
                }, 1000);
            }
        }
    });

    // 全局错误处理
    window.addEventListener('error', (event) => {
        console.error('Global Error:', event.error);
    });

    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled Promise Rejection:', event.reason);
    });

})();