# AI剧本批量拆解工具

一款基于AI的剧本分镜自动化工具，支持资产提取、去重检测和分镜生成。

## ✨ 核心功能

- **资产提取**：AI自动识别剧本中的角色、场景、道具
- **智能去重**：自动检测并合并重复资产
- **分镜生成**：根据剧本自动生成专业分镜表
- **深度剧本分析**：AI深度理解剧情、挖掘细节、分析情绪
- **多模型支持**：Claude、Gemini、DeepSeek
- **项目管理**：多项目、多剧集管理
- **导出功能**：支持CSV导出和表格复制

## 🚀 快速开始（Docker版 - 推荐）

### 前置要求
- Docker Desktop（Windows/Mac）或 Docker Engine（Linux）
- 至少4GB内存
- Claude API Key（必需）

### 3步启动

**Windows用户：**
```bash
# 1. 双击运行
start.bat

# 2. 首次运行会提示配置API Key
# 3. 等待启动完成，浏览器自动打开
```

**Mac/Linux用户：**
```bash
# 1. 添加执行权限
chmod +x start.sh

# 2. 运行启动脚本
./start.sh

# 3. 按提示配置API Key后重新运行
```

### 详细文档
- [Docker使用指南](./DOCKER使用指南.md) - 完整的Docker部署文档
- [API Key配置指南](./API_KEY配置指南.md) - API Key获取和配置

## 📖 使用流程

1. **注册账号** → 2. **创建项目** → 3. **提取资产** → 4. **生成分镜** → 5. **导出结果**

## 🤖 支持的AI模型

### Claude (Anthropic) - 推荐
- Sonnet 4.5 (推荐)
- Opus 4.5 (最强)
- Haiku 4.5 (经济)

### DeepSeek (深度求索)
- DeepSeek V3 (推荐)
- DeepSeek R1 (推理模型)

### Gemini (Google)
- Gemini 2.5 Flash
- Gemini 3 Pro High

## 🛠️ 技术栈

**前端：**
- React 18 + TypeScript
- Vite
- TailwindCSS

**后端：**
- Python 3.11 + Flask
- SQLite
- Anthropic Claude API

**部署：**
- Docker + Docker Compose
- Nginx

## 📦 本地开发

<details>
<summary>点击展开本地开发指南</summary>

### 后端启动
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 前端启动
```bash
npm install
npm run dev
```

### 环境变量
复制 `.env.example` 为 `.env` 并填写API Key。

</details>

## 🔧 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

## 📊 系统架构

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   浏览器    │ ───> │   Nginx     │ ───> │   Flask     │
│  (React)    │ <─── │  (前端)     │ <─── │   (后端)    │
└─────────────┘      └─────────────┘      └─────────────┘
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │   SQLite    │
                                           │  (数据库)   │
                                           └─────────────┘
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │ Claude API  │
                                           │  (AI服务)   │
                                           └─────────────┘
```

## 📁 项目结构

```
├── backend/                   # 后端服务
│   ├── app.py                # Flask应用入口
│   ├── routes/               # API路由
│   ├── services/             # 业务逻辑
│   ├── database/             # 数据库模型
│   └── Dockerfile            # 后端Docker配置
├── components/               # React组件
│   ├── AuthForm.tsx          # 认证表单
│   ├── ProjectList.tsx       # 项目列表
│   ├── AssetExtraction.tsx   # 资产提取
│   └── StoryboardGeneration.tsx  # 分镜生成
├── services/                 # 前端服务层
│   ├── authService.ts        # 认证服务
│   ├── projectService.ts     # 项目服务
│   └── storyboardService.ts  # 分镜服务
├── docker-compose.yml        # Docker编排配置
├── Dockerfile                # 前端Docker配置
├── nginx.conf                # Nginx配置
└── README.md                 # 项目文档
```

## 🔒 安全说明

- ⚠️ 不要将 `.env` 文件提交到Git
- ⚠️ 不要在公网暴露服务（仅本地使用）
- ⚠️ 定期更换API Key
- ⚠️ 使用强密码注册账号

## 📝 更新日志

### v2.0 (2026-02-12)
- ✅ 添加Docker支持，一键部署
- ✅ 完善分镜生成功能
- ✅ 优化AI提示词（强化剧情忠实原则）
- ✅ 修复项目管理bug（重复项目名、删除功能）
- ✅ 添加asset_mapping字段支持
- ✅ 完善用户认证系统
- ✅ 添加完整的后端API

### v1.0 (2026-02-07)
- ✅ 基础功能实现
- ✅ 多模型支持
- ✅ 智能分段生成

## 🤝 贡献

欢迎提交Issue和Pull Request。

## 📄 许可证

MIT License

## 📞 联系方式

- GitHub: [项目地址](https://github.com/5JjiaLin/01)
- Issues: [问题反馈](https://github.com/5JjiaLin/01/issues)

---

**Made with ❤️ by AI Script Team**
