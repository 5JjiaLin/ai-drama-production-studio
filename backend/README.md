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
├── database/
│   ├── init_db.py         # 数据库初始化
│   ├── models.py          # SQLAlchemy模型
│   └── schema.sql         # SQL表结构
├── api/                   # API路由（待添加）
└── services/              # 业务逻辑（待添加）
```

## 快速开始

### 1. 安装Python依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 初始化数据库

数据库会在首次启动时自动初始化，或手动执行：

```bash
python -m database.init_db
```

### 3. 启动后端服务

```bash
python app.py
```

后端将在 `http://localhost:5000` 启动

### 4. 测试API

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

- [ ] 添加资产提取API（调用AI模型）
- [ ] 添加资产去重确认API
- [ ] 添加分镜生成API
- [ ] 添加导出功能
- [ ] 前端集成

## 注意事项

1. 开发环境使用SQLite，生产环境可考虑PostgreSQL
2. API Key需要在环境变量中配置（.env.local）
3. 跨域CORS已启用，支持前端调用
4. 默认端口5000，可通过PORT环境变量修改
