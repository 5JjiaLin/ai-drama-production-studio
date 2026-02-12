# AI剧本批量拆解系统 - 性能优化方案

## 执行摘要

本文档针对多用户SaaS平台的性能瓶颈提供全面的优化方案，涵盖数据库、缓存、异步任务、前端性能和监控等关键领域。

### 系统特点
- 大文本处理（剧本10万字+）
- AI调用耗时长（30秒-3分钟）
- 实时进度反馈需求
- 多用户并发访问
- 复杂的多表关联查询

### 技术栈
- 后端：Flask + PostgreSQL + Redis + Celery
- 前端：React + Vite
- 部署：Docker + Nginx

---

## 1. 数据库性能优化

### 1.1 当前问题分析

**发现的问题：**
1. 使用SQLite作为生产数据库（不适合多用户并发）
2. 缺少索引优化
3. 大文本字段（script_content, description）存储在主表
4. 复杂的多表JOIN查询（项目→分集→资产→分镜）
5. N+1查询问题

**性能影响：**
- 并发写入锁表
- 查询响应时间 > 2秒
- 数据库文件膨胀

### 1.2 优化方案

#### 1.2.1 迁移到PostgreSQL

**理由：**
- 支持真正的并发写入（MVCC）
- 更好的JSON支持
- 全文搜索能力
- 连接池支持

**实施步骤：**
```python
# config.py
import os
from urllib.parse import quote_plus

class Config:
    # PostgreSQL配置
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'script_analysis')

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # 连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,          # 连接池大小
        'max_overflow': 40,       # 最大溢出连接
        'pool_timeout': 30,       # 连接超时
        'pool_recycle': 3600,     # 连接回收时间
        'pool_pre_ping': True,    # 连接健康检查
    }
```

#### 1.2.2 索引优化策略

**关键索引设计：**

```sql
-- 项目表索引
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_updated_at ON projects(updated_at DESC);

-- 剧集表索引
CREATE INDEX idx_episodes_project_id ON episodes(project_id);
CREATE INDEX idx_episodes_upload_status ON episodes(upload_status);
CREATE INDEX idx_episodes_project_episode ON episodes(project_id, episode_number);

-- 资产表索引（最关键）
CREATE INDEX idx_assets_project_id ON assets(project_id) WHERE is_deleted = false;
CREATE INDEX idx_assets_type_project ON assets(asset_type, project_id) WHERE is_deleted = false;
CREATE INDEX idx_assets_first_appeared ON assets(first_appeared_episode_id);
CREATE INDEX idx_assets_name_gin ON assets USING gin(to_tsvector('simple', name)); -- 全文搜索

-- 资产提取记录索引
CREATE INDEX idx_extraction_episode ON asset_extraction_records(episode_id);
CREATE INDEX idx_extraction_asset ON asset_extraction_records(asset_id);
CREATE INDEX idx_extraction_dedup_status ON asset_extraction_records(dedup_status);

-- 分镜表索引
CREATE INDEX idx_storyboards_episode ON storyboards(episode_id);
CREATE INDEX idx_storyboards_snapshot ON storyboards(snapshot_id);
CREATE INDEX idx_storyboards_episode_shot ON storyboards(episode_id, shot_number);

-- 分镜资产关联索引
CREATE INDEX idx_storyboard_refs_storyboard ON storyboard_asset_references(storyboard_id);
CREATE INDEX idx_storyboard_refs_asset ON storyboard_asset_references(asset_id);
```

**索引使用建议：**
- 复合索引顺序：高选择性字段在前
- 部分索引（WHERE条件）减少索引大小
- GIN索引用于全文搜索和JSON字段

#### 1.2.3 大文本字段优化

**问题：** script_content字段可能达到10万字，影响查询性能

**解决方案：表分离策略**

```python
# 新增剧本内容表
class EpisodeContent(Base):
    """剧本内容表（分离大文本）"""
    __tablename__ = 'episode_contents'

    episode_id = Column(Integer, ForeignKey('episodes.id'), primary_key=True)
    script_content = Column(Text, nullable=False)
    content_hash = Column(String(64))  # SHA256哈希，用于去重
    word_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

# 修改Episode模型
class Episode(Base):
    __tablename__ = 'episodes'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    episode_number = Column(Integer)
    title = Column(String)
    upload_status = Column(String, default='UPLOADED')
    word_count = Column(Integer)  # 冗余字段，避免JOIN

    # 关系（懒加载）
    content = relationship("EpisodeContent", lazy='select', uselist=False)
```

**优势：**
- 列表查询不加载大文本（减少90%数据传输）
- 只在需要时加载内容
- 支持内容去重检测

#### 1.2.4 查询优化

**优化前（N+1问题）：**
```python
# app.py line 157 - get_project()
# 存在多次单独查询
cursor.execute("SELECT COUNT(*) FROM episodes WHERE project_id = ?", (project_id,))
cursor.execute("SELECT COUNT(*) FROM assets WHERE project_id = ?", (project_id,))
cursor.execute("SELECT COUNT(*) FROM storyboards...")
```

**优化后（单次JOIN查询）：**
```python
@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project_optimized(project_id):
    """优化后的项目详情查询"""
    query = """
        SELECT
            p.id, p.name, p.description, p.status,
            p.created_at, p.updated_at,
            COUNT(DISTINCT e.id) as episode_count,
            COUNT(DISTINCT a.id) as asset_count,
            COUNT(DISTINCT s.id) as storyboard_count
        FROM projects p
        LEFT JOIN episodes e ON e.project_id = p.id
        LEFT JOIN assets a ON a.project_id = p.id AND a.is_deleted = false
        LEFT JOIN storyboards s ON s.episode_id = e.id
        WHERE p.id = %s
        GROUP BY p.id
    """

    cursor.execute(query, (project_id,))
    row = cursor.fetchone()

    if not row:
        return error_response("项目不存在", 404)

    return success_response({
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "status": row[3],
        "created_at": row[4],
        "updated_at": row[5],
        "episode_count": row[6],
        "asset_count": row[7],
        "storyboard_count": row[8]
    })
```

**性能提升：** 3-4次查询 → 1次查询，响应时间减少60%

#### 1.2.5 分页和限制

**实施分页策略：**
```python
@app.route('/api/projects/<int:project_id>/assets', methods=['GET'])
def get_project_assets_paginated(project_id):
    """分页获取资产列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    asset_type = request.args.get('type', None)

    # 限制每页最大数量
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # 构建查询
    query = """
        SELECT
            id, asset_type, name, description,
            gender, age, voice, role, created_at
        FROM assets
        WHERE project_id = %s AND is_deleted = false
    """
    params = [project_id]

    if asset_type:
        query += " AND asset_type = %s"
        params.append(asset_type)

    # 获取总数
    count_query = f"SELECT COUNT(*) FROM ({query}) as t"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # 分页查询
    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    cursor.execute(query, params)
    assets = [dict(zip([col[0] for col in cursor.description], row))
              for row in cursor.fetchall()]

    return success_response({
        "assets": assets,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    })
```

---

## 2. 缓存架构设计

### 2.1 多层缓存策略

**缓存层级：**
1. **应用层缓存**（Redis）- 热数据、会话、任务状态
2. **数据库查询缓存**（PostgreSQL）- 查询结果集
3. **CDN缓存**（Nginx）- 静态资源
4. **浏览器缓存** - API响应、资源文件

### 2.2 Redis缓存实现

**配置Redis连接池：**
```python
# cache.py
import redis
import json
from functools import wraps
from typing import Any, Optional, Callable
import hashlib

class CacheManager:
    """Redis缓存管理器"""

    def __init__(self, redis_url: str = 'redis://localhost:6379/0'):
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            max_connections=50,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        try:
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(value, ensure_ascii=False)
            )
        except Exception as e:
            print(f"Cache set error: {e}")

    def delete(self, key: str):
        """删除缓存"""
        try:
            self.redis_client.delete(key)
        except Exception as e:
            print(f"Cache delete error: {e}")

    def delete_pattern(self, pattern: str):
        """批量删除匹配的键"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache delete pattern error: {e}")

# 全局缓存实例
cache = CacheManager()

def cache_response(key_prefix: str, ttl: int = 3600):
    """缓存装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{hashlib.md5(str(args).encode()).hexdigest()}"

            # 尝试从缓存获取
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

**使用示例：**
```python
@app.route('/api/projects/<int:project_id>', methods=['GET'])
@cache_response('project_detail', ttl=300)  # 缓存5分钟
def get_project(project_id):
    # 原有逻辑
    pass
```

### 2.3 缓存策略表

| 数据类型 | 缓存位置 | TTL | 失效策略 |
|---------|---------|-----|---------|
| 项目列表 | Redis | 5分钟 | 创建/更新项目时删除 |
| 项目详情 | Redis | 5分钟 | 项目状态变更时删除 |
| 资产列表 | Redis | 10分钟 | 资产增删改时删除 `project:{id}:assets:*` |
| 去重结果 | Redis | 30分钟 | 资产变更时删除 |
| AI提取结果 | Redis | 1小时 | 不主动失效 |
| 任务状态 | Redis | 实时 | 任务完成时删除 |
| 用户会话 | Redis | 24小时 | 登出时删除 |

### 2.4 缓存失效策略

**写入时失效（Write-Through）：**
```python
@app.route('/api/projects/<int:project_id>/assets', methods=['POST'])
def create_asset(project_id):
    """创建资产并清除相关缓存"""
    try:
        # 创建资产逻辑
        # ...

        # 清除相关缓存
        cache.delete_pattern(f'project:{project_id}:assets:*')
        cache.delete(f'project_detail:{project_id}')
        cache.delete(f'project_stats:{project_id}')

        return success_response(asset)
    except Exception as e:
        return error_response(str(e))
```

### 2.5 防止缓存穿透/击穿/雪崩

**缓存穿透（查询不存在的数据）：**
```python
def get_with_null_cache(key: str, fetch_func: Callable, ttl: int = 300):
    """支持空值缓存"""
    cached = cache.get(key)

    if cached == "NULL":  # 空值标记
        return None

    if cached is not None:
        return cached

    # 从数据库获取
    result = fetch_func()

    if result is None:
        cache.set(key, "NULL", ttl=60)  # 空值缓存1分钟
    else:
        cache.set(key, result, ttl)

    return result
```

**缓存击穿（热点数据过期）：**
```python
import threading

locks = {}

def get_with_lock(key: str, fetch_func: Callable, ttl: int = 300):
    """使用分布式锁防止击穿"""
    cached = cache.get(key)
    if cached is not None:
        return cached

    # 获取分布式锁
    lock_key = f"lock:{key}"
    lock = cache.redis_client.set(lock_key, "1", nx=True, ex=10)

    if lock:
        try:
            result = fetch_func()
            cache.set(key, result, ttl)
            return result
        finally:
            cache.delete(lock_key)
    else:
        # 等待其他线程完成
        import time
        time.sleep(0.1)
        return get_with_lock(key, fetch_func, ttl)
```

**缓存雪崩（大量key同时过期）：**
```python
import random

def set_with_jitter(key: str, value: Any, ttl: int):
    """添加随机过期时间"""
    jitter = random.randint(0, int(ttl * 0.1))  # 10%抖动
    cache.set(key, value, ttl + jitter)
```

---

## 3. 异步任务队列优化

### 3.1 Celery配置优化

**celery_config.py：**
```python
from kombu import Queue, Exchange

class CeleryConfig:
    # Broker配置（使用Redis）
    broker_url = 'redis://localhost:6379/1'
    result_backend = 'redis://localhost:6379/2'

    # 任务序列化
    task_serializer = 'json'
    result_serializer = 'json'
    accept_content = ['json']
    timezone = 'Asia/Shanghai'
    enable_utc = True

    # 性能优化
    worker_prefetch_multiplier = 1  # 每次只取1个任务（长任务）
    worker_max_tasks_per_child = 50  # 防止内存泄漏
    task_acks_late = True  # 任务完成后才确认
    task_reject_on_worker_lost = True  # worker崩溃时重新入队

    # 任务超时
    task_soft_time_limit = 300  # 5分钟软限制
    task_time_limit = 360  # 6分钟硬限制

    # 结果过期
    result_expires = 3600  # 1小时后清理结果

    # 任务路由（不同队列处理不同任务）
    task_routes = {
        'tasks.ai_extraction': {'queue': 'ai_tasks'},
        'tasks.deduplication': {'queue': 'cpu_tasks'},
        'tasks.notification': {'queue': 'default'},
    }

    # 队列定义
    task_queues = (
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('ai_tasks', Exchange('ai_tasks'), routing_key='ai_tasks'),
        Queue('cpu_tasks', Exchange('cpu_tasks'), routing_key='cpu_tasks'),
    )
```

### 3.2 AI提取任务实现

**tasks/ai_tasks.py：**
```python
from celery import Celery, Task
from celery.signals import task_prerun, task_postrun, task_failure
import time

celery_app = Celery('script_analysis')
celery_app.config_from_object('celery_config.CeleryConfig')

class CallbackTask(Task):
    """支持进度回调的任务基类"""

    def update_progress(self, task_id: str, progress: int, message: str):
        """更新任务进度到Redis"""
        from cache import cache
        cache.set(
            f'task_progress:{task_id}',
            {
                'progress': progress,
                'message': message,
                'timestamp': time.time()
            },
            ttl=3600
        )

@celery_app.task(bind=True, base=CallbackTask, queue='ai_tasks')
def extract_assets_async(self, episode_id: int, model: str = 'claude'):
    """异步AI资产提取任务"""
    from services.ai_service import get_ai_service, AIModel
    from database.models import get_session, Episode
    from cache import cache

    try:
        # 更新进度：0%
        self.update_progress(self.request.id, 0, '开始提取资产...')

        # 获取剧集数据
        session = get_session()
        episode = session.query(Episode).filter_by(id=episode_id).first()

        if not episode:
            raise ValueError(f"剧集 {episode_id} 不存在")

        # 更新进度：10%
        self.update_progress(self.request.id, 10, '正在调用AI模型...')

        # 调用AI服务
        ai_service = get_ai_service(AIModel(model))
        result = ai_service.extract_assets(
            episode.script_content,
            episode.episode_number
        )

        # 更新进度：70%
        self.update_progress(self.request.id, 70, '正在保存资产到数据库...')

        # 保存到数据库（省略具体实现）
        # ...

        # 更新进度：100%
        self.update_progress(self.request.id, 100, '提取完成')

        # 清除相关缓存
        cache.delete_pattern(f'project:{episode.project_id}:*')

        return {
            'episode_id': episode_id,
            'extracted_count': len(result.get('characters', [])) +
                             len(result.get('props', [])) +
                             len(result.get('scenes', []))
        }

    except Exception as e:
        self.update_progress(self.request.id, -1, f'提取失败: {str(e)}')
        raise

### 3.3 API集成异步任务

**修改后的API端点：**
```python
@app.route('/api/episodes/<int:episode_id>/extract-assets', methods=['POST'])
def extract_assets_endpoint(episode_id):
    """提交异步提取任务"""
    from tasks.ai_tasks import extract_assets_async

    data = request.get_json() or {}
    model = data.get('model', 'claude')

    # 提交异步任务
    task = extract_assets_async.apply_async(
        args=[episode_id, model],
        task_id=f'extract_{episode_id}_{int(time.time())}'
    )

    return success_response({
        'task_id': task.id,
        'episode_id': episode_id,
        'status': 'PENDING',
        'progress_url': f'/api/tasks/{task.id}/progress'
    }, '任务已提交')

@app.route('/api/tasks/<task_id>/progress', methods=['GET'])
def get_task_progress(task_id):
    """获取任务进度"""
    from cache import cache
    from celery.result import AsyncResult

    # 从Redis获取进度
    progress = cache.get(f'task_progress:{task_id}')

    # 获取Celery任务状态
    task = AsyncResult(task_id)

    return success_response({
        'task_id': task_id,
        'state': task.state,
        'progress': progress.get('progress', 0) if progress else 0,
        'message': progress.get('message', '') if progress else '',
        'result': task.result if task.ready() else None
    })
```



### 4.2 前端轮询实现

**React Hook实现：**
\/api/tasks/\/progress\

