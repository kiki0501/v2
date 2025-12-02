# Vertex AI Proxy - Docker 部署指南

本文档说明如何使用 Docker 部署 Vertex AI Proxy v2 版本。

## 📋 前置要求

- Docker 20.10 或更高版本
- Docker Compose 1.29 或更高版本（可选）

## 🚀 快速开始

### 方法 1: 使用 Docker Compose（推荐）

1. **构建并启动容器**
   ```bash
   cd v2
   docker-compose up -d
   ```

2. **查看日志**
   ```bash
   docker-compose logs -f
   ```

3. **停止服务**
   ```bash
   docker-compose down
   ```

### 方法 2: 使用 Docker 命令

1. **构建镜像**
   ```bash
   cd v2
   docker build -t vertex-ai-proxy-v2 .
   ```

2. **运行容器**
   ```bash
   docker run -d \
     --name vertex-ai-proxy-v2 \
     -p 7860:7860 \
     -p 28881:28881 \
     -v $(pwd)/credentials.json:/app/credentials.json \
     -v $(pwd)/stats.json:/app/stats.json \
     -v $(pwd)/auth_bundle.json:/app/auth_bundle.json \
     -e NOGUI=1 \
     vertex-ai-proxy-v2
   ```

3. **查看日志**
   ```bash
   docker logs -f vertex-ai-proxy-v2
   ```

4. **停止并删除容器**
   ```bash
   docker stop vertex-ai-proxy-v2
   docker rm vertex-ai-proxy-v2
   ```

## 🔧 配置说明

### 端口映射

- `7860`: API 服务端口（用于接收 OpenAI 格式的请求）
- `28881`: WebSocket 端口（用于接收浏览器脚本发送的凭证）

### 环境变量

- `NOGUI=1`: 禁用 GUI 界面，在无头模式下运行
- `PYTHONUNBUFFERED=1`: 禁用 Python 输出缓冲，实时显示日志

### 数据持久化

以下文件通过 Docker 卷挂载以保持数据持久化：

- `credentials.json`: 存储从浏览器获取的认证凭证
- `stats.json`: 存储 API 调用统计信息
- `auth_bundle.json`: 存储认证包数据

## 📝 使用说明

1. **启动 Docker 容器后，容器会在后台运行并监听端口**

2. **在浏览器中安装并运行 Harvester 用户脚本**
   - 用户脚本需要连接到 `ws://YOUR_SERVER_IP:28881`
   - 脚本会自动从 Google Vertex AI Studio 获取凭证并发送到服务器

3. **配置客户端使用代理 API**
   ```
   API Base URL: http://YOUR_SERVER_IP:7860/v1
   API Key: 任意值（不验证）
   ```

## 🔍 故障排除

### 查看容器状态
```bash
docker ps -a | grep vertex-ai-proxy-v2
```

### 查看实时日志
```bash
docker logs -f vertex-ai-proxy-v2
```

### 重启容器
```bash
docker restart vertex-ai-proxy-v2
```

### 进入容器调试
```bash
docker exec -it vertex-ai-proxy-v2 /bin/bash
```

### 检查网络连接
```bash
# 测试 API 端口
curl http://localhost:7860/v1/models

# 测试 WebSocket 端口
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     http://localhost:28881/
```

## 🔄 更新容器

当代码更新后：

```bash
# 停止并删除旧容器
docker-compose down

# 重新构建镜像
docker-compose build

# 启动新容器
docker-compose up -d
```

## 📊 监控

### 查看统计信息
```bash
# 查看 stats.json 文件
cat stats.json

# 或通过 API 查询
curl http://localhost:7860/v1/models
```

## 🌐 网络访问

如果需要从其他机器访问：

1. 确保防火墙允许 7860 和 28881 端口
2. 使用服务器的 LAN IP 或公网 IP 替换 `localhost`

## ⚠️ 注意事项

1. **凭证文件**：首次运行时，如果 `credentials.json` 不存在，服务会等待浏览器脚本发送凭证

2. **GUI 模式**：Docker 容器中默认禁用 GUI，如需本地运行 GUI 版本，请直接运行 `python main.py`

3. **端口冲突**：如果端口已被占用，请修改 `docker-compose.yml` 中的端口映射

4. **数据备份**：定期备份 `credentials.json` 和 `stats.json` 文件

## 📚 更多信息

参考主 README.md 文件了解更多关于项目的信息。