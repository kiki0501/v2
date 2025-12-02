@echo off
REM 启动有头浏览器模式的快速脚本 (Windows)

echo 🚀 Vertex AI Proxy v2 - 有头浏览器模式启动脚本
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

echo 📋 检查依赖...

REM 检查 Playwright 是否安装
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  未找到 Playwright，正在安装...
    pip install -r requirements.txt
    echo 📥 安装 Playwright 浏览器...
    playwright install chromium
) else (
    echo ✅ Playwright 已安装
)

REM 设置环境变量
set BROWSER_MODE=headful
set NOGUI=1
set PYTHONUNBUFFERED=1

REM 如果未设置 API_KEY，使用默认值
if not defined API_KEY (
    set API_KEY=your-secret-api-key-here
    echo ⚠️  使用默认 API_KEY，建议设置环境变量 API_KEY
)

echo.
echo 🎯 启动配置:
echo    - 模式: 有头浏览器 (Headful)
echo    - API 端口: 7860
echo    - API Key: %API_KEY:~0,10%...
echo.

REM 启动应用
echo 🚀 启动服务...
python main.py

pause