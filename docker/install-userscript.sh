#!/bin/bash
# 用户脚本安装辅助脚本
# 由于 Chrome 扩展需要手动安装，这个脚本提供安装说明

cat << 'EOF'

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   📦 Vertex AI Harvester 用户脚本安装说明                      ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

🌐 浏览器已启动！请按照以下步骤安装用户脚本：

步骤 1: 安装 Tampermonkey 扩展
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 在浏览器中访问 Chrome Web Store
  2. 搜索 "Tampermonkey" 并安装
  3. 或直接访问：
     https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo

步骤 2: 安装 Harvester 用户脚本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 点击浏览器工具栏中的 Tampermonkey 图标
  2. 选择 "创建新脚本"
  3. 将以下文件内容复制粘贴到编辑器中：
     /app/vertex-ai-harvester.user.js
  4. 按 Ctrl+S 保存脚本

步骤 3: 登录 Google 账号
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 浏览器会自动打开 Vertex AI Studio
  2. 使用您的 Google 账号登录
  3. 确保账号有 Vertex AI 访问权限

步骤 4: 验证安装
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 刷新 Vertex AI Studio 页面
  2. 您应该在页面左下角看到 "Vertex AI Harvester" 窗口
  3. 窗口显示 "✅ Connected to ws://127.0.0.1:28881"
  4. 发送一条测试消息，Harvester 会自动捕获凭证

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 提示：
  • 用户脚本文件位于：/app/vertex-ai-harvester.user.js
  • 您可以使用 VNC 查看器或 noVNC Web 界面访问浏览器
  • noVNC 地址：http://localhost:6080
  • VNC 密码：vertex

🔗 相关端口：
  • API 服务：http://localhost:7860
  • WebSocket：ws://localhost:28881
  • noVNC Web：http://localhost:6080
  • VNC 直连：localhost:5900

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF