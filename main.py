import asyncio
import json
import time
import uuid
import httpx
import uvicorn
import sys
import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from typing import Dict, Any, Optional, List, Generator
from stats_manager import DailyStatsManager

# --- Configuration ---
PORT_API = 7860
PORT_WS = 28881
MODELS_CONFIG_FILE = "models.json"
STATS_FILE = "stats.json"
API_KEY = os.environ.get("API_KEY", "your-secret-api-key-here").strip()  # 从环境变量读取并清理空格
print(f"\n{'='*60}")
print(f"🔑 API_KEY 配置:")
print(f"   - 来源: {'环境变量' if 'API_KEY' in os.environ else '默认值'}")
print(f"   - 长度: {len(API_KEY)} 字符")
print(f"{'='*60}\n")

# 浏览器模式配置
BROWSER_MODE = os.environ.get("BROWSER_MODE", "manual")  # manual / headful / websocket

# API Key 认证 - 使用标准的 Bearer token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security_bearer = HTTPBearer(auto_error=False)

async def verify_api_key(bearer: HTTPAuthorizationCredentials = Depends(security_bearer)):
    """验证 API Key - 使用 Authorization: Bearer <token>"""
    if not bearer or not bearer.credentials:
        raise HTTPException(
            status_code=401,
            detail="API Key is required. Please provide Authorization: Bearer <token> header."
        )
    
    token = bearer.credentials.strip()
    
    if token != API_KEY:
        print(f"⚠️ API Key 验证失败 (长度不匹配: 期望 {len(API_KEY)}, 收到 {len(token)})")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return token

# --- Token Stats Manager ---
class TokenStatsManager:
    def __init__(self, filepath=STATS_FILE):
        self.filepath = filepath
        self.stats = {"total_requests": 0, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        self.lock = asyncio.Lock()
        self.load_stats()

    def load_stats(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.stats = json.load(f)
        except FileNotFoundError:
            self.save_stats()
        except Exception as e:
            print(f"⚠️ Error loading stats: {e}")

    def save_stats(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving stats: {e}")

    async def update(self, prompt_tokens, completion_tokens):
        async with self.lock:
            self.stats["total_requests"] += 1
            self.stats["prompt_tokens"] += prompt_tokens
            self.stats["completion_tokens"] += completion_tokens
            self.stats["total_tokens"] += (prompt_tokens + completion_tokens)
            self.save_stats()

stats_manager = TokenStatsManager()
daily_stats_manager = DailyStatsManager()

# --- Credential Manager ---
class CredentialManager:
    def __init__(self, filepath="credentials.json"):
        self.filepath = filepath
        self.latest_harvest: Optional[Dict[str, Any]] = None
        self.last_updated: float = 0
        self.refresh_event = asyncio.Event() # Event to block requests during refresh
        self.refresh_complete_event = asyncio.Event() # Event to signal UI is ready after refresh
        self.refresh_lock = asyncio.Lock() # Lock to ensure only one refresh triggers at a time
        self.refresh_event.set() # Initially set (not refreshing)
        self.refresh_complete_event.set()
        self.load_from_disk()

    def load_from_disk(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容两种格式：旧格式 {'harvest': {...}} 和新格式 {...}
                if 'harvest' in data:
                    self.latest_harvest = data.get('harvest')
                    self.last_updated = data.get('timestamp', 0)
                else:
                    # 新格式直接存储凭证
                    self.latest_harvest = data
                    self.last_updated = data.get('timestamp', time.time())
                print(f"📂 Loaded credentials from disk (Age: {int(time.time() - self.last_updated)}s)")
        except FileNotFoundError:
            print("📂 No saved credentials found.")
        except Exception as e:
            print(f"⚠️ Error loading credentials: {e}")

    def save_to_disk(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                # 直接保存凭证，不嵌套在 'harvest' 键下
                json.dump(self.latest_harvest, f, indent=2)
            print(f"💾 Credentials saved to {self.filepath}")
        except Exception as e:
            print(f"⚠️ Error saving credentials: {e}")

    def update(self, data: Dict[str, Any]):
        """
        更新凭证
        
        Args:
            data: 凭证数据，格式：
                {
                    "headers": {...},
                    "cookies": "...",
                    "url": "...",
                    "body": "...",  # 必须是字符串格式
                    "timestamp": 123456
                }
        """
        # 确保 body 是字符串格式
        if 'body' in data and not isinstance(data['body'], str):
            print(f"⚠️ Warning: body is not a string, converting...")
            data['body'] = json.dumps(data['body'])
        
        self.latest_harvest = data
        self.last_updated = time.time()
        # 更新时间戳
        self.latest_harvest['timestamp'] = self.last_updated
        
        print(f"🔄 Credentials updated at {time.strftime('%H:%M:%S')}")
        self.save_to_disk()
        self.refresh_event.set() # Unblock credential waiting requests

    def update_token(self, token: str):
        if self.latest_harvest and 'headers' in self.latest_harvest:
            # Debug: Print old token prefix
            old_val = self.latest_harvest['headers'].get('X-Goog-First-Party-Reauth', 'None')
            print(f"🔍 Old Token Prefix: {old_val[:20]}...")

            # Update the specific header.
            formatted_token = json.dumps([token])
            self.latest_harvest['headers']['X-Goog-First-Party-Reauth'] = formatted_token
            
            print(f"🔍 New Token Prefix: {formatted_token[:20]}...")
            
            self.last_updated = time.time()
            print(f"🔄 Token refreshed via WebSocket at {time.strftime('%H:%M:%S')}")
            self.save_to_disk()
            self.refresh_event.set() # Unblock waiting requests

    async def wait_for_refresh(self, timeout=30):
        """Blocks until new credentials are received or timeout occurs."""
        self.refresh_event.clear() # Start blocking for credentials
        self.refresh_complete_event.clear() # Also block for UI completion signal
        try:
            print("   - Waiting for credentials...")
            await asyncio.wait_for(self.refresh_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            print("   - Timed out waiting for credentials.")
            self.refresh_complete_event.set() # Unblock the other wait if this one fails
            return False

    async def wait_for_refresh_complete(self, timeout=30):
        """Blocks until the frontend signals the refresh sequence is fully complete."""
        try:
            print("   - Waiting for frontend UI to be ready...")
            await asyncio.wait_for(self.refresh_complete_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            print("   - Timed out waiting for frontend UI.")
            return False

    def get_credentials(self) -> Optional[Dict[str, Any]]:
        if not self.latest_harvest:
            return None
        # Simple freshness check (warn if older than 10 minutes)
        # Note: Vertex AI tokens are short-lived, but cookies might last longer.
        # We'll just warn for now.
        if time.time() - self.last_updated > 1800: # 30 mins
            print("⚠️ Warning: Credentials might be stale (>30 mins old).")
        return self.latest_harvest

cred_manager = CredentialManager()

# --- 浏览器模式全局变量 ---
_headful_browser = None
_refresh_fail_count = 0
_REDIRECT_THRESHOLD = 2
_refresh_lock = None

# --- Vertex AI Client ---
class AuthError(Exception):
    """Raised when authentication fails (e.g. Recaptcha invalid)."""
    pass

class VertexAIClient:
    def __init__(self):
        # Increase connection limits for concurrency
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.client = httpx.AsyncClient(timeout=120.0, limits=limits)

    async def complete_chat(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Dict[str, Any]:
        """Aggregates the streaming response into a single non-streaming ChatCompletion object."""
        
        full_content = ""
        reasoning_content = ""
        finish_reason = "stop"
        
        # Use the existing streaming logic to get chunks
        async for chunk_data_sse in self.stream_chat(messages, model, **kwargs):
            # SSE format: "data: {json_chunk}\n\n"
            if chunk_data_sse.startswith("data: "):
                json_str = chunk_data_sse[6:].strip()
                if json_str == "[DONE]":
                    continue
                
                try:
                    chunk = json.loads(json_str)
                    choices = chunk.get('choices', [])
                    if choices:
                        delta = choices[0].get('delta', {})
                        
                        # Aggregate content
                        if 'content' in delta:
                            full_content += delta['content']
                        if 'reasoning_content' in delta:
                            reasoning_content += delta['reasoning_content']
                            
                        # Capture finish reason from the last chunk
                        if choices[0].get('finish_reason'):
                            finish_reason = choices[0]['finish_reason']
                            
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON chunk in complete_chat: {e}")
                    # Continue to next chunk
                    
        # Construct the final non-streaming response
        # Note: We are not calculating token usage here, as that requires more complex logic
        # and is usually done by the upstream API. We will use placeholders.
        
        # Combine reasoning and content if reasoning exists
        final_content = full_content
        if reasoning_content:
            final_content = f"**Reasoning:**\n{reasoning_content}\n\n**Response:**\n{full_content}"
        
        # Workaround for clients that treat empty content as failure
        if not final_content:
            final_content = " "
            
        response = {
            "id": f"chatcmpl-proxy-nonstream-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "usage": {
                "prompt_tokens": 0, # Placeholder
                "completion_tokens": 0, # Placeholder
                "total_tokens": 0 # Placeholder
            },
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_content
                    },
                    "finish_reason": finish_reason
                }
            ]
        }
        return response

    async def stream_chat(self, messages: List[Dict[str, str]], model: str, **kwargs):
        # 1. Check Credential Freshness & Auto-Refresh
        # Vertex AI tokens typically last 1 hour. We'll refresh if older than 50 mins.
        
        # Use a lock to prevent multiple requests from triggering refresh simultaneously
        if not cred_manager.latest_harvest or (time.time() - cred_manager.last_updated > 3000):
            async with cred_manager.refresh_lock:
                # Double check inside lock
                should_refresh = False
                if not cred_manager.latest_harvest:
                    should_refresh = True
                elif time.time() - cred_manager.last_updated > 3000:
                    print("⚠️ Credentials are stale (>50 mins). Triggering pre-flight refresh...")
                    should_refresh = True
                
                if should_refresh:
                    # 根据模式选择刷新策略
                    if BROWSER_MODE == "headful":
                        await headful_browser_refresh()
                    else:
                        await request_token_refresh()
                    
                    # Wait for credentials (with a timeout)
                    print("⏳ Waiting for fresh credentials...")
                    refreshed = await cred_manager.wait_for_refresh(timeout=60)
                    
                    if refreshed:
                        # Add 1 second delay after token is received and refresh_event is set
                        await asyncio.sleep(1)
                    
                    if not refreshed and not cred_manager.latest_harvest:
                        # Only fail if we have NO credentials at all.
                        error_msg = "⚠️ **Proxy Error**: Could not refresh credentials.\n\nPlease ensure **Google Vertex AI Studio** is open in your browser and the Harvester script is active."
                        chunk = {
                            "id": "error-no-creds",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "vertex-ai-proxy",
                            "choices": [{"index": 0, "delta": {"content": error_msg}, "finish_reason": "stop"}]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        return

        # 4. Send Request (with Retry Logic)
        max_retries = 1
        content_yielded = False # Track if any content chunk was yielded
        
        for attempt in range(max_retries + 1):
            
            creds = cred_manager.get_credentials()
            # Double check in case refresh failed but we have old creds
            if not creds:
                # Should be handled above, but just in case
                # If we are in a retry loop, this means refresh failed completely
                if attempt > 0:
                    break
                return # Should not happen if pre-flight check passed

            # 1. Prepare Request Data
            original_body = json.loads(creds['body'])
            
            # Extract System Prompt
            system_instruction = ""
            chat_history = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_instruction += msg['content'] + "\n"
                elif msg['role'] == 'user':
                    parts = []
                    if isinstance(msg['content'], str):
                        parts.append({"text": msg['content']})
                    elif isinstance(msg['content'], list):
                        for part in msg['content']:
                            if part['type'] == 'text':
                                parts.append({"text": part['text']})
                            elif part['type'] == 'image_url':
                                image_url = part['image_url']['url']
                                if image_url.startswith('data:'):
                                    # Extract base64 data
                                    header, encoded = image_url.split(',', 1)
                                    mime_type = header.split(':')[1].split(';')[0]
                                    parts.append({
                                        "inlineData": {
                                            "mimeType": mime_type,
                                            "data": encoded
                                        }
                                    })
                    chat_history.append({"role": "user", "parts": parts})
                elif msg['role'] == 'assistant':
                    chat_history.append({"role": "model", "parts": [{"text": msg['content']}]})

            # 2. Construct New Body
            # We clone the harvested body structure to keep all the magic context/metadata
            new_variables = original_body.get('variables', {}).copy()
            
            # Update contents (Chat History)
            new_variables['contents'] = chat_history
            
            # Update System Instruction
            if system_instruction:
                new_variables['systemInstruction'] = {"parts": [{"text": system_instruction.strip()}]}

            # Disable Safety Filters
            new_variables['safetySettings'] = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
            ]
                
            # Update Model
            # Load model mapping from models.json
            model_map = {}
            try:
                with open(MODELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    model_map = config.get('alias_map', {})
            except Exception as e:
                print(f"⚠️ Error loading models.json: {e}")

            target_model = model_map.get(model, model)
            
            # Handle suffixes for thinking and resolution
            thinking_mode = None
            resolution_mode = None
            
            if target_model.endswith("-low"):
                target_model = target_model[:-4]
                thinking_mode = "low"
            elif target_model.endswith("-high"):
                target_model = target_model[:-5]
                thinking_mode = "high"
                
            if target_model.endswith("-1k"):
                resolution_mode = "1k"
                target_model = target_model[:-3]
            elif target_model.endswith("-2k"):
                resolution_mode = "2k"
                target_model = target_model[:-3]
            elif target_model.endswith("-4k"):
                resolution_mode = "4k"
                target_model = target_model[:-3]

            print(f"🔄 Switching model to: {target_model} (requested: {model})")
            new_variables['model'] = target_model
            
            # Apply generation parameters from client
            if 'generationConfig' not in new_variables:
                new_variables['generationConfig'] = {}
            
            gen_config = new_variables['generationConfig']

            # Handle Thinking Config
            # Case 1: Explicit suffixes (-low, -high)
            if thinking_mode:
                gen_config['thinkingConfig'] = {"includeThoughts": True}
                if thinking_mode == 'low':
                     budget = 8192
                elif thinking_mode == 'high':
                     budget = 32768
                
                gen_config['thinkingConfig']['budget_token_count'] = budget
                gen_config['thinkingConfig']['thinkingBudget'] = budget
                print(f"ℹ️ Configured Thinking (Suffix): Mode={thinking_mode}, Budget={budget}")

            # Case 2: No suffix, but client provided max_tokens (treat as thinking budget for 3-pro)
            # Only applies if we haven't already set a thinking mode via suffix
            elif 'gemini-3-pro' in target_model and 'max_tokens' in kwargs and kwargs['max_tokens'] is not None:
                budget = int(kwargs['max_tokens'])
                # Only enable thinking if budget is reasonable for thinking (e.g. > 1024)
                # or if user explicitly wants it. Let's assume max_tokens on 3-pro implies thinking budget.
                gen_config['thinkingConfig'] = {
                    "includeThoughts": True,
                    "budget_token_count": budget,
                    "thinkingBudget": budget
                }
                print(f"ℹ️ Configured Thinking (Custom): Budget={budget}")
            
            # Handle Resolution (Image Generation)
            if resolution_mode:
                # Ensure responseModalities includes IMAGE
                if 'responseModalities' not in gen_config:
                    gen_config['responseModalities'] = ["TEXT", "IMAGE"]

                if 'imageConfig' not in gen_config:
                    gen_config['imageConfig'] = {}
                
                # Map resolution mode to Vertex AI imageSize strings
                # Based on logs: "imageSize": "4K"
                size_str_map = {
                    "1k": "1K", # Assumed based on 4K pattern
                    "2k": "2K", # Assumed based on 4K pattern
                    "4k": "4K"  # Confirmed from logs
                }
                
                if resolution_mode in size_str_map:
                    gen_config['imageConfig']['imageSize'] = size_str_map[resolution_mode]
                    
                    # Set other standard image generation parameters from logs
                    gen_config['imageConfig']['personGeneration'] = "ALLOW_ALL"
                    
                    if 'imageOutputOptions' not in gen_config['imageConfig']:
                        gen_config['imageConfig']['imageOutputOptions'] = {"mimeType": "image/png"}
                    
                    # Default to 1:1 if not specified, as resolution suffixes usually imply square
                    if 'aspectRatio' not in gen_config['imageConfig']:
                        gen_config['imageConfig']['aspectRatio'] = "1:1"
                    
                    print(f"ℹ️ Configured Image Generation: Size={gen_config['imageConfig'].get('imageSize')}, Ratio={gen_config['imageConfig'].get('aspectRatio')}")
            
            # CLEANUP: Remove model-specific configurations that might cause conflicts
            # If we switch models, old generation configs (like thinking) might be invalid.
            
            # Remove 'thinkingConfig' if present, unless the model is explicitly a thinking model
            if not thinking_mode:
                gen_config.pop('thinkingConfig', None)
                # Also check for snake_case just in case
                gen_config.pop('thinking_config', None)

            # Remove 'imageConfig' if NOT an image model (to be safe)
            if not resolution_mode:
                gen_config.pop('imageConfig', None)
                gen_config.pop('sampleImageSize', None)
                gen_config.pop('width', None)
                gen_config.pop('height', None)
            
            # Note: The exact field name might be 'thinkingConfig' or inside 'generationConfig'
            # Based on common Vertex AI payloads, let's check 'generationConfig'
            
            # Fix maxOutputTokens
            # Allow client to override max_tokens, otherwise default to harvested value or 65535
            # client_max_tokens = original_body.get('variables', {}).get('generationConfig', {}).get('maxOutputTokens')
            
            # Check if client provided max_tokens in the request body (OpenAI format)
            # Note: 'original_body' here is the harvested body. We need to check the incoming 'messages' or 'body' from the request.
            # But wait, 'stream_chat' doesn't receive the full request body, only 'messages' and 'model'.
            # Let's assume we want to restore the high limit.
            
            if isinstance(gen_config, dict):
                # Restore high limit or use a safe default
                # If the harvested token had a value, we keep it (unless we want to force it)
                # User requested to put it back to 65535
                if 'maxOutputTokens' in gen_config:
                    # Ensure it's at least 8192 if it was lowered, or just set to 65535 if missing/low
                    if gen_config['maxOutputTokens'] < 8192:
                            gen_config['maxOutputTokens'] = 65535
                else:
                    gen_config['maxOutputTokens'] = 65535
            
            if 'temperature' in kwargs and kwargs['temperature'] is not None:
                gen_config['temperature'] = float(kwargs['temperature'])
                print(f"ℹ️ Set temperature: {gen_config['temperature']}")
                
            if 'top_p' in kwargs and kwargs['top_p'] is not None:
                gen_config['topP'] = float(kwargs['top_p'])
                print(f"ℹ️ Set topP: {gen_config['topP']}")
                
            if 'top_k' in kwargs and kwargs['top_k'] is not None:
                gen_config['topK'] = int(kwargs['top_k'])
                print(f"ℹ️ Set topK: {gen_config['topK']}")
                
            if 'max_tokens' in kwargs and kwargs['max_tokens'] is not None:
                gen_config['maxOutputTokens'] = int(kwargs['max_tokens'])
                print(f"ℹ️ Set maxOutputTokens: {gen_config['maxOutputTokens']}")
                
            if 'stop' in kwargs and kwargs['stop'] is not None:
                gen_config['stopSequences'] = kwargs['stop'] if isinstance(kwargs['stop'], list) else [kwargs['stop']]
                print(f"ℹ️ Set stopSequences: {gen_config['stopSequences']}")

            # DEBUG: Print all generation config parameters for inspection
            if resolution_mode or thinking_mode:
                print("\n🔍 --- DEBUG: Generation Config Parameters ---")
                print(json.dumps(gen_config, indent=2))
                print("---------------------------------------------\n")

            # Reassemble body
            new_body = {
                "querySignature": original_body.get('querySignature'), # Might need this?
                "operationName": original_body.get('operationName'),
                "variables": new_variables
            }
            
            # 3. Prepare Headers
            headers = creds['headers'].copy() # Copy to avoid mutating the cached credentials
            
            # Ensure critical headers are present and correct
            # Note: 'Cookie', 'User-Agent', 'Origin', 'Referer' should now be in creds['headers'] from the harvester
            
            headers['content-type'] = 'application/json'
            
            # Remove headers that httpx/network layer should handle or that might cause conflicts
            headers.pop('content-length', None)
            headers.pop('Content-Length', None)
            headers.pop('host', None)
            headers.pop('Host', None)
            headers.pop('connection', None)
            headers.pop('Connection', None)
            headers.pop('accept-encoding', None) # Let httpx handle decompression

            url = creds['url']
            
            print(f"🚀 Sending request to Google Vertex AI (Attempt {attempt+1})...")
            try:
                # Use a try-finally block to ensure we handle cancellation if needed,
                # though async with handles cleanup automatically.
                async with self.client.stream('POST', url, headers=headers, json=new_body) as response:
                    print(f"📡 Response Status: {response.status_code}")
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        print(f"❌ Google API Error: {response.status_code} - {error_text}")
                        
                        # Check for potential token expiration
                        if response.status_code in [400, 401, 403] and attempt < max_retries:
                            print(f"⚠️ Auth Error ({response.status_code}). Triggering refresh and waiting...")
                            
                            # 根据模式选择刷新策略
                            if BROWSER_MODE == "headful":
                                await headful_browser_refresh()
                            else:
                                await request_token_refresh()
                            
                            # Wait for new credentials
                            refreshed = await cred_manager.wait_for_refresh(timeout=45)
                            if refreshed:
                                print("✅ Credentials refreshed! Waiting 1s before retrying request...")
                                await asyncio.sleep(1) # Add 1 second delay
                                # Update headers/url with new credentials
                                new_creds = cred_manager.get_credentials()
                                headers = new_creds['headers'].copy()
                                headers['content-type'] = 'application/json'
                                headers.pop('content-length', None)
                                headers.pop('host', None)
                                url = new_creds['url']
                                continue # Retry loop
                            else:
                                print("❌ Refresh timed out.")
                        
                        # If we get here, it's a fatal error or retry failed
                        error_payload = {"error": {"message": f"Upstream Error: {response.status_code} - {error_text.decode()}", "type": "upstream_error"}}
                        yield f"data: {json.dumps(error_payload)}\n\n"
                        return

                    buffer = ""
                    chunk_count = 0
                    
                    # ... (Stream processing logic) ...
                    # We need to handle the stream inside the loop, but if it fails mid-stream due to auth (rare for 200 OK), we can't easily retry.
                    # However, we handled the "200 OK but error inside JSON" case before. We need to adapt that too.
                    
                    async for chunk in response.aiter_text():
                        chunk_count += 1
                        buffer += chunk
                        
                        while buffer:
                            # Skip whitespace
                            buffer = buffer.lstrip()
                            if not buffer:
                                break
                                
                            # Handle Google's JSON array format [obj, obj, ...]
                            if buffer.startswith('['):
                                buffer = buffer[1:]
                                continue
                            if buffer.startswith(','):
                                buffer = buffer[1:]
                                continue
                            if buffer.startswith(']'):
                                buffer = buffer[1:]
                                continue

                            try:
                                decoder = json.JSONDecoder()
                                obj, idx = decoder.raw_decode(buffer)
                                
                                for chunk_data in self.process_google_response(obj):
                                    yield chunk_data
                                    content_yielded = True # Mark that content was successfully yielded
                                
                                buffer = buffer[idx:]
                            except json.JSONDecodeError:
                                # Incomplete JSON, wait for more data
                                break
                            except AuthError as e:
                                raise e # Re-raise to be caught by the outer try-except
                            except Exception as e:
                                print(f"Error parsing stream chunk: {e}")
                                # Log the start of the buffer to debug unexpected characters
                                print(f"🐛 Debug Buffer (Start): {buffer[:100].strip()}")
                                
                                # Aggressive skip: Find the next JSON start character
                                next_json_start = -1
                                for char in ['[', '{']:
                                    try:
                                        idx = buffer.index(char)
                                        if next_json_start == -1 or idx < next_json_start:
                                            next_json_start = idx
                                    except ValueError:
                                        pass
                                
                                if next_json_start != -1:
                                    print(f"⚠️ Skipping {next_json_start} non-JSON characters.")
                                    buffer = buffer[next_json_start:]
                                else:
                                    # If no JSON start found, skip one char to avoid infinite loop
                                    buffer = buffer[1:]
                    
                    # If we successfully processed the stream, break the retry loop
                    break

            except AuthError as e:
                print(f"⚠️ Auth Error caught in stream: {e}")
                if attempt < max_retries:
                    print("🔄 Triggering refresh and retrying...")
                    if BROWSER_MODE == "headful":
                        await headful_browser_refresh()
                    else:
                        await request_token_refresh()
                    # Step 1: Wait for the new credentials to be harvested
                    refreshed = await cred_manager.wait_for_refresh(timeout=60)
                    if refreshed:
                        # Step 2: Wait for the frontend to confirm the UI is stable
                        ui_ready = await cred_manager.wait_for_refresh_complete(timeout=60)
                        if ui_ready:
                            print("✅ Credentials and UI ready! Waiting 1s before retrying request...")
                            await asyncio.sleep(1) # Add 1 second delay
                            # Update headers/url with new credentials
                            new_creds = cred_manager.get_credentials()
                            headers = new_creds['headers'].copy()
                            headers['content-type'] = 'application/json'
                            headers.pop('content-length', None)
                            headers.pop('host', None)
                            url = new_creds['url']
                            continue # Retry the request
                        else:
                            print("❌ Frontend UI did not become ready in time.")
                    else:
                        print("❌ Credential refresh timed out.")

                error_payload = {"error": {"message": str(e), "type": "authentication_error"}}
                yield f"data: {json.dumps(error_payload)}\n\n"
                return

            except Exception as e:
                print(f"❌ Request failed: {e}")
                if attempt < max_retries:
                    continue
                error_payload = {"error": {"message": str(e), "type": "request_error"}}
                yield f"data: {json.dumps(error_payload)}\n\n"
                return # Stop generator on fatal error
        
        # If we exit the loop without returning, it means we successfully processed the stream.
        
        if not content_yielded:
            # If the stream finished but yielded no content, log a warning.
            # We rely on the client to handle the empty stream gracefully after receiving [DONE].
            print("⚠️ Proxy Warning: Google API returned an empty stream (200 OK but no content).")
            
        # Ensure the stream is properly terminated with [DONE]
        yield "data: [DONE]\n\n"

    def process_google_response(self, data: Dict[str, Any]) -> Generator[str, None, None]:
            """Converts Google's response format to OpenAI's SSE format, handling text and images."""
            try:
                if not data:
                    return
                
                # Debug: Log the raw data received from Google
                print(f"🔍 Google Raw Chunk: {json.dumps(data, indent=2)[:500]}...")
    
                if 'error' in data:
                    print(f"⚠️ Google Stream Error: {data['error']}")
                    # This error is usually not fatal, just a part of the stream.
                    return
    
                if 'results' in data and data['results']:
                    for result in data['results']:
                        if not result: continue
    
                        if 'errors' in result:
                            for err in result['errors']:
                                msg = err.get('message', 'Unknown Error')
                                print(f"⚠️ Google API Error: {msg}")
                                if "Recaptcha" in msg or "token" in msg.lower() or "Authentication" in msg:
                                    raise AuthError(f"Authentication failed: {msg}")
                            continue
    
                        result_data = result.get('data')
                        if not result_data: continue
    
                        candidates = result_data.get('candidates')
                        if not candidates: continue
    
                        for candidate in candidates:
                            content = candidate.get('content') or {}
                            parts = content.get('parts') or []
    
                            for part in parts:
                                delta = {}
                                # --- Text Part ---
                                text = part.get('text', '')
                                if text:
                                    if part.get('thought', False):
                                        delta['reasoning_content'] = text
                                    else:
                                        delta['content'] = text
    
                                # --- Image Part (inline data) ---
                                inline_data = part.get('inlineData')
                                uri = part.get('uri') # Check for external URI
                                
                                if inline_data:
                                    mime_type = inline_data.get('mimeType')
                                    b64_data = inline_data.get('data')
                                    if mime_type and b64_data:
                                        # Format as a markdown image data URI
                                        image_md = f"![Generated Image](data:{mime_type};base64,{b64_data})"
                                        delta['content'] = image_md
                                elif uri:
                                    # Format as a markdown image URL
                                    image_md = f"![Generated Image]({uri})"
                                    delta['content'] = image_md
    
                                # --- Yield Chunk if we have content ---
                                if delta:
                                    chunk = {
                                        "id": f"chatcmpl-proxy-{uuid.uuid4()}",
                                        "object": "chat.completion.chunk",
                                        "created": int(time.time()),
                                        "model": "vertex-ai-proxy",
                                        "choices": [{"index": 0, "delta": delta, "finish_reason": None}]
                                    }
                                    yield f"data: {json.dumps(chunk)}\n\n"
    
                            # Check finish reason for the candidate
                            finish_reason = candidate.get('finishReason')
                            
                            # Only send finish chunk if it's a final stop reason AND not part of a thought process
                            # Note: We assume if 'thought' is present in any part, the finish reason might be premature.
                            is_thought_part = any(p.get('thought', False) for p in parts)
                            
                            if finish_reason in ['STOP', 'MAX_TOKENS'] and not is_thought_part:
                                finish_chunk = {
                                    "id": f"chatcmpl-proxy-finish-{uuid.uuid4()}",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": "vertex-ai-proxy",
                                    "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason.lower()}]
                                }
                                yield f"data: {json.dumps(finish_chunk)}\n\n"
                            elif finish_reason in ['STOP', 'MAX_TOKENS'] and is_thought_part:
                                print("⚠️ Suppressing premature finishReason due to active thinking mode.")
            except AuthError:
                raise # Re-raise to be caught by the retry logic
            except Exception as e:
                print(f"Error processing response object: {e}")
                print(f"🐛 Debug Data causing error: {json.dumps(data, indent=2)}")

vertex_client = VertexAIClient()

# --- FastAPI App ---
app = FastAPI()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """重定向到仪表盘"""
    return FileResponse("static/dashboard.html")

@app.get("/dashboard")
async def dashboard():
    """仪表盘页面"""
    return FileResponse("static/dashboard.html")

@app.post("/dashboard/verify")
async def verify_dashboard_access(bearer: HTTPAuthorizationCredentials = Depends(security_bearer)):
    """验证仪表盘访问权限 - 使用 Authorization: Bearer <token>"""
    if not bearer or not bearer.credentials:
        print("❌ Dashboard验证失败: 未提供 Bearer token")
        raise HTTPException(
            status_code=401,
            detail="API Key is required. Please provide Authorization: Bearer <token> header."
        )
    
    token = bearer.credentials.strip()
    
    if token != API_KEY:
        print(f"⚠️ Dashboard验证失败 (长度不匹配: 期望 {len(API_KEY)}, 收到 {len(token)})")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    print("✅ Dashboard验证成功")
    return {"status": "ok"}

@app.get("/dashboard/stats")
async def get_dashboard_stats(api_key: str = Depends(verify_api_key)):
    """获取仪表盘统计数据"""
    today_stats = daily_stats_manager.get_today_stats()
    return {
        "today": today_stats,
        "date": daily_stats_manager.get_beijing_date()
    }

@app.get("/v1/models")
async def list_models(api_key: str = Depends(verify_api_key)):
    # Return a list of common Vertex AI models
    # This helps clients know what's available
    current_time = int(time.time())
    models = []
    try:
        with open(MODELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            models = config.get('models', [])
    except Exception as e:
        print(f"⚠️ Error loading models.json: {e}")
        # Fallback
        models = ["gemini-1.5-pro", "gemini-1.5-flash"]

    data = {
        "object": "list",
        "data": [
            {"id": m, "object": "model", "created": current_time, "owned_by": "google"}
            for m in models
        ]
    }
    return data

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, api_key: str = Depends(verify_api_key)):
    try:
        body = await request.json()
        messages = body.get('messages', [])
        model = body.get('model', 'gemini-1.5-pro')
        stream = body.get('stream', False) # Extract stream flag
        
        # Extract generation parameters
        temperature = body.get('temperature')
        top_p = body.get('top_p')
        top_k = body.get('top_k')
        max_tokens = body.get('max_tokens')
        stop = body.get('stop')
        
        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        # 记录请求到每日统计
        await daily_stats_manager.record_request(model)

        if stream:
            return StreamingResponse(
                vertex_client.stream_chat(
                    messages,
                    model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    max_tokens=max_tokens,
                    stop=stop
                ),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming request
            response_data = await vertex_client.complete_chat(
                messages,
                model,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                stop=stop
            )
            return response_data

    except Exception as e:
        print(f"Error in endpoint: {e}")
        # FastAPI handles exceptions better, but for compatibility:
        raise HTTPException(status_code=500, detail={"error": str(e)})

# --- WebSocket Server (For Harvester) ---
import websockets

# Store connected harvester clients
harvester_clients = set()

async def websocket_handler(websocket):
    print("🔌 WebSocket client connected")
    harvester_clients.add(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                if msg_type == "credentials_harvested":
                    cred_manager.update(data.get("data"))
                elif msg_type == "token_refreshed":
                    cred_manager.update_token(data.get("token"))
                elif msg_type == "refresh_complete":
                    print("✅ Frontend confirms refresh is complete.")
                    cred_manager.refresh_complete_event.set()
                elif msg_type == "identify":
                    print(f"👋 Client identified: {data.get('client')}")
            except Exception as e:
                print(f"WS Error: {e}")
    except websockets.ConnectionClosed:
        print("🔌 WebSocket client disconnected")
        harvester_clients.remove(websocket)
    except Exception as e:
        print(f"WS Handler Error: {e}")
        if websocket in harvester_clients:
            harvester_clients.remove(websocket)

async def request_token_refresh():
    print("🔄 Requesting token refresh from frontend...")
    if not harvester_clients:
        print("⚠️ No harvester clients connected!")
        return
    
    message = json.dumps({"type": "refresh_token"})
    # Broadcast to all connected harvesters
    for ws in list(harvester_clients):
        try:
            await ws.send(message)
        except Exception as e:
            print(f"Failed to send refresh request: {e}")
            harvester_clients.remove(ws)

async def headful_browser_refresh() -> None:
    """有头浏览器模式凭证刷新"""
    global _headful_browser, _refresh_fail_count, _refresh_lock
    
    # 延迟初始化锁（在异步上下文中）
    if _refresh_lock is None:
        _refresh_lock = asyncio.Lock()
    
    # 获取刷新锁，防止并发刷新
    if _refresh_lock.locked():
        print("⏳ 检测到正在进行的凭证刷新，等待完成...")
        async with _refresh_lock:
            print("✅ 凭证刷新已由其他请求完成")
            return
    
    async with _refresh_lock:
        if _headful_browser and _headful_browser.is_running:
            print("🔄 有头浏览器模式: 按需刷新凭证...")
        
            try:
                # 记录刷新前的凭证时间戳
                old_timestamp = cred_manager.last_updated
                print(f"   🔍 刷新前凭证时间戳: {old_timestamp}")
                
                # 先尝试关闭任何可能的 overlay
                await _headful_browser._dismiss_overlays()
                
                success = await _headful_browser.send_test_message()
                if success:
                    # 等待凭证实际更新（最多等待 5 秒）
                    for i in range(10):
                        await asyncio.sleep(0.5)
                        if cred_manager.last_updated > old_timestamp:
                            new_timestamp = cred_manager.last_updated
                            print(f"✅ 有头浏览器模式: 凭证已更新")
                            print(f"   新凭证时间戳: {new_timestamp} (延迟 {new_timestamp - old_timestamp:.1f}秒)")
                            _refresh_fail_count = 0
                            
                            # 立即设置事件
                            cred_manager.refresh_event.set()
                            cred_manager.refresh_complete_event.set()
                            return  # 成功，直接返回
                    
                    print("⚠️ 有头浏览器模式: 消息已发送但凭证未更新 (可能被 recaptcha 拦截)")
                
                # 失败处理
                _refresh_fail_count += 1
                print(f"❌ 有头浏览器模式: 凭证刷新失败 (连续失败 {_refresh_fail_count}/{_REDIRECT_THRESHOLD})")
                
                # 连续失败达到阈值，尝试恢复
                if _refresh_fail_count >= _REDIRECT_THRESHOLD:
                    print("🔄 有头浏览器模式: 重复失败，尝试恢复...")
                    _refresh_fail_count = 0
                    
                    recovered = False
                    
                    # 策略1: 刷新当前页面
                    try:
                        print("   📍 策略1: 刷新当前页面...")
                        if _headful_browser.page:
                            await _headful_browser._dismiss_overlays()
                            await _headful_browser.page.reload(wait_until="domcontentloaded", timeout=15000)
                            await asyncio.sleep(2)
                            await _headful_browser._dismiss_overlays()
                            
                            retry_success = await _headful_browser.send_test_message()
                            if retry_success:
                                print("   ✅ 页面刷新后恢复成功")
                                recovered = True
                    except Exception as e:
                        print(f"   ⚠️ 页面刷新失败: {str(e)[:50]}")
                    
                    # 策略2: 重定向到 Vertex AI Studio
                    if not recovered:
                        try:
                            print("   📍 策略2: 重定向到 Vertex AI Studio...")
                            if _headful_browser.page:
                                await _headful_browser.page.goto(
                                    _headful_browser.VERTEX_AI_URL,
                                    wait_until="domcontentloaded",
                                    timeout=30000
                                )
                                print("   ✅ 已重定向，等待页面加载...")
                                await asyncio.sleep(3)
                                
                                await _headful_browser._dismiss_overlays()
                                
                                retry_success = await _headful_browser.send_test_message()
                                if retry_success:
                                    print("   ✅ 重定向后恢复成功")
                                    recovered = True
                                else:
                                    print("   ⚠️ 重定向后仍然失败")
                        except Exception as e:
                            print(f"   ⚠️ 重定向失败: {str(e)[:50]}")
                    
                    if not recovered:
                        print("⚠️ 有头浏览器模式: 所有恢复策略失败")
                        
            except Exception as e:
                print(f"❌ 有头浏览器模式: 凭证刷新异常: {e}")
                _refresh_fail_count += 1
        else:
            print("⚠️ 有头浏览器模式: 浏览器未运行，无法刷新凭证")


async def start_headful_browser_mode() -> None:
    """启动有头浏览器模式"""
    global _headful_browser
    
    try:
        from src.browser import HeadfulBrowser
        from src.harvester import CredentialHarvester
    except ImportError as e:
        print(f"❌ 无法导入浏览器模块: {e}")
        print("   请确保已安装 playwright: pip install playwright && playwright install chromium")
        return
    
    print("🌐 有头浏览器模式启动中...")
    
    # 创建浏览器实例
    browser = HeadfulBrowser()
    _headful_browser = browser
    
    def on_credentials(data):
        cred_manager.update(data)
        cred_manager.refresh_complete_event.set()
    
    harvester = CredentialHarvester(on_credentials=on_credentials)
    
    # 启动浏览器（有头模式）
    if not await browser.start(headless=False):
        print("❌ 有头浏览器启动失败")
        _headful_browser = None
        return
    
    # 设置请求拦截
    await browser.setup_request_interception(harvester.handle_request)
    
    # 导航到 Vertex AI
    if not await browser.navigate_to_vertex():
        print("❌ 无法访问 Vertex AI Studio")
        await browser.close()
        _headful_browser = None
        return
    
    print("🔄 有头浏览器模式: 获取初始凭证...")
    await browser.send_test_message()
    
    print("✅ 有头浏览器模式已就绪 (按需刷新)")
    print("   👁️ 浏览器窗口已打开，您可以看到浏览器操作")
    
    # 保持浏览器运行
    try:
        while browser.is_running:
            await asyncio.sleep(1)
    finally:
        await browser.close()
        _headful_browser = None


async def main():
    """启动服务器"""
    print(f"\n📋 浏览器模式: {BROWSER_MODE}")
    
    tasks = []
    
    # 根据模式启动相应的服务
    if BROWSER_MODE == "websocket":
        # WebSocket 模式（原有模式）
        print("🌐 WebSocket 模式: 等待浏览器脚本连接...")
        ws_server = websockets.serve(websocket_handler, "0.0.0.0", PORT_WS)
        tasks.append(ws_server)
        
    elif BROWSER_MODE == "headful":
        # 有头浏览器模式
        print("🌐 有头浏览器模式: 自动获取凭证...")
        tasks.append(asyncio.create_task(start_headful_browser_mode()))
        
    elif BROWSER_MODE == "manual":
        # 手动模式（使用已保存的凭证）
        print("📄 手动模式: 使用已保存的凭证")
        if not cred_manager.get_credentials():
            print("⚠️ 未找到凭证文件，请先运行其他模式获取凭证")
    
    # 启动 API 服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT_API, log_level="info")
    server = uvicorn.Server(config)

    print(f"\n🚀 Proxy 服务已启动")
    print(f"   - API: http://0.0.0.0:{PORT_API}")
    if BROWSER_MODE == "websocket":
        print(f"   - WS:  ws://0.0.0.0:{PORT_WS}")
        print("   👉 请确保浏览器中的 Harvester 脚本正在运行")
    elif BROWSER_MODE == "headful":
        print("   👁️ 浏览器窗口将自动打开")

    tasks.append(server.serve())
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    import os
    
    # 检查是否启用无 GUI 模式（用于 Docker）
    if os.environ.get('NOGUI', '').lower() in ('1', 'true', 'yes'):
        print("🐳 Running in headless mode (no GUI)")
        asyncio.run(main())
    else:
        # 使用 GUI 模式
        try:
            import gui
            
            def server_runner():
                asyncio.run(main())
                
            gui.run(server_runner, stats_manager)
        except ImportError:
            print("⚠️ GUI module not available, running in headless mode")
            asyncio.run(main())