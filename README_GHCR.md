# GitHub Container Registry (GHCR) 使用指南

本文档说明如何使用 GitHub Container Registry 部署和使用 Vertex AI Proxy v2。

## 📦 关于 GHCR

GitHub Container Registry (GHCR) 是 GitHub 提供的容器镜像托管服务，可以自动构建和发布 Docker 镜像。

## 🚀 快速使用预构建镜像

### 方法 1: 使用 Docker Run

```bash
docker run -d \
  --name vertex-ai-proxy-v2 \
  -p 7860:7860 \
  -p 28881:28881 \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/stats.json:/app/stats.json \
  -v $(pwd)/auth_bundle.json:/app/auth_bundle.json \
  -e NOGUI=1 \
  ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest
```

### 方法 2: 使用 Docker Compose

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  vertex-ai-proxy:
    image: ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest
    container_name: vertex-ai-proxy-v2
    ports:
      - "7860:7860"
      - "28881:28881"
    volumes:
      - ./credentials.json:/app/credentials.json
      - ./stats.json:/app/stats.json
      - ./auth_bundle.json:/app/auth_bundle.json
    environment:
      - NOGUI=1
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

然后运行：

```bash
docker-compose up -d
```

## 🔧 设置自动构建（仓库所有者）

### 1. 启用 GitHub Actions

确保你的仓库已启用 GitHub Actions：
- 进入仓库设置 → Actions → General
- 允许所有 actions 运行

### 2. 配置 Packages 权限

1. 进入仓库设置 → Actions → General
2. 在 "Workflow permissions" 中选择：
   - ✅ Read and write permissions
   - ✅ Allow GitHub Actions to create and approve pull requests

### 3. 触发构建

工作流会在以下情况下自动触发：

- **推送到 main/master 分支**：构建并推送 `latest` 标签
- **创建版本标签**：例如 `v1.0.0`，会创建对应版本的镜像
- **Pull Request**：仅构建不推送
- **手动触发**：在 Actions 页面手动运行

### 4. 创建版本发布

```bash
# 创建并推送标签
git tag v1.0.0
git push origin v1.0.0
```

这将自动构建并推送以下标签的镜像：
- `ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:v1.0.0`
- `ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:1.0`
- `ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:1`
- `ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest`

## 📥 拉取镜像

### 公开镜像

如果镜像设置为公开，可以直接拉取：

```bash
docker pull ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest
```

### 私有镜像

如果镜像是私有的，需要先登录：

```bash
# 创建 GitHub Personal Access Token (PAT)
# 权限：read:packages

# 使用 PAT 登录
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# 拉取镜像
docker pull ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest
```

## 🔐 设置镜像为公开

1. 进入 GitHub 个人主页
2. 点击 "Packages" 标签
3. 找到 `vertex-ai-proxy-v2` 镜像
4. 点击 "Package settings"
5. 在 "Danger Zone" 中选择 "Change visibility" → "Public"

## 📋 可用的镜像标签

- `latest` - 最新的 main/master 分支构建
- `main` 或 `master` - 对应分支的最新构建
- `v1.0.0` - 特定版本（语义化版本）
- `1.0` - 主要和次要版本
- `1` - 主要版本

## 🏗️ 本地构建和推送（高级）

### 1. 构建镜像

```bash
cd v2
docker build -t ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest .
```

### 2. 登录 GHCR

```bash
# 使用 Personal Access Token
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### 3. 推送镜像

```bash
docker push ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest
```

## 🔄 更新镜像

### 拉取最新版本

```bash
docker pull ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest
docker-compose down
docker-compose up -d
```

### 使用特定版本

```bash
# 在 docker-compose.yml 中指定版本
image: ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:v1.0.0
```

## 🌍 多架构支持

GitHub Actions 工作流配置了多架构构建：
- `linux/amd64` - x86_64 架构（常规服务器）
- `linux/arm64` - ARM64 架构（Apple Silicon、ARM 服务器）

Docker 会自动拉取适合你系统架构的镜像。

## 📊 查看构建状态

1. 进入 GitHub 仓库
2. 点击 "Actions" 标签
3. 查看 "Docker Image CI/CD" 工作流的运行状态

## 🐛 故障排除

### 构建失败

检查 Actions 日志：
1. 进入 Actions 页面
2. 点击失败的工作流运行
3. 查看详细日志

常见问题：
- **权限不足**：检查 Workflow permissions 设置
- **Dockerfile 错误**：检查 Dockerfile 语法
- **上下文路径错误**：确保工作流中的 `context: ./v2` 路径正确

### 无法拉取镜像

```bash
# 检查镜像是否存在
docker manifest inspect ghcr.io/YOUR_USERNAME/YOUR_REPO/vertex-ai-proxy-v2:latest

# 如果是私有镜像，确保已登录
docker login ghcr.io
```

### 镜像过大

优化建议：
- 使用 `.dockerignore` 排除不必要的文件
- 使用多阶段构建
- 清理不需要的依赖

## 📚 相关链接

- [GitHub Packages 文档](https://docs.github.com/packages)
- [GitHub Actions 文档](https://docs.github.com/actions)
- [Docker 文档](https://docs.docker.com/)

## 💡 最佳实践

1. **使用版本标签**：生产环境使用特定版本而非 `latest`
2. **定期更新**：及时拉取最新的安全更新
3. **备份数据**：定期备份 `credentials.json` 和 `stats.json`
4. **监控日志**：使用 `docker logs -f` 监控运行状态
5. **资源限制**：在生产环境中设置内存和 CPU 限制

```yaml
services:
  vertex-ai-proxy:
    # ... 其他配置 ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 📞 支持

如有问题，请在 GitHub 仓库中提交 Issue。