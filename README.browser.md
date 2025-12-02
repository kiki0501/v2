# Vertex AI Proxy v2 - 浏览器版本

这是 Vertex AI Proxy v2 的浏览器版本，在 Docker 容器中运行完整的 Chrome 浏览器，通过 noVNC 提供 Web 界面访问。

## 🌟 特性

- ✅ **完整的浏览器环境**：在 Docker 中运行 Chrome 浏览器
- ✅ **Web 界面访问**：通过 noVNC 在浏览器中访问容器内的浏览器
- ✅ **自动启动**：容器启动时自动打开 Vertex AI Studio
- ✅ **持久化登录**：浏览器数据保存在 Docker volume 中
- ✅ **改进的遮挡处理**：参考 vvv 实现，自动处理 overlay 遮挡

## 📋 前置要求

- Docker 和 Docker Compose
- 至少 4GB 可用内存
- Google 账号（需要 Vertex AI 访问权限）

## 🚀 快速开始

### 1. 构建并启动容器

```bash
cd v2
docker-compose -f docker-compose.browser.yml up -d
```

### 2. 访问浏览器界面

打开浏览器访问：**http://localhost:6080**

您将看到运行在 Docker 容器中的 Chrome 浏览器。

### 3. 安装 Tampermonkey 和用户脚本

在容器内的浏览器中：

1. **安装 Tampermonkey 扩展**
   - 访问 Chrome Web Store
   - 搜索并安装 "Tampermonkey"
   - 或访问：https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo

2. **安装 Harvester 用户脚本**
   - 点击 Tampermonkey 图标 → "创建新脚本"
   - 复制 `vertex-ai-harvester.user.js` 的内容
   - 粘贴到编辑器并保存（Ctrl+S）

3. **登录 Google 账号**
   - 浏览器会自动打开 Vertex AI Studio
   - 使用您的 Google 账号登录

4. **验证安装**
   - 刷新页面
   - 在左下角应该看到 "Vertex AI Harvester" 窗口
   - 显示 "✅ Connected to ws://127.0.0.1:28881"

### 4. 测试代理

```bash
curl http://localhost:7860/v1/models
```

## 🔧 配置

### 环境变量

在 `docker-compose.browser.yml` 中配置：

```yaml
environment:
  - API_KEY=your-secret-api-key-here  # API 密钥
  - VNC_PASSWORD=vertex                # VNC 密码
```

### 端口说明

| 端口 | 用途 |
|------|------|
| 7860 | API 服务端口 |
| 28881 | WebSocket 端口（用户脚本连接） |
| 6080 | noVNC Web 界面 |
| 5900 | VNC 直连端口 |

## 📊 查看日志

```bash
# 查看所有日志
docker-compose -f docker-compose.browser.yml logs -f

# 查看特定服务日志
docker logs vertex-ai-proxy-v2-browser

# 查看浏览器日志
docker exec vertex-ai-proxy-v2-browser cat /var/log/supervisor/chrome.log
```

## 🔍 故障排除

### 浏览器无法启动

```bash
# 检查 X 服务器状态
docker exec vertex-ai-proxy-v2-browser ps aux | grep Xvfb

# 重启容器
docker-compose -f docker-compose.browser.yml restart
```

### 用户脚本未连接

1. 检查 WebSocket 端口是否开放：
   ```bash
   curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     http://localhost:28881
   ```

2. 在浏览器控制台查看错误信息（F12）

3. 确认 Harvester 窗口显示连接状态

### noVNC 无法访问

```bash
# 检查 noVNC 进程
docker exec vertex-ai-proxy-v2-browser ps aux | grep novnc

# 检查端口映射
docker port vertex-ai-proxy-v2-browser
```

## 🎯 改进的遮挡处理

本版本参考 vvv 的实现，改进了用户脚本中的遮挡手势处理：

### 新增功能

1. **`dismissOverlays()` 函数**
   - 自动关闭 Material Design 对话框
   - 按 Escape 键关闭模态窗口
   - 查找并点击关闭按钮

2. **`tryJavaScriptSend()` 策略**
   - 使用 JavaScript 直接操作，绕过 overlay
   - 作为第一优先级发送策略

3. **增强的错误处理**
   - 检测 overlay 遮挡错误
   - 自动重试机制

### 技术细节

参考文件：
- `vvv/src/headless/browser.py` - `_dismiss_overlays()` 方法
- `vvv/src/headless/terms_handler.py` - 条款处理逻辑

## 🔄 更新

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose -f docker-compose.browser.yml build

# 重启容器
docker-compose -f docker-compose.browser.yml up -d
```

## 🛑 停止服务

```bash
docker-compose -f docker-compose.browser.yml down
```

## 📝 注意事项

1. **内存要求**：Chrome 浏览器需要较多内存，建议至少 4GB
2. **登录持久化**：浏览器数据保存在 Docker volume 中，删除 volume 会清除登录状态
3. **安全性**：VNC 密码默认为 `vertex`，建议修改
4. **性能**：noVNC 可能有轻微延迟，可使用 VNC 客户端直连 5900 端口

## 🆚 与标准版本的区别

| 特性 | 标准版本 | 浏览器版本 |
|------|---------|-----------|
| 浏览器位置 | 本地 | Docker 容器内 |
| 访问方式 | 本地浏览器 | noVNC Web 界面 |
| 用户脚本安装 | 本地安装 | 容器内安装 |
| 登录持久化 | 本地浏览器 | Docker volume |
| 资源占用 | 较低 | 较高 |

## 📚 相关文档

- [标准版本 README](README.md)
- [用户脚本说明](vertex-ai-harvester.user.js)
- [vvv 参考实现](../vvv/README.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License