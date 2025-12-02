#!/bin/bash
# 启动有头浏览器模式的快速脚本

set -e

echo "🚀 Vertex AI Proxy v2 - 有头浏览器模式启动脚本"
echo ""

# 检查是否在 Docker 环境中
if [ -f /.dockerenv ]; then
    echo "📦 检测到 Docker 环境"
    IS_DOCKER=true
else
    echo "💻 检测到本地环境"
    IS_DOCKER=false
fi

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python"
    exit 1
fi

# 如果是本地环境，检查依赖
if [ "$IS_DOCKER" = false ]; then
    echo ""
    echo "📋 检查依赖..."
    
    # 检查 pip 包
    if ! python3 -c "import playwright" &> /dev/null; then
        echo "⚠️  未找到 Playwright，正在安装..."
        pip install -r requirements.txt
        echo "📥 安装 Playwright 浏览器..."
        playwright install chromium
        playwright install-deps chromium || echo "⚠️  某些系统依赖可能需要手动安装"
    else
        echo "✅ Playwright 已安装"
    fi
fi

# 设置环境变量
export BROWSER_MODE=headful
export NOGUI=1
export PYTHONUNBUFFERED=1

# 如果未设置 API_KEY，使用默认值
if [ -z "$API_KEY" ]; then
    export API_KEY="your-secret-api-key-here"
    echo "⚠️  使用默认 API_KEY，建议设置环境变量 API_KEY"
fi

# Linux 环境下配置 X11
if [ "$(uname)" = "Linux" ] && [ "$IS_DOCKER" = false ]; then
    if [ -z "$DISPLAY" ]; then
        export DISPLAY=:0
    fi
    echo "🖥️  DISPLAY=$DISPLAY"
fi

echo ""
echo "🎯 启动配置:"
echo "   - 模式: 有头浏览器 (Headful)"
echo "   - API 端口: 7860"
echo "   - API Key: ${API_KEY:0:10}..."
echo ""

# 启动应用
echo "🚀 启动服务..."
python3 main.py