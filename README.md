# Vertex AI Proxy v2

基于 Google Vertex AI 的 OpenAI API 兼容代理服务器，支持多种凭证获取模式。

## 🌟 特性

- ✅ **OpenAI API 兼容**: 无缝替换 OpenAI API
- 🔄 **多种凭证模式**: Manual / WebSocket / Headful 三种模式
- 🌐 **有头浏览器模式**: 自动化浏览器可视化操作（新功能）
- 📊 **统计面板**: 实时查看使用统计
- 🔐 **API Key 认证**: 安全的 API 访问控制
- 🐳 **Docker 支持**: 一键部署
- 💬 **流式响应**: 支持 SSE 流式输出
- 🖼️ **图像生成**: 支持 Imagen 模型
- 🧠 **思维模式**: 支持 Gemini 2.0 思维模式

## 🎯 三种运行模式

### 1️⃣ Manual 模式（手动模式）
使用已保存的凭证文件，适合测试和离线使用。

```bash
BROWSER_MODE=manual python main.py
```

### 2️⃣ WebSocket 模式（原有模式）
通过浏览器油猴脚本自动获取凭证，适合日常使用。

```bash
BROWSER_MODE=websocket python main.py
```

### 3️⃣ Headful 模式（有头浏览器）⭐ 新功能
在 Docker 中自动运行可见浏览器，完全自动化获取凭证。

```bash
# 本地运行
bash start-headful.sh
# 或 Windows
start-headful.bat

# Docker 运行
docker-compose -f docker-compose.headful.yml up
```

## 📦 快速开始

### 配置环境变量

**首先创建 `.env` 文件**（必需步骤）：

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，设置你的 API Key
# API_KEY=your-secret-api-key-here  # 修改这里！
```

或者直接创建 `.env` 文件：
```bash
echo "API_KEY=your-custom-api-key" > .env
echo "BROWSER_MODE=headful" >> .env
```

### 方式 1: Docker WebSocket 模式（推荐）

```bash
# 1. 配置环境变量（见上方）
# 确保 .env 文件已创建并设置了 API_KEY

# 2. 启动服务
docker-compose up -d

# 3. 在浏览器中安装油猴脚本
# 访问 http://localhost:7860 获取脚本

# 4. 打开 Vertex AI Studio
# https://console.cloud.google.com/vertex-ai/generative/multimodal/create/text

# 5. 脚本会自动连接并发送凭证
```

### 方式 2: 有头浏览器模式

```bash
# Linux
bash start-headful.sh

# Windows
start-headful.bat

# 或使用 Docker
docker-compose -f docker-compose.headful.yml up
```

### 方式 3: 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# WebSocket 模式
BROWSER_MODE=websocket python main.py

# 有头浏览器模式（需先安装 Playwright）
pip install playwright
playwright install chromium
BROWSER_MODE=headful python main.py
```

## 🔧 环境变量配置

### 配置方式

有两种方式配置环境变量：

#### 1. 使用 .env 文件（推荐）

```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env 文件
API_KEY=your-custom-api-key-here
BROWSER_MODE=headful
```

#### 2. 直接修改 docker-compose.yml

编辑 `docker-compose.yml` 或 `docker-compose.headful.yml` 中的 `environment` 部分。

### 环境变量列表

| 变量 | 说明 | 默认值 | 可选值 | 是否必需 |
|------|------|--------|--------|----------|
| `API_KEY` | API 认证密钥（用于调用此反代服务） | `your-secret-api-key-here` | 任意字符串 | ⭐ **必需** |
| `BROWSER_MODE` | 凭证获取模式 | `manual` | `manual`, `websocket`, `headful` | 可选 |
| `NOGUI` | 禁用 GUI | `1` | `0`, `1` | 可选 |
| `PORT_API` | API 端口 | `7860` | 任意端口 | 可选 |
| `PORT_WS` | WebSocket 端口 | `28881` | 任意端口 | 可选 |

### ⚠️ 重要提示

- **API_KEY** 是用于访问此反代服务的密钥，不是 Google 的 API Key
- 建议使用强密码作为 API_KEY（长度 ≥ 16 字符）
- 不要将 API_KEY 提交到版本控制系统（.env 文件已在 .gitignore 中）

## 📡 API 使用

### 兼容 OpenAI API

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:7860/v1",
    api_key="your-secret-api-key-here"
)

response = client.chat.completions.create(
    model="gemini-2.0-flash-exp",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### 支持的模型

查看 [`models.json`](models.json) 获取完整的模型列表。

主要模型：
- `gemini-2.0-flash-exp` - 最新 Flash 模型
- `gemini-2.0-flash-thinking-exp` - 思维模式
- `gemini-1.5-pro` - Pro 模型
- `gemini-1.5-flash` - Flash 模型
- `imagen-3.0-*` - 图像生成模型

### 特殊功能

**思维模式（Thinking）**：
```python
# 使用后缀指定思维预算
model="gemini-2.0-flash-thinking-exp-low"   # 低预算 (8K tokens)
model="gemini-2.0-flash-thinking-exp-high"  # 高预算 (32K tokens)

# 或使用 max_tokens 参数
response = client.chat.completions.create(
    model="gemini-2.0-flash-thinking-exp",
    max_tokens=16384,  # 思维预算
    messages=[...]
)
```

**图像生成**：
```python
# 使用分辨率后缀
model="imagen-3.0-generate-001-1k"  # 1K 分辨率
model="imagen-3.0-generate-001-2k"  # 2K 分辨率
model="imagen-3.0-generate-001-4k"  # 4K 分辨率
```

## 📊 统计面板

访问 `http://localhost:7860/dashboard` 查看使用统计。

登录时需要输入你在 `.env` 文件中设置的 `API_KEY`。

## 🔄 模式对比

| 特性 | Manual | WebSocket | Headful |
|------|--------|-----------|---------|
| 自动化程度 | ❌ | ✅ 半自动 | ✅ 全自动 |
| 需要浏览器 | ❌ | ✅ 本地 | ✅ Docker 内 |
| 用户干预 | 高 | 中 | 低 |
| 可视化调试 | ❌ | ❌ | ✅ |
| 适用场景 | 测试 | 日常 | 生产 |
| Docker 支持 | ✅ | ✅ | ✅ |

## 📚 详细文档

- [有头浏览器模式详细说明](README.headful.md)
- [模型配置说明](models.json)

## 🛠️ 开发

### 项目结构

```
v2/
├── main.py                    # 主程序
├── gui.py                     # GUI 界面
├── stats_manager.py           # 统计管理
├── models.json                # 模型配置
├── requirements.txt           # Python 依赖
├── Dockerfile                 # Docker 镜像
├── docker-compose.yml         # WebSocket 模式
├── docker-compose.headful.yml # 有头浏览器模式
├── src/                       # 源代码
│   ├── __init__.py
│   ├── browser.py            # 浏览器管理
│   └── harvester.py          # 凭证抓取
├── static/                    # 静态文件
│   └── dashboard.html        # 统计面板
└── vertex-ai-harvester.user.js # 油猴脚本
```

### 构建 Docker 镜像

```bash
# 标准镜像
docker build -t vertex-ai-proxy-v2 .

# 多架构构建
docker buildx build --platform linux/amd64,linux/arm64 -t vertex-ai-proxy-v2 .
```

## 🐛 故障排除

### 问题：凭证获取失败

1. 确保已登录 Google 账号
2. 检查网络连接
3. 查看浏览器控制台日志

### 问题：Docker 中浏览器无法显示

```bash
# Linux: 授权 X11
xhost +local:docker

# 设置 DISPLAY
export DISPLAY=:0
```

### 问题：API 请求失败

1. 检查 API Key 是否正确
2. 确认凭证是否已获取
3. 查看服务器日志

## 📝 注意事项

1. **首次运行**: 首次运行有头浏览器模式时，需要手动登录 Google 账号
2. **凭证保存**: 凭证会自动保存到 `credentials.json`
3. **刷新机制**: 凭证约 50 分钟后自动刷新
4. **并发限制**: 建议单账号并发请求不超过 10 个

## 🆚 与 vvv 的区别

本项目 v2 版本相比 vvv 项目的主要区别：

| 特性 | vvv | v2 |
|------|-----|-----|
| 浏览器模式 | Headless（无头） | Headful（有头） |
| 可见窗口 | ❌ | ✅ |
| 调试难度 | 较难 | 容易 |
| 模式选择 | 单一 | 多种（3种） |
| 项目结构 | 模块化 | 简化 |

## 📄 许可证

MIT License

## 🙏 致谢

- Google Vertex AI
- Playwright
- FastAPI

## 🔗 相关链接

- [Google Vertex AI 文档](https://cloud.google.com/vertex-ai/docs)
- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
- [Playwright 文档](https://playwright.dev/python/)
