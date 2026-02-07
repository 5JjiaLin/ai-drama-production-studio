# AI 剧本批量拆解工具

一个基于 AI 的剧本自动化分镜工具，支持将剧本智能拆解为专业的分镜脚本。

## 🌟 主要功能

- **深度剧本分析**：AI 深度理解剧情、挖掘细节、分析情绪
- **基础资产提取**：自动识别角色、道具、场景
- **智能分镜生成**：自动生成专业级分镜表（支持 50+ 分镜）
- **视觉风格定义**：生成统一的视觉风格指令
- **多模型支持**：Claude、DeepSeek、Gemini、GPT 等

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000 或显示的地址

### 构建生产版本

```bash
npm run build
npm run preview
```

## 🤖 支持的 AI 模型

### Claude (Anthropic)
- Sonnet 4.5 (推荐)
- Opus 4.5 (最强)
- Haiku 4.5 (经济)

### DeepSeek (深度求索)
- DeepSeek V3 (推荐)
- DeepSeek R1 (推理模型)

### Gemini (Google)
- Gemini 2.5 Flash
- Gemini 3 Pro High

### GPT (OpenAI)
- GPT-4o
- GPT-4o Mini

## ⚙️ API 配置

支持以下 API 接入方式：

1. **代理模式**：使用第三方 API 服务
2. **官方 API**：
   - Anthropic 官方 API
   - DeepSeek 官方 API
   - Google 官方 API
   - OpenAI 官方 API

### API Key 配置

方式一：在界面顶部直接输入 API Key

方式二：在项目根目录创建 `apikey.txt` 文件（会自动加载）

## 📊 性能优化

- **上下文长度**：支持 50 万字符剧本
- **输出 Token**：最高 65536 tokens
- **超时时间**：最长 15 分钟
- **智能分段**：超过 50 个分镜自动分段生成
- **批次大小**：每批 30-50 个分镜

## 📁 项目结构

```
├── App.tsx                    # 主应用组件
├── components/                # UI 组件
│   ├── Button.tsx
│   ├── DataTable.tsx
│   ├── FeedbackInput.tsx
│   └── StepIndicator.tsx
├── services/                  # 服务层
│   ├── gemini.ts             # AI 调用服务
│   ├── gemini-chunking.ts    # 分段生成逻辑
│   ├── apiConfig.ts          # API 配置
│   └── fileUtils.ts          # 文件处理
├── types.ts                   # TypeScript 类型定义
└── index.html                # HTML 入口

```

## 📖 使用文档

- [DeepSeek 使用说明](./DEEPSEEK使用说明.md)

## 🔧 技术栈

- **前端框架**：React 19
- **构建工具**：Vite
- **样式**：Tailwind CSS
- **语言**：TypeScript
- **AI SDK**：Google Generative AI SDK

## ⚠️ 注意事项

1. **API Key 安全**：不要将 API Key 提交到版本控制系统
2. **网络要求**：需要稳定的网络连接访问 AI API
3. **分镜数量**：建议单批次不超过 50 个分镜
4. **文件格式**：支持 .docx 和 .txt 格式的剧本文件

## 📝 更新日志

### v1.0.0 (2026-02-07)

- ✅ 完整的剧本拆解流程
- ✅ 多模型支持（Claude、DeepSeek、Gemini、GPT）
- ✅ 智能分段生成
- ✅ 深度剧本分析
- ✅ JSON 格式优化
- ✅ DeepSeek 官方 API 支持

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
