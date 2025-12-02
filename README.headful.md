# Vertex AI Proxy v2 - 有头浏览器模式

本项目已集成 Playwright 浏览器自动化，支持三种凭证获取模式。

## 🎯 三种运行模式

### 1. Manual 模式（手动模式）
使用已保存的凭证文件，不需要浏览器。

```bash
# 本地运行
BROWSER_MODE=manual python main.py

# Docker 运行
docker-compose up
```

### 2. WebSocket 模式（原有模式）
通过浏览器中的油猴脚本自动获取凭证。

```bash
# 本地运行
BROWSER_MODE=websocket python main.py

# Docker 运行
BROWSER_MODE=websocket docker-compose up
```

### 3. Headful 模式（有头浏览器模式）⭐ 新功能
**自动在 Docker 中运行可见浏览器窗口，完全自动化获取凭证。**

```bash
# 本地运行（需要已安装 Playwright）
BROWSER_MODE=headful python main.py

# Docker 运行
docker-compose -f docker-compose.headful.yml up
```

## 📦 安装依赖

### 本地运行

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
playwright install-deps chromium
```

### Docker 运行

Docker 镜像已包含所有必要依赖，无需额外安装。

## 🚀 快速开始

### 方式 1: 本地有头浏览器模式

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 2. 设置环境变量
export BROWSER_MODE=headful
export API_KEY=your-secret-api-key

# 3. 运行
python main.py
```

浏览器窗口将自动打开并导航到 Vertex AI Studio，您可以看到整个自动化过程。

### 方式 2: Docker 有头浏览器模式

```bash
# 1. 构建镜像
docker-compose -f docker-compose.headful.yml build

# 2. 运行（Linux 需要配置 X11）
# Linux:
xhost +local:docker
docker-compose -f docker-compose.headful.yml up

# Windows/Mac:
# 需要先安装 VNC 服务器或使用无头模式
```

### 方式 3: Docker WebSocket 模式（推荐用于 Windows/Mac）

```bash
# 1. 启动服务
docker-compose up -d

# 2. 在本地浏览器中安装油猴脚本
# 访问 http://localhost:7860 获取脚本

# 3. 打开 Google Vertex AI Studio
# https://console.cloud.google.com/vertex-ai/generative/multimodal/create/text

# 4. 脚本将自动连接并发送凭证
```

## 🔧 环境变量说明

| 变量 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| `BROWSER_MODE` | 浏览器模式 | `manual` | `manual`, `websocket`, `headful` |
| `API_KEY` | API 密钥 | `your-secret-api-key-here` | 任意字符串 |
| `NOGUI` | 禁用 GUI | `1` | `0`, `1` |
| `DISPLAY` | X11 显示（Linux） | `:99` | `:0`, `:1`, 等 |

## 🎨 模式对比

| 特性 | Manual | WebSocket | Headful |
|------|--------|-----------|---------|
| 自动化程度 | ❌ 需手动更新 | ✅ 半自动 | ✅ 全自动 |
| 需要浏览器 | ❌ | ✅ 本地浏览器 | ✅ Docker 内 |
| 用户干预 | 高 | 中 | 低 |
| 适用场景 | 测试/离线 | 日常使用 | 生产部署 |
| Docker 支持 | ✅ | ✅ | ✅ (Linux) |
| Windows/Mac | ✅ | ✅ | ⚠️ 需 VNC |

## 🐧 Linux 上运行有头浏览器

```bash
# 1. 允许 Docker 访问 X11
xhost +local:docker

# 2. 使用主机的 DISPLAY
export DISPLAY=:0

# 3. 运行
docker-compose -f docker-compose.headful.yml up

# 4. 浏览器窗口将显示在您的桌面上
```

## 🪟 Windows/Mac 上运行有头浏览器

由于 Docker Desktop 不直接支持 GUI 应用，有两种方案：

### 方案 1: 使用 VNC（推荐）

1. 修改 `docker-compose.headful.yml`，添加 VNC 服务器
2. 使用 VNC 客户端连接到 `localhost:5900`
3. 在 VNC 窗口中查看浏览器

### 方案 2: 使用 WebSocket 模式

在 Windows/Mac 上推荐使用 WebSocket 模式：

```bash
docker-compose up
```

然后在本地浏览器中运行油猴脚本。

## 🔍 调试

### 查看日志

```bash
# Docker 日志
docker-compose logs -f

# 本地日志
python main.py  # 直接输出到控制台
```

### 测试 API

```bash
# 测试连接
curl -X POST http://localhost:7860/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "model": "gemini-2.0-flash-exp",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

## 📝 注意事项

1. **首次运行**: 首次运行有头浏览器模式时，需要手动登录 Google 账号
2. **凭证保存**: 凭证会自动保存到 `credentials.json`，重启后可直接使用
3. **刷新机制**: 凭证过期时（约 50 分钟），会自动触发刷新
4. **失败重试**: 连续失败 2 次后，会尝试重新导航到 Vertex AI Studio

## 🆚 与 vvv 的区别

| 特性 | vvv | v2 |
|------|-----|-----|
| 浏览器模式 | Headless（无头） | Headful（有头） |
| 可见窗口 | ❌ | ✅ |
| 调试难度 | 较难 | 容易 |
| 资源占用 | 低 | 中 |
| 适用场景 | 后台运行 | 可视化监控 |

## 🛠️ 故障排除

### 问题: 浏览器无法启动

```bash
# 检查 Playwright 是否正确安装
playwright install --with-deps chromium
```

### 问题: Docker 中无法显示浏览器窗口

```bash
# Linux: 检查 DISPLAY 环境变量
echo $DISPLAY

# 重新授权 X11
xhost +local:docker
```

### 问题: 凭证获取失败

1. 检查是否已登录 Google 账号
2. 检查网络连接
3. 查看浏览器日志

## 📚 更多信息

- [Playwright 文档](https://playwright.dev/python/)
- [Vertex AI 文档](https://cloud.google.com/vertex-ai/docs)
- [项目主页](../README.md)