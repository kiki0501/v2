# Vertex AI Headful Proxy

这是一个基于 Python 和 浏览器脚本（Userscript）的 Vertex AI 代理工具。它允许你通过本地的 OpenAI 兼容接口（API）调用 Google Vertex AI 的强大模型（如 Gemini 1.5 Pro, Gemini 2.0 Flash 等），利用浏览器已登录的会话进行认证。

## ✨ 功能特点

*   **OpenAI 格式兼容**: 提供标准的 `/v1/chat/completions` 接口，可直接接入 NextChat, Chatbox, LobeChat 等常见 AI 客户端。
*   **自动凭证获取**: 通过 Tampermonkey 脚本自动从浏览器抓取 Vertex AI Studio 的请求头和 Token。
*   **自动保活与刷新**: 支持自动检测 Token 过期并触发浏览器刷新 Token，实现长时间稳定或 `max_tokens` 触发）。
    *   **图片生成**: 支持调用 Imagen 或 Gemini 的画图能力（通过 `-1k`, `-2k`, `-4k` 后缀触发）。
*   **可视化界面**: 提供简洁的 GUI 界面查看实时请求统计、Token 消耗和运行。
*   **多模型支持**: 支持 `models.json` 中配置的多种 Gemini 模型，包括最新的预览版。
*   **高级特性支持**:
    *   **思考模式 (Thinking Mode)**: 支持 Gemini 的思考过程（通过 `-low` 或 `-high` 后缀日志。

## 🛠️ 安装指南

### 1. 后端环境准备

确保你已安装 Python 3.8+。

1.  克隆或下载本项目到本地。
2.  安装依赖库：
    

```bash
    pip install -r requirements.txt
    ```### 2. 前端脚本安装

你需要一个支持用户脚本的浏览器扩展，推荐 **Tampermonkey** (油猴)。

1.  在浏览器中安装 Tampermonkey 扩展。
2.  点击 Tampermonkey 图标 -> "添加新脚本"。
3.  将 ```bash
python main.`vertex-ai-harvester.user.js` 文件的内容全部复制并粘贴到编辑器中。
4.  保存脚本 (Ctrl+S)。

## 🚀 使用教程

### 第一步：启动代理服务

在项目目录下运行 `main.py`：

py
```

启动后会出现一个 GUI 窗口，控制台会显示：
*   API 地址: `http://0.0.0.0:28880`
*   WebSocket 地址: `ws://0.0.0.0:28881`

### 第二步：获取凭证 (Harvesting)

1.  打开浏览器，登录 [Google Cloud Console - Vertex AI Studio](https://console.cloud.google.com/vertex-ai/studio/multimodal)。
2.  确保 Tampermonkey 脚本已启用。你应该能在页面左下角看到一个半透明的 "Vertex AI Harvester" 状态面板。
3.  **关键步骤**：在 Vertex AI Studio 的对话框中随便发送一条消息（例如 "Hello"）。
4.  脚本会自动拦截请求，并将凭证发送给本地代理服务。
5.  观察本地 GUI 或控制台，出现 `🔄 Credentials updated` 即表示凭证获取成功。

### 第三步：连接客户端

现在你可以使用任何支持 OpenAI 接口的客户端连接了。

*   **Base URL (接口地址)**: `http://127.0.0.1:28880/v1` (或者 `http://localhost:28880/v1`)
*   **API Key**: 任意填写 (例如 `sk-vertex-proxy`)
*   **Model (模型)**: 输入你想使用的模型名称，例如 `gemini-1.5-pro` 或 `gemini-2.0-flash-exp`。

## ⚙️ 高级用法

### 思考模式 (Thinking Mode)
对于支持思考的模型（如 Gemini 2.0 Flash Thinking），你可以通过以下方式触发：
*   **后缀法**: 在模型名后添加 `-low` (8k budget) 或 `-high` (32k budget)。
    *   例如: `gemini-2.0-flash-thinking-exp-low`
*   **参数法**: 设置 `max_tokens` 参数。代理会自动将其识别为思考预算。

### 图片生成
使用支持图片生成的模型时，可以通过后缀指定分辨率：
*   `-1k`: 1024x1024
*   `-2k`: 2048x2048 (如果模型支持)
*   例如: `gemini-2.5-flash-image-1k`

### 模型列表配置
你可以在 `models.json` 中修改或添加支持的模型列表和别名映射。

## ❓ 常见问题

**Q: 为什么提示 "Credentials might be stale"?**
A: Google 的 Token 有效期较短（通常 1 小时）。代理会自动尝试通过 WebSocket 通知浏览器刷新页面来获取新 Token。请保持浏览器中 Vertex AI Studio 页面处于打开状态。

**Q: 浏览器脚本没有反应？**
A: 请确保你处于 `console.cloud.google.com/vertex-ai` 下的页面，并且脚本已在 Tampermonkey 中启用。尝试刷新页面。

**Q: 如何在局域网其他设备使用？**
A: 代理默认监听 `0.0.0.0`，你可以使用运行代理电脑的局域网 IP 地址来访问。

## ⚠️ 免责声明

本项目仅供学习和研究使用。请遵守 Google Cloud Platform 的服务条款。不要将此工具用于非法用途。