// ==UserScript==
// @name         Vertex AI Credential Harvester v1.1
// @namespace    http://tampermonkey.net/
// @version      1.1
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

    console.log('Harvester v1.1: Initializing...');

    // --- 全局状态管理 ---
    let isRefreshing = false;  // 防止重复刷新
    let lastCredentialTime = 0;  // 上次获取凭证的时间
    let connectionAttempts = 0;  // 连接尝试次数
    let heartbeatInterval = null;  // 心跳定时器

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

    // --- Web Worker for Reliable Timers ---
    let keepaliveWorker = null;

    function startKeepaliveWorker() {
        const workerCode = () => {
            // Worker is not affected by background tab throttling
            const HEARTBEAT_INTERVAL = 30000;  // 30 seconds
            const KEEPALIVE_CHECK_INTERVAL = 60000; // 1 minute

            // Heartbeat
            setInterval(() => {
                self.postMessage({ command: 'ping' });
            }, HEARTBEAT_INTERVAL);

            // Refresh check
            setInterval(() => {
                self.postMessage({ command: 'check_refresh' });
            }, KEEPALIVE_CHECK_INTERVAL);
        };

        try {
            const blob = new Blob(['(', workerCode.toString(), ')()'], { type: 'application/javascript' });
            const url = URL.createObjectURL(blob);
            keepaliveWorker = new Worker(url);

            keepaliveWorker.onmessage = (e) => {
                const { command } = e.data;
                if (command === 'ping') {
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: 'ping' }));
                    }
                } else if (command === 'check_refresh') {
                    // This replaces the old setInterval-based keepalive
                    if (window.__LAST_RECAPTCHA_SITEKEY__ && !isRefreshing) {
                        const timeSinceLastCred = Date.now() - lastCredentialTime;
                        if (timeSinceLastCred > CREDENTIAL_REFRESH_INTERVAL) {
                            logToScreen('⏱️ Auto-refreshing token (Keepalive via Worker)...');
                            attemptRefresh();
                        }
                    }
                }
            };
            logToScreen('✅ Keepalive Worker started successfully.');
            URL.revokeObjectURL(url); // Clean up
        } catch (e) {
            logToScreen(`❌ Failed to start Keepalive Worker: ${e}`);
            // Fallback to less reliable setInterval if worker fails
            startHeartbeat();
            startLegacyKeepalive();
        }
    }


    // --- WebSocket Communication ---
    let socket = null;
    const WEBSOCKET_URL = 'ws://127.0.0.1:28881';
    const CREDENTIAL_REFRESH_INTERVAL = 3 * 60 * 1000;  // 3分钟自动刷新

    function connect() {
        connectionAttempts++;
        logToScreen(`🔄 Connecting to backend (attempt ${connectionAttempts})...`);

        try {
            socket = new WebSocket(WEBSOCKET_URL);
        } catch (e) {
            logToScreen(`❌ WebSocket creation failed: ${e}`);
            scheduleReconnect();
            return;
        }

        socket.onopen = () => {
            logToScreen(`✅ Connected to ${WEBSOCKET_URL}`);
            connectionAttempts = 0;  // 重置连接计数

            // Identify as harvester
            socket.send(JSON.stringify({ type: 'identify', client: 'harvester' }));

            // 启动心跳 (由Worker管理)
            // startHeartbeat(); // This is now handled by the worker

            // 连接成功后，如果凭证过期或不存在，自动刷新
            const timeSinceLastCred = Date.now() - lastCredentialTime;
            if (lastCredentialTime === 0 || timeSinceLastCred > CREDENTIAL_REFRESH_INTERVAL) {
                logToScreen('🔄 Auto-refreshing credentials on connect...');
                setTimeout(() => attemptRefresh(), 2000);  // 等待页面稳定
            }
        };

        socket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'refresh_token') {
                    logToScreen('🔄 Received refresh request from backend.');
                    if (!isRefreshing) {
                        attemptRefresh();
                    } else {
                        logToScreen('⚠️ Refresh already in progress, skipping...');
                    }
                } else if (msg.type === 'hello') {
                    logToScreen('👋 Backend handshake received.');
                } else if (msg.type === 'pong') {
                    // 心跳响应
                }
            } catch (e) {
                console.error('WS Parse Error', e);
            }
        };

        socket.onclose = (event) => {
            logToScreen(`⚠️ WebSocket closed (code: ${event.code})`);
            // stopHeartbeat(); // Worker will continue trying to send pings
            scheduleReconnect();
        };

        socket.onerror = (err) => {
            console.error('WS Error', err);
            logToScreen('❌ WebSocket error occurred');
        };
    }

    function scheduleReconnect() {
        // 使用指数退避策略
        const delay = Math.min(2000 * Math.pow(1.5, connectionAttempts), 30000);
        logToScreen(`🔄 Reconnecting in ${Math.round(delay/1000)}s...`);
        setTimeout(connect, delay);
    }

    // DEPRECATED: The old heartbeat functions are no longer needed as the worker handles this.
    // They are kept here as a potential fallback if the worker fails to initialize.
    function startHeartbeat() {
        stopHeartbeat();  // 清除旧的心跳
        heartbeatInterval = setInterval(() => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Hardcoded interval for fallback
    }

    function stopHeartbeat() {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
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
        if (isRefreshing) {
            logToScreen('⚠️ Refresh already in progress, skipping...');
            return;
        }

        isRefreshing = true;
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
                return;  // isRefreshing 会在页面加载后重置
            }

            // 等待页面完全加载
            await waitForPageReady();

            // If we are already on the URL, proceed to send message
            await sendDummyMessage();
            logToScreen('✅ Auto-refresh sequence completed.');
            lastCredentialTime = Date.now();

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
                socket.send(JSON.stringify({ type: 'refresh_failed', error: String(e) }));
            }
        } finally {
            isRefreshing = false;
        }
    }

    async function waitForPageReady() {
        const MAX_WAIT = 15000;  // 最多等待15秒
        const CHECK_INTERVAL = 500;  // 每500ms检查一次
        let waited = 0;

        while (waited < MAX_WAIT) {
            // 检查编辑器是否存在
            const editor = document.querySelector('div[contenteditable="true"]');
            if (editor) {
                logToScreen('✅ Page ready - editor found');
                return;
            }

            await new Promise(r => setTimeout(r, CHECK_INTERVAL));
            waited += CHECK_INTERVAL;
        }

        throw new Error('Page did not become ready in time');
    }

    async function sendDummyMessage() {
        const MAX_RETRIES = 8;
        let attempts = 0;

        while (attempts < MAX_RETRIES) {
            attempts++;
            try {
                // Find editor - prioritize contenteditable div
                const editor = document.querySelector('div[contenteditable="true"]');

                if (!editor) {
                    logToScreen(`⚠️ Editor not found (Attempt ${attempts}/${MAX_RETRIES}). Waiting...`);
                    await new Promise(r => setTimeout(r, 1500));
                    continue;
                }

                // 检查编辑器是否可见和可交互
                const rect = editor.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) {
                    logToScreen(`⚠️ Editor not visible (Attempt ${attempts}/${MAX_RETRIES}). Waiting...`);
                    await new Promise(r => setTimeout(r, 1000));
                    continue;
                }

                logToScreen(`✍️ Entering "Hello" (Attempt ${attempts})...`);

                // 清除现有内容 - 使用 textContent 而非 innerHTML 以避免 Trusted Types 错误
                editor.textContent = '';
                await new Promise(r => setTimeout(r, 100));

                editor.focus();
                editor.click(); // Ensure focus

                // 使用多种方法尝试输入文本
                // Method 1: 直接设置 textContent
                editor.textContent = 'Hello';

                // Method 2: 如果 textContent 不生效，尝试使用 Selection API
                if (editor.textContent.trim() === '') {
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(editor);
                    range.collapse(false);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    document.execCommand('insertText', false, 'Hello');
                }

                // Method 3: 如果还是不行，尝试使用 InputEvent
                if (editor.textContent.trim() === '') {
                    const inputEvent = new InputEvent('beforeinput', {
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertText',
                        data: 'Hello'
                    });
                    editor.dispatchEvent(inputEvent);
                }

                // Dispatch multiple events to trigger framework bindings
                editor.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
                editor.dispatchEvent(new Event('change', { bubbles: true }));
                await new Promise(r => setTimeout(r, 600));

                logToScreen('🚀 Pressing Enter to send...');

                // 尝试多种方式发送
                // Method 1: KeyboardEvent
                const enterEvent = new KeyboardEvent('keydown', {
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true,
                    cancelable: true,
                    composed: true
                });
                editor.dispatchEvent(enterEvent);

                // Check if text was cleared (success indicator)
                await new Promise(r => setTimeout(r, 1200));
                if (editor.textContent.trim() === '') {
                    logToScreen('✅ Message sent successfully (Editor cleared).');
                    return;
                }

                // Method 2: Try clicking send button
                logToScreen('⚠️ Editor not cleared. Trying send button...');

                // 尝试多种选择器找到发送按钮
                const sendBtnSelectors = [
                    'button[aria-label*="Send"]',
                    'button[aria-label*="send"]',
                    'button[data-testid*="send"]',
                    'button.send-button',
                    '[role="button"][aria-label*="Send"]'
                ];

                let sendBtn = null;
                for (const selector of sendBtnSelectors) {
                    sendBtn = document.querySelector(selector);
                    if (sendBtn && !sendBtn.disabled) break;
                }

                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                    await new Promise(r => setTimeout(r, 1200));
                    if (editor.textContent.trim() === '') {
                        logToScreen('✅ Message sent successfully (Send button).');
                        return;
                    }
                }

                // Method 3: Try pressing Enter on the button
                if (sendBtn) {
                    sendBtn.focus();
                    sendBtn.dispatchEvent(enterEvent);
                    await new Promise(r => setTimeout(r, 1000));
                    if (editor.textContent.trim() === '') {
                        logToScreen('✅ Message sent successfully (Button Enter).');
                        return;
                    }
                }

                logToScreen(`⚠️ Send attempt ${attempts} failed, retrying...`);

            } catch (e) {
                logToScreen(`❌ Error in send attempt: ${e}`);
            }

            await new Promise(r => setTimeout(r, 1500));
        }
        throw "Failed to send message after multiple attempts";
    }

    // --- Auto-Keepalive (Now handled by Web Worker) ---
    function startLegacyKeepalive() {
        logToScreen('⚠️ Using legacy setInterval for keepalive.');
        setInterval(() => {
            if (window.__LAST_RECAPTCHA_SITEKEY__ && !isRefreshing) {
                const timeSinceLastCred = Date.now() - lastCredentialTime;
                if (timeSinceLastCred > CREDENTIAL_REFRESH_INTERVAL) {
                    logToScreen('⏰ Auto-refreshing token (Legacy Keepalive)...');
                    attemptRefresh();
                }
            }
        }, 60 * 1000); // 每分钟检查一次
    }


    function sendCredentials(data) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: 'credentials_harvested',
                data: data
            }));
            lastCredentialTime = Date.now();
            logToScreen(`📤 Sent captured request data to backend.`);
        } else {
            logToScreen(`⚠️ Cannot send credentials - WebSocket not connected`);
            // 尝试重新连接
            if (!socket || socket.readyState === WebSocket.CLOSED) {
                connect();
            }
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
    window.addEventListener('DOMContentLoaded', () => {
        connect();
        intercept();
        hookRecaptcha();
        startKeepaliveWorker(); // Start the reliable timer
        logToScreen('Harvester v1.1 Armed. Please send a message in Vertex AI Studio.');

        // Check for pending refresh
        if (sessionStorage.getItem(REFRESH_FLAG_KEY) === 'true') {
            logToScreen('🔄 Resuming refresh sequence after redirect...');
            sessionStorage.removeItem(REFRESH_FLAG_KEY);
            isRefreshing = true;  // 标记正在刷新
            // Wait a bit for the editor to be ready
            setTimeout(async () => {
                try {
                    await waitForPageReady();
                    await sendDummyMessage();
                    logToScreen('✅ Refresh completed after redirect.');
                    lastCredentialTime = Date.now();

                    setTimeout(() => {
                        if (socket && socket.readyState === WebSocket.OPEN) {
                            socket.send(JSON.stringify({ type: 'refresh_complete' }));
                            logToScreen('👍 Sent refresh completion signal to backend.');
                        }
                    }, 1500);
                } catch (e) {
                    logToScreen(`❌ Refresh after redirect failed: ${e}`);
                } finally {
                    isRefreshing = false;
                }
            }, 3000); // 3 seconds delay to ensure page load
        }
    });

    // 页面可见性变化时的处理
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            logToScreen('👁️ Page became visible');
            // 检查WebSocket连接状态
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                logToScreen('🔄 Reconnecting WebSocket...');
                connect();
            }
        }
    });

    // 页面卸载前清理
    window.addEventListener('beforeunload', () => {
        stopHeartbeat();
        if (socket) {
            socket.close();
        }
    });

})();