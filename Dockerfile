# Dockerfile for Vertex AI Proxy (v2)
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY main.py gui.py models.json ./

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 28880
EXPOSE 28881

# 设置环境变量（禁用 GUI）
ENV NOGUI=1
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["python", "main.py"]