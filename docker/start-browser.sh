#!/bin/bash
set -e

echo "🌐 等待 X 服务器启动..."
sleep 5

echo "🔧 配置 Chrome 浏览器..."

# 创建 Chrome 配置目录
CHROME_USER_DATA="/root/.config/google-chrome"
mkdir -p "$CHROME_USER_DATA/Default"

# 创建 Chrome 首选项文件，禁用一些提示
cat > "$CHROME_USER_DATA/Default/Preferences" <<EOF
{
  "browser": {
    "check_default_browser": false,
    "show_home_button": true
  },
  "profile": {
    "default_content_setting_values": {
      "notifications": 2
    },
    "password_manager_enabled": false
  },
  "credentials_enable_service": false,
  "download": {
    "prompt_for_download": false,
    "directory_upgrade": true,
    "extensions_to_open": ""
  },
  "safebrowsing": {
    "enabled": false
  }
}
EOF

echo "📦 准备安装用户脚本..."

# 等待代理服务器启动
echo "⏳ 等待代理服务器启动..."
for i in {1..30}; do
    if curl -s http://localhost:7860/v1/models > /dev/null 2>&1; then
        echo "✅ 代理服务器已就绪"
        break
    fi
    echo "   等待中... ($i/30)"
    sleep 2
done

echo "🚀 启动 Chrome 浏览器..."

# 启动 Chrome 并打开 Vertex AI Studio
google-chrome \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --disable-software-rasterizer \
    --disable-setuid-sandbox \
    --disable-infobars \
    --disable-notifications \
    --disable-popup-blocking \
    --disable-translate \
    --disable-features=TranslateUI \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding \
    --disable-background-networking \
    --no-first-run \
    --no-default-browser-check \
    --user-data-dir="$CHROME_USER_DATA" \
    --window-size=1920,1080 \
    --start-maximized \
    "https://console.cloud.google.com/vertex-ai/studio/multimodal?mode=prompt&model=gemini-2.5-flash-lite-preview-09-2025" \
    > /var/log/chrome.log 2>&1

echo "❌ Chrome 浏览器已退出"