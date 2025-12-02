#!/bin/bash
set -e

echo "🚀 Vertex AI Proxy v2 - Docker 启动脚本"

# 检查浏览器模式
if [ "$BROWSER_MODE" = "headful" ]; then
    echo "🌐 检测到有头浏览器模式，启动 Xvfb..."
    
    # 启动 Xvfb（虚拟显示服务器）
    Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
    XVFB_PID=$!
    
    # 设置 DISPLAY 环境变量
    export DISPLAY=:99
    
    # 等待 Xvfb 启动
    sleep 2
    
    echo "✅ Xvfb 已启动 (PID: $XVFB_PID, DISPLAY: $DISPLAY)"
    
    # 设置清理函数
    cleanup() {
        echo "🛑 正在停止 Xvfb..."
        kill $XVFB_PID 2>/dev/null || true
    }
    trap cleanup EXIT
fi

# 启动应用
echo "🚀 启动应用..."
exec python main.py