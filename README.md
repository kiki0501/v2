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

### 方式 1: Docker WebSocket 模式（推荐）

```bash
# 1. 启动服务
docker-compose up -d

# 2. 在浏览器中安装油猴脚本
# 访问 http://localhost:7860 获取脚本

# 3. 打开 Vertex AI Studio
# https://console.cloud.google.com/vertex-ai/generative/multimodal/create/text

# 4. 脚本会自动连接并发送凭证
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

## 🔧 环境变量

| 变量 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| `BROWSER_MODE` | 凭证获取模式 | `manual` | `manual`, `websocket`, `headful` |
| `API_KEY` | API 认证密钥 | `your-secret-api-key-here` | 任意字符串 |
| `NOGUI` | 禁用 GUI | `1` | `0`, `1` |
| `PORT_API` | API 端口 | `7860` | 任意端口 |
| `PORT_WS` | WebSocket 端口 | `28881` | 任意端口 |

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

需要使用 API Key 进行认证（在 Header 中添加 `X-API-Key`）。

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
