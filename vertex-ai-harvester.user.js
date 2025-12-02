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

    function connect() {
        socket = new WebSocket(WEBSOCKET_URL);
        socket.onopen = () => {
            logToScreen(`✅ Connected to ${WEBSOCKET_URL}`);
            // Identify as harvester
            socket.send(JSON.stringify({ type: 'identify', client: 'harvester' }));
        };
        
        socket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'refresh_token') {
                    logToScreen('🔄 Received refresh request from backend.');
                    attemptRefresh();
                }
            } catch (e) {
                console.error('WS Parse Error', e);
            }
        };

        socket.onclose = () => setTimeout(connect, 2000);
        socket.onerror = (err) => console.error('WS Error', err);
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

        // If we are already on the URL, proceed to send message
        try {
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
        }
    }

    async function sendDummyMessage() {
        const MAX_RETRIES = 5;
        let attempts = 0;

        while (attempts < MAX_RETRIES) {
            attempts++;
            try {
                // Find editor - prioritize contenteditable div
                const editor = document.querySelector('div[contenteditable="true"]');
                
                if (!editor) {
                    logToScreen(`⚠️ Editor not found (Attempt ${attempts}/${MAX_RETRIES}). Waiting...`);
                    await new Promise(r => setTimeout(r, 1000));
                    continue;
                }

                logToScreen(`✍️ Entering "Hello" (Attempt ${attempts})...`);
                
                editor.focus();
                editor.click(); // Ensure focus
                
                // Set text content directly
                editor.textContent = 'Hello'; // Use a simple, short message
                
                // Dispatch input events to trigger framework bindings
                editor.dispatchEvent(new Event('input', { bubbles: true }));
                await new Promise(r => setTimeout(r, 500));

                logToScreen('🚀 Pressing Enter to send...');
                const enterEvent = new KeyboardEvent('keydown', {
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true,
                    cancelable: true
                });
                editor.dispatchEvent(enterEvent);
                
                // Check if text was cleared (success indicator)
                await new Promise(r => setTimeout(r, 1000));
                if (editor.textContent.trim() === '') {
                    logToScreen('✅ Message sent successfully (Editor cleared).');
                    return;
                }
                
                // If Enter failed, try clicking send button once, but don't retry the whole block
                logToScreen('⚠️ Editor not cleared. Trying send button...');
                const sendBtn = document.querySelector('button[aria-label*="Send"]');
                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                    await new Promise(r => setTimeout(r, 1000));
                    if (editor.textContent.trim() === '') {
                        logToScreen('✅ Message sent successfully (Send button cleared).');
                        return;
                    }
                }
                
                // If we reach here, neither method worked in this attempt.
                
            } catch (e) {
                logToScreen(`❌ Error in send attempt: ${e}`);
            }
            
            await new Promise(r => setTimeout(r, 1000));
        }
        throw "Failed to send message after multiple attempts";
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
    window.addEventListener('DOMContentLoaded', () => {
        connect();
        intercept();
        hookRecaptcha();
        logToScreen('Harvester Armed. Please send a message in Vertex AI Studio.');

        // Check for pending refresh
        if (sessionStorage.getItem(REFRESH_FLAG_KEY) === 'true') {
            logToScreen('🔄 Resuming refresh sequence after redirect...');
            sessionStorage.removeItem(REFRESH_FLAG_KEY);
            // Wait a bit for the editor to be ready
            setTimeout(() => {
                attemptRefresh();
            }, 5000); // 5 seconds delay to ensure page load
        }
    });

})();