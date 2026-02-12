# 多用户SaaS平台后端架构分析

## 项目概述

基于现有代码分析，这是一个AI驱动的剧本批量拆解系统，需要从单用户原型升级为多用户SaaS平台。

**当前技术栈:**
- Flask (Python 3.x)
- SQLite (需迁移到PostgreSQL)
- 多AI提供商集成 (Claude/DeepSeek/Gemini/GPT-4)

**核心业务流程:**
1. 用户上传剧本 → 2. AI提取资产 → 3. 去重检测 → 4. 资产库管理 → 5. 分镜生成

---

## 1. 架构选型: 单体 vs 微服务

### 推荐方案: **模块化单体架构 (Modular Monolith)**

**理由:**

#### 为什么不选微服务?
1. **团队规模**: 微服务需要更多运维资源和DevOps能力
2. **业务复杂度**: 当前业务逻辑紧密耦合(项目→剧集→资产→分镜)，强行拆分会增加分布式事务复杂度
3. **开发速度**: 单体架构可以更快迭代，适合MVP和早期产品验证
4. **成本**: 微服务需要更多基础设施(服务发现、API网关、消息队列等)

#### 模块化单体的优势
1. **清晰的模块边界**: 按业务领域划分模块，为未来微服务化预留空间
2. **简化部署**: 单一部署单元，降低运维复杂度
3. **性能优势**: 进程内调用，无网络开销
4. **易于调试**: 统一日志、统一追踪
5. **渐进式演进**: 当某个模块成为瓶颈时，可以独立拆分为微服务

### 架构分层设计

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway Layer                     │
│  (Flask Blueprint + CORS + Rate Limiting + Auth)        │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │  Auth    │  │ Project  │  │  Asset   │  │Storyboard││
│  │ Service  │  │ Service  │  │ Service  │  │ Service  ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    Domain Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │   User   │  │ Project  │  │  Asset   │  │AI Gateway││
│  │  Domain  │  │  Domain  │  │  Domain  │  │  Domain  ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                Infrastructure Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │PostgreSQL│  │  Redis   │  │  Celery  │  │ AI APIs ││
│  │   ORM    │  │  Cache   │  │  Worker  │  │ Clients ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
└─────────────────────────────────────────────────────────┘
```

### 模块划分原则

**核心模块:**

1. **auth_module**: 用户认证、授权、会话管理
2. **project_module**: 项目管理、剧集上传
3. **asset_module**: 资产提取、去重、合并
4. **storyboard_module**: 分镜生成、资产引用
5. **ai_gateway_module**: AI服务统一网关
6. **billing_module**: 配额管理、计费(未来扩展)

**每个模块包含:**
- `routes.py`: API路由定义
- `services.py`: 业务逻辑
- `models.py`: 数据模型
- `schemas.py`: 请求/响应验证(Pydantic)
- `exceptions.py`: 自定义异常

---

## 2. 数据库架构设计

### 2.1 SQLite → PostgreSQL 迁移策略

**迁移原因:**
- SQLite不支持并发写入(多用户场景)
- 缺少高级特性(全文搜索、JSON查询、分区表)
- 无法水平扩展

**迁移步骤:**

#### Phase 1: 双写模式(过渡期)
```python
# 同时写入SQLite和PostgreSQL，读取仍从SQLite
# 验证数据一致性
```

#### Phase 2: 切换读取
```python
# 读取切换到PostgreSQL
# SQLite作为备份
```

#### Phase 3: 完全迁移
```python
# 移除SQLite依赖
```

### 2.2 数据库连接池配置

**推荐配置 (SQLAlchemy + psycopg2):**

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@localhost/dbname',
    poolclass=QueuePool,
    pool_size=20,              # 核心连接数
    max_overflow=10,           # 最大溢出连接
    pool_timeout=30,           # 获取连接超时(秒)
    pool_recycle=3600,         # 连接回收时间(秒)
    pool_pre_ping=True,        # 连接健康检查
    echo=False,                # 生产环境关闭SQL日志
    connect_args={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000'  # 查询超时30秒
    }
)
```

**连接池大小计算公式:**
```
pool_size = (核心数 * 2) + 磁盘数
```

对于4核服务器: `pool_size = 4 * 2 + 1 = 9` (保守估计20已足够)

**监控指标:**
- 连接池使用率 (应保持在70%以下)
- 连接等待时间
- 连接泄漏检测

### 2.3 数据库索引优化

**必须添加的索引:**

```sql
-- 用户表
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- 项目表
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_updated_at ON projects(updated_at);

-- 剧集表
CREATE INDEX idx_episodes_project_id ON episodes(project_id);
CREATE INDEX idx_episodes_upload_status ON episodes(upload_status);
CREATE UNIQUE INDEX idx_episodes_project_episode ON episodes(project_id, episode_number);

-- 资产表
CREATE INDEX idx_assets_project_id ON assets(project_id);
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_deleted ON assets(is_deleted) WHERE is_deleted = false;
CREATE INDEX idx_assets_name_gin ON assets USING gin(name gin_trgm_ops); -- 模糊搜索

-- 资产提取记录
CREATE INDEX idx_extraction_episode_id ON asset_extraction_records(episode_id);
CREATE INDEX idx_extraction_dedup_status ON asset_extraction_records(dedup_status);

-- 分镜表
CREATE INDEX idx_storyboards_episode_id ON storyboards(episode_id);
CREATE INDEX idx_storyboards_snapshot_id ON storyboards(snapshot_id);
```

**复合索引(覆盖查询):**

```sql
-- 查询用户的活跃项目
CREATE INDEX idx_projects_user_status ON projects(user_id, status, updated_at DESC);

-- 查询项目的未处理剧集
CREATE INDEX idx_episodes_project_status ON episodes(project_id, upload_status);
```

### 2.4 数据库分区策略(未来扩展)

当数据量增长到百万级时，考虑分区:

```sql
-- 按时间分区(项目表)
CREATE TABLE projects (
    id SERIAL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    ...
) PARTITION BY RANGE (created_at);

CREATE TABLE projects_2024 PARTITION OF projects
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE projects_2025 PARTITION OF projects
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

---

## 3. 事务管理策略

### 3.1 事务边界定义

**原则: 事务应该尽可能小，只包含必须原子执行的操作**

#### 反模式(当前代码问题):
```python
# ❌ 错误: 事务包含AI调用(可能耗时几分钟)
@app.route('/api/episodes/<int:episode_id>/extract-assets', methods=['POST'])
def extract_assets_from_episode(episode_id):
    conn = get_db()
    cursor = conn.cursor()

    # 更新状态
    cursor.execute("UPDATE episodes SET upload_status = 'ANALYZING' WHERE id = ?", (episode_id,))
    conn.commit()

    # ❌ 在事务中调用AI(长时间阻塞)
    ai_service = get_ai_service(model)
    extraction_result = ai_service.extract_assets(script_content, episode_number)

    # 插入资产
    for char in extraction_result.get('characters', []):
        cursor.execute("INSERT INTO assets ...")

    conn.commit()
```

#### 正确模式:
```python
# ✅ 正确: 将AI调用移到事务外，使用异步任务
@app.route('/api/episodes/<int:episode_id>/extract-assets', methods=['POST'])
def extract_assets_from_episode(episode_id):
    # 1. 快速验证和状态更新(短事务)
    with db.session.begin():
        episode = Episode.query.get_or_404(episode_id)
        if episode.upload_status == 'COMPLETED':
            raise BadRequest("已提取过资产")

        episode.upload_status = 'ANALYZING'
        db.session.flush()

    # 2. 提交异步任务(无事务)
    task = extract_assets_task.delay(episode_id, model)

    return success_response({
        "task_id": task.id,
        "status": "processing"
    })
```

### 3.2 分布式事务处理(Saga模式)

对于跨模块的复杂操作，使用Saga编排模式:

**场景: 用户删除项目**
1. 删除项目记录
2. 删除所有剧集
3. 删除所有资产
4. 删除所有分镜
5. 清理存储文件
6. 扣减配额

**实现方式:**

```python
class DeleteProjectSaga:
    def __init__(self, project_id):
        self.project_id = project_id
        self.compensations = []  # 补偿操作栈

    def execute(self):
        try:
            # Step 1: 软删除项目
            self._mark_project_deleted()
            self.compensations.append(self._restore_project)

            # Step 2: 删除剧集
            self._delete_episodes()
            self.compensations.append(self._restore_episodes)

            # Step 3: 删除资产
            self._delete_assets()
            self.compensations.append(self._restore_assets)

            # Step 4: 清理文件(异步)
            cleanup_task.delay(self.project_id)

            # Step 5: 提交最终删除
            self._commit_deletion()

        except Exception as e:
            # 执行补偿操作(回滚)
            self._compensate()
            raise e

    def _compensate(self):
        """执行补偿操作(逆序)"""
        for compensation in reversed(self.compensations):
            try:
                compensation()
            except Exception as e:
                logger.error(f"补偿操作失败: {e}")
```

### 3.3 乐观锁 vs 悲观锁

**乐观锁(推荐用于资产编辑):**

```python
class Asset(Base):
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(Integer, default=1, nullable=False)  # 版本号
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 更新时检查版本
def update_asset(asset_id, data, expected_version):
    with db.session.begin():
        asset = Asset.query.filter_by(
            id=asset_id,
            version=expected_version
        ).with_for_update().first()

        if not asset:
            raise ConflictError("资产已被其他用户修改，请刷新后重试")

        asset.name = data['name']
        asset.version += 1  # 递增版本号
        db.session.flush()
```

**悲观锁(用于配额扣减):**

```python
def consume_quota(user_id, amount):
    with db.session.begin():
        # 行级锁(FOR UPDATE)
        user = User.query.filter_by(id=user_id).with_for_update().first()

        if user.quota_remaining < amount:
            raise InsufficientQuotaError("配额不足")

        user.quota_remaining -= amount
        user.quota_used += amount
        db.session.flush()
```

---

## 4. 多用户数据隔离

### 4.1 数据模型调整

**添加用户表和租户隔离:**

```python
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)

    # 配额管理
    quota_total = Column(Integer, default=100)  # 总配额(AI调用次数)
    quota_used = Column(Integer, default=0)
    quota_remaining = Column(Integer, default=100)

    # 订阅信息
    subscription_tier = Column(String, default='FREE')  # FREE/PRO/ENTERPRISE
    subscription_expires_at = Column(DateTime)

    # 状态
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)

    # 关系
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 新增
    name = Column(String, nullable=False)
    # ... 其他字段

    # 关系
    user = relationship("User", back_populates="projects")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_project_name'),  # 用户级唯一
    )
```

### 4.2 查询过滤器(自动注入user_id)

**使用Flask-Login + SQLAlchemy事件监听:**

```python
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.orm import Session

@event.listens_for(Session, "before_flush")
def receive_before_flush(session, flush_context, instances):
    """自动注入user_id"""
    for instance in session.new:
        if hasattr(instance, 'user_id') and instance.user_id is None:
            if current_user.is_authenticated:
                instance.user_id = current_user.id

# 查询过滤器
class UserScopedQuery(Query):
    def get(self, ident):
        obj = super().get(ident)
        if obj and hasattr(obj, 'user_id'):
            if obj.user_id != current_user.id:
                raise Forbidden("无权访问该资源")
        return obj

# 应用到模型
class Project(Base):
    query_class = UserScopedQuery
```

### 4.3 行级安全策略(PostgreSQL RLS)

**数据库层面的安全保障:**

```sql
-- 启用行级安全
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- 创建策略: 用户只能访问自己的项目
CREATE POLICY user_projects_policy ON projects
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

-- 应用层设置当前用户
SET app.current_user_id = 123;
```

**Python集成:**

```python
@contextmanager
def user_context(user_id):
    """设置当前用户上下文"""
    with db.engine.connect() as conn:
        conn.execute(text(f"SET LOCAL app.current_user_id = {user_id}"))
        yield conn

# 使用
with user_context(current_user.id):
    projects = Project.query.all()  # 自动过滤
```

---

## 下一部分预告

接下来将详细分析:
- AI服务网关设计(配额管理、重试机制、降级策略)
- 异步任务处理架构(Celery + Redis)
- 认证授权系统(JWT双Token机制)
- API设计规范(RESTful最佳实践)
- 限流和防滥用策略
- 日志和监控架构
- 部署架构方案

请确认是否继续输出下一部分?
