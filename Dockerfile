# Dockerfile for Vertex AI Proxy (v2)
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（包括 Playwright 所需的浏览器依赖）
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器（Chromium）
RUN playwright install chromium
RUN playwright install-deps chromium

# 复制应用文件
COPY main.py gui.py models.json stats_manager.py ./
COPY static/ ./static/
COPY src/ ./src/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 7860
EXPOSE 28881

# 设置环境变量
ENV NOGUI=1
ENV PYTHONUNBUFFERED=1
ENV BROWSER_MODE=manual
# Playwright 环境变量
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 启动命令
CMD ["python", "main.py"]