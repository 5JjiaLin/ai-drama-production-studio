# AI剧本批量拆解系统 - 后端说明

## 版本信息
- 版本: 2.0
- 架构: Flask + SQLite
- 更新时间: 2026-02-07

## 目录结构

```
backend/
├── app.py                  # Flask主应用
├── requirements.txt        # Python依赖
├── test_api.py            # API测试脚本
├── .env.example           # 环境变量示例
├── database/
│   ├── init_db.py         # 数据库初始化
│   └── schema.sql         # SQL表结构
└── services/              # 业务逻辑
    ├── __init__.py        # 模块初始化
    └── ai_service.py      # AI资产提取服务
```

## 快速开始

### 1. 安装Python依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制`.env.example`为`.env`并配置API密钥：

```bash
cp .env.example .env
```

编辑`.env`文件，至少配置一个AI模型的API密钥：

```env
# 至少配置一个
CLAUDE_API_KEY=your_claude_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 3. 初始化数据库

数据库会在首次启动时自动初始化，或手动执行：

```bash
python -m database.init_db
```

### 4. 启动后端服务

```bash
python app.py
```

后端将在 `http://localhost:5000` 启动

### 5. 测试API

在另一个终端运行：

```bash
python test_api.py
```

## API接口文档

### 基础接口

#### 健康检查
```
GET /api/health
```

### 项目管理

#### 创建项目
```
POST /api/projects
Body: {
  "name": "项目名称",
  "description": "项目描述"
}
```

#### 获取项目列表
```
GET /api/projects
```

#### 获取项目详情
```
GET /api/projects/{project_id}
```

#### 更新项目状态（新）
```
PUT /api/projects/{project_id}/status
Body: {
  "status": "ASSET_LOCKED"  // ASSET_BUILDING | ASSET_LOCKED | STORYBOARD_GENERATION | COMPLETED
}
```

**状态转换规则**：
- `ASSET_BUILDING` → `ASSET_LOCKED` (锁定资产库，创建快照)
- `ASSET_LOCKED` → `STORYBOARD_GENERATION` (开始分镜生成)
- `STORYBOARD_GENERATION` → `COMPLETED` (完成项目)

#### 获取项目统计（新）
```
GET /api/projects/{project_id}/statistics
```

返回剧集数、资产数、分镜数等统计信息。

#### 获取项目快照（新）
```
GET /api/projects/{project_id}/snapshots
```

返回资产库历史快照列表。

### 剧集管理

#### 上传剧集
```
POST /api/projects/{project_id}/episodes
Form Data:
  - episode_number: 集数
  - title: 标题
  - script_content: 剧本内容
  或
  - script_file: 剧本文件
```

### 资产管理

#### 获取项目资产
```
GET /api/projects/{project_id}/assets
```

#### AI资产提取（新）
```
POST /api/episodes/{episode_id}/extract-assets
Body: {
  "model": "claude"  // 可选: claude, deepseek, gemini, gpt4
}
```

**功能说明**：
- 从剧集剧本中自动提取角色、道具、场景
- 支持多AI模型切换
- 自动过滤低重要性资产（importance < 5）
- 记录提取历史供追溯

#### 检测重复资产（新）
```
GET /api/projects/{project_id}/assets/duplicates?threshold=0.8
```

**功能说明**：
- 检测项目中可能重复的资产
- 支持自定义相似度阈值（0-1，默认0.8）
- 返回重复组及合并建议
- 综合名称和描述相似度计算

#### 合并资产（新）
```
POST /api/assets/merge
Body: {
  "primary_asset_id": 1,
  "merge_asset_ids": [2, 3]
}
```

**功能说明**：
- 将多个资产合并为一个主资产
- 自动转移分镜引用关系
- 记录合并历史供审计
- 软删除被合并的资产

## AI服务

### 支持的模型

1. **Claude Sonnet 4.5** (推荐)
   - 模型ID: `claude-sonnet-4-5-20250929`
   - 优点: 理解能力强，JSON输出稳定
   - 需要: `CLAUDE_API_KEY`

2. **DeepSeek Chat**
   - 优点: 成本低，速度快
   - 需要: `DEEPSEEK_API_KEY`

3. **Google Gemini 2.0 Flash**
   - 优点: 免费额度大
   - 需要: `GEMINI_API_KEY`

4. **OpenAI GPT-4**
   - 优点: 稳定可靠
   - 需要: `OPENAI_API_KEY`

### Prompt工程

系统使用精心设计的Prompt确保：
- 严格JSON格式输出
- 按重要性过滤资产（importance >= 5）
- 详细描述便于后续分镜生成
- 角色名称统一化

### 资产提取流程

1. 用户上传剧集 → `extraction_status: PENDING`
2. 调用AI提取API → `extraction_status: PROCESSING`
3. AI返回结构化资产 → 插入数据库
4. 完成 → `extraction_status: COMPLETED`
5. 失败自动回滚 → `extraction_status: FAILED`

### 资产去重检测

使用多维度相似度算法检测重复资产：

1. **名称相似度**（权重0.7）
   - 使用SequenceMatcher算法
   - 去除空格、统一大小写
   - "张三" vs "老张" → 相似度计算

2. **描述相似度**（权重0.3）
   - Jaccard关键词重叠率
   - 中文分词 + 英文分词
   - 综合语义相似度

3. **合并策略**
   - 选择描述最详细的资产为主资产
   - 选择最早出现的资产为主资产
   - 自动转移所有引用关系

## 数据库

数据库文件存储在：`storage/projects/default.db`

包含9张表：
1. projects - 项目表
2. episodes - 剧集表
3. assets - 资产表
4. asset_extraction_records - 资产提取记录
5. asset_merge_history - 资产合并历史
6. asset_snapshots - 资产快照
7. storyboards - 分镜表
8. storyboard_asset_references - 分镜-资产关联
9. visual_styles - 视觉风格

## 下一步开发

- [x] 添加资产提取API（调用AI模型）✅ 已完成
- [x] 添加资产去重确认API ✅ 已完成
- [x] 添加项目状态管理API ✅ 已完成
- [ ] 添加分镜生成API
- [ ] 添加导出功能
- [ ] 前端集成

## 注意事项

1. 开发环境使用SQLite，生产环境可考虑PostgreSQL
2. AI API Key需要在`.env`文件中配置
3. 跨域CORS已启用，支持前端调用
4. 默认端口5000，可通过PORT环境变量修改
5. AI提取需要消耗API配额，请合理使用
