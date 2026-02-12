# 异步任务处理架构

## 1. 为什么需要异步任务?

### 1.1 业务场景分析

**同步处理的问题:**
- AI资产提取可能需要30秒-3分钟
- HTTP请求超时(通常30-60秒)
- 阻塞用户界面
- 无法批量处理

**异步处理的优势:**
- 立即返回任务ID
- 后台处理，不阻塞
- 支持进度追踪
- 失败自动重试
- 可扩展(增加Worker)

---

## 2. Celery + Redis 架构设计

### 2.1 整体架构

```
┌─────────────┐
│   Flask     │  1. 接收请求
│   API       │  2. 创建任务
└──────┬──────┘  3. 返回task_id
       │
       ▼
┌─────────────┐
│   Redis     │  任务队列 + 结果存储
│   Broker    │  (消息中间件)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Celery    │  4. 执行任务
│   Worker    │  5. 更新进度
└──────┬──────┘  6. 存储结果
       │
       ▼
┌─────────────┐
│ PostgreSQL  │  持久化存储
└─────────────┘
```

### 2.2 Celery 配置

**celery_config.py:**

```python
from celery import Celery
from kombu import Queue, Exchange
import os

# Celery实例
celery_app = Celery('ai_script_analyzer')

# Redis配置
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery配置
celery_app.conf.update(
    # Broker配置
    broker_url=REDIS_URL,
    broker_connection_retry_on_startup=True,

    # 结果后端
    result_backend=REDIS_URL,
    result_expires=3600,  # 结果保留1小时

    # 任务序列化
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # 时区
    timezone='UTC',
    enable_utc=True,

    # 任务路由
    task_routes={
        'tasks.ai.*': {'queue': 'ai_tasks'},
        'tasks.asset.*': {'queue': 'asset_tasks'},
        'tasks.cleanup.*': {'queue': 'cleanup_tasks'},
    },

    # 队列定义
    task_queues=(
        Queue('ai_tasks', Exchange('ai_tasks'), routing_key='ai_tasks',
              queue_arguments={'x-max-priority': 10}),  # 支持优先级
        Queue('asset_tasks', Exchange('asset_tasks'), routing_key='asset_tasks'),
        Queue('cleanup_tasks', Exchange('cleanup_tasks'), routing_key='cleanup_tasks'),
    ),

    # Worker配置
    worker_prefetch_multiplier=1,  # 每次只取1个任务(长任务场景)
    worker_max_tasks_per_child=100,  # 每个worker处理100个任务后重启(防止内存泄漏)

    # 任务超时
    task_soft_time_limit=300,  # 软超时5分钟(抛出异常)
    task_time_limit=360,       # 硬超时6分钟(强制终止)

    # 任务重试
    task_acks_late=True,       # 任务完成后才确认(失败可重新入队)
    task_reject_on_worker_lost=True,

    # 监控
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# 自动发现任务
celery_app.autodiscover_tasks(['tasks'])
```

---

## 3. 任务定义

### 3.1 AI资产提取任务

**tasks/ai_tasks.py:**

```python
from celery import Task
from celery.utils.log import get_task_logger
from typing import Dict, Any
import time

from celery_config import celery_app
from services.ai_service import get_ai_service, AIModel
from database.models import Episode, Asset, AssetExtractionRecord
from database import db

logger = get_task_logger(__name__)

class CallbackTask(Task):
    """支持进度回调的任务基类"""

    def update_progress(self, current: int, total: int, message: str = ""):
        """更新任务进度"""
        self.update_state(
            state='PROGRESS',
            meta={
                'current': current,
                'total': total,
                'percent': int((current / total) * 100),
                'message': message
            }
        )

@celery_app.task(
    bind=True,
    base=CallbackTask,
    name='tasks.ai.extract_assets',
    max_retries=3,
    default_retry_delay=60,  # 重试延迟60秒
    autoretry_for=(Exception,),  # 自动重试的异常类型
    retry_backoff=True,  # 指数退避
    retry_jitter=True    # 添加随机抖动
)
def extract_assets_task(
    self,
    episode_id: int,
    model: str = 'claude',
    user_id: int = None
) -> Dict[str, Any]:
    """
    异步提取资产任务

    Args:
        episode_id: 剧集ID
        model: AI模型
        user_id: 用户ID

    Returns:
        提取结果
    """
    logger.info(f"开始提取资产: episode_id={episode_id}, model={model}")

    try:
        # 1. 更新进度: 加载剧集
        self.update_progress(1, 5, "加载剧集数据...")

        episode = db.session.query(Episode).get(episode_id)
        if not episode:
            raise ValueError(f"剧集不存在: {episode_id}")

        # 检查状态
        if episode.upload_status == 'COMPLETED':
            raise ValueError("该剧集已提取过资产")

        # 更新状态为处理中
        episode.upload_status = 'ANALYZING'
        db.session.commit()

        # 2. 更新进度: 调用AI
        self.update_progress(2, 5, f"调用{model}提取资产...")

        ai_service = get_ai_service(AIModel(model))
        extraction_result = ai_service.extract_assets(
            episode.script_content,
            episode.episode_number
        )

        # 3. 更新进度: 保存资产
        self.update_progress(3, 5, "保存提取的资产...")

        inserted_assets = {
            'characters': [],
            'props': [],
            'scenes': []
        }

        # 插入角色
        for idx, char in enumerate(extraction_result.get('characters', [])):
            asset = Asset(
                project_id=episode.project_id,
                asset_type='CHARACTER',
                name=char['name'],
                description=char.get('description', ''),
                gender=char.get('gender'),
                age=char.get('age'),
                voice=char.get('voice'),
                role=char.get('role'),
                first_appeared_episode_id=episode_id
            )
            db.session.add(asset)
            db.session.flush()

            # 记录提取记录
            record = AssetExtractionRecord(
                episode_id=episode_id,
                asset_id=asset.id,
                extracted_name=char['name'],
                extracted_description=char.get('description', ''),
                extracted_type='CHARACTER'
            )
            db.session.add(record)

            inserted_assets['characters'].append({
                'id': asset.id,
                'name': char['name']
            })

        # 插入道具和场景(类似逻辑)
        # ... (省略)

        # 4. 更新进度: 去重检测
        self.update_progress(4, 5, "执行去重检测...")

        # 触发去重任务(异步)
        deduplicate_assets_task.delay(episode.project_id)

        # 5. 完成
        self.update_progress(5, 5, "提取完成!")

        episode.upload_status = 'COMPLETED'
        db.session.commit()

        logger.info(f"资产提取完成: episode_id={episode_id}")

        return {
            'episode_id': episode_id,
            'extracted_assets': inserted_assets,
            'total': {
                'characters': len(inserted_assets['characters']),
                'props': len(inserted_assets['props']),
                'scenes': len(inserted_assets['scenes'])
            }
        }

    except Exception as e:
        logger.error(f"资产提取失败: {str(e)}", exc_info=True)

        # 更新状态为失败
        episode = db.session.query(Episode).get(episode_id)
        if episode:
            episode.upload_status = 'FAILED'
            db.session.commit()

        # 重新抛出异常(触发重试)
        raise
```

### 3.2 批量处理任务

**tasks/batch_tasks.py:**

```python
from celery import group, chord
from celery_config import celery_app
from tasks.ai_tasks import extract_assets_task

@celery_app.task(name='tasks.batch.extract_multiple_episodes')
def extract_multiple_episodes(episode_ids: list, model: str = 'claude'):
    """
    批量提取多个剧集的资产

    使用Celery的group并行执行
    """
    # 创建任务组(并行执行)
    job = group(
        extract_assets_task.s(episode_id, model)
        for episode_id in episode_ids
    )

    result = job.apply_async()
    return {
        'group_id': result.id,
        'total_tasks': len(episode_ids)
    }

@celery_app.task(name='tasks.batch.extract_with_callback')
def extract_with_callback(episode_ids: list, model: str = 'claude'):
    """
    批量提取并在全部完成后执行回调

    使用Celery的chord
    """
    # 创建chord(所有任务完成后执行回调)
    callback = finalize_batch_extraction.s()

    job = chord(
        extract_assets_task.s(episode_id, model)
        for episode_id in episode_ids
    )(callback)

    return {'chord_id': job.id}

@celery_app.task(name='tasks.batch.finalize')
def finalize_batch_extraction(results: list):
    """批量提取完成后的回调"""
    logger.info(f"批量提取完成，共{len(results)}个任务")

    # 发送通知、生成报告等
    # ...

    return {'status': 'completed', 'total': len(results)}
```

---

## 4. 任务进度追踪

### 4.1 进度查询API

**routes/task_routes.py:**

```python
from flask import Blueprint, jsonify
from celery.result import AsyncResult
from celery_config import celery_app

task_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@task_bp.route('/<task_id>/status', methods=['GET'])
def get_task_status(task_id: str):
    """
    查询任务状态

    返回格式:
    {
        "task_id": "xxx",
        "state": "PROGRESS",
        "current": 3,
        "total": 5,
        "percent": 60,
        "message": "保存提取的资产...",
        "result": null
    }
    """
    task = AsyncResult(task_id, app=celery_app)

    response = {
        'task_id': task_id,
        'state': task.state,
    }

    if task.state == 'PENDING':
        response.update({
            'status': 'pending',
            'message': '任务等待中...'
        })

    elif task.state == 'PROGRESS':
        response.update({
            'status': 'processing',
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'percent': task.info.get('percent', 0),
            'message': task.info.get('message', '')
        })

    elif task.state == 'SUCCESS':
        response.update({
            'status': 'completed',
            'result': task.result,
            'message': '任务完成'
        })

    elif task.state == 'FAILURE':
        response.update({
            'status': 'failed',
            'error': str(task.info),
            'message': '任务失败'
        })

    elif task.state == 'RETRY':
        response.update({
            'status': 'retrying',
            'message': '任务重试中...',
            'retry_count': task.info.get('retry_count', 0)
        })

    return jsonify(response)

@task_bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id: str):
    """取消任务"""
    task = AsyncResult(task_id, app=celery_app)
    task.revoke(terminate=True)  # 强制终止

    return jsonify({
        'task_id': task_id,
        'status': 'cancelled'
    })
```

### 4.2 前端轮询示例

```javascript
// 前端轮询任务状态
async function pollTaskStatus(taskId) {
    const maxAttempts = 120; // 最多轮询2分钟
    let attempts = 0;

    while (attempts < maxAttempts) {
        const response = await fetch(`/api/tasks/${taskId}/status`);
        const data = await response.json();

        // 更新进度条
        if (data.state === 'PROGRESS') {
            updateProgressBar(data.percent, data.message);
        }

        // 任务完成
        if (data.state === 'SUCCESS') {
            console.log('任务完成:', data.result);
            return data.result;
        }

        // 任务失败
        if (data.state === 'FAILURE') {
            throw new Error(data.error);
        }

        // 等待1秒后继续轮询
        await new Promise(resolve => setTimeout(resolve, 1000));
        attempts++;
    }

    throw new Error('任务超时');
}
```

---

## 5. 任务优先级管理

### 5.1 优先级队列

```python
# 定义优先级
class TaskPriority:
    CRITICAL = 10  # 付费用户
    HIGH = 7       # 重要任务
    NORMAL = 5     # 普通任务
    LOW = 3        # 批量任务

# 发送任务时指定优先级
extract_assets_task.apply_async(
    args=[episode_id, model],
    priority=TaskPriority.HIGH
)
```

### 5.2 基于用户订阅的优先级

```python
def get_task_priority(user_id: int) -> int:
    """根据用户订阅等级返回任务优先级"""
    user = User.query.get(user_id)

    priority_map = {
        'FREE': TaskPriority.LOW,
        'PRO': TaskPriority.NORMAL,
        'ENTERPRISE': TaskPriority.HIGH
    }

    return priority_map.get(user.subscription_tier, TaskPriority.NORMAL)
```

---

## 6. 任务失败处理

### 6.1 死信队列

```python
# Celery配置
celery_app.conf.update(
    # 任务失败后发送到死信队列
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)

# 死信队列处理
@celery_app.task(name='tasks.handle_failed_task')
def handle_failed_task(task_id: str, exception: str):
    """处理失败的任务"""
    logger.error(f"任务失败: {task_id}, 错误: {exception}")

    # 记录到数据库
    failed_task = FailedTask(
        task_id=task_id,
        exception=exception,
        created_at=datetime.utcnow()
    )
    db.session.add(failed_task)
    db.session.commit()

    # 发送告警通知
    send_alert_notification(task_id, exception)
```

### 6.2 任务重试策略

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(RateLimitError, ProviderUnavailableError),
    retry_backoff=True,
    retry_backoff_max=600,  # 最大退避时间10分钟
    retry_jitter=True
)
def resilient_ai_task(self, episode_id: int):
    """具有弹性的AI任务"""
    try:
        # 执行任务
        result = process_episode(episode_id)
        return result

    except QuotaExceededError as e:
        # 配额超限，不重试
        logger.error(f"配额超限: {e}")
        raise

    except RateLimitError as e:
        # 速率限制，延迟重试
        logger.warning(f"速率限制，将在{self.default_retry_delay}秒后重试")
        raise self.retry(exc=e, countdown=60)

    except ProviderUnavailableError as e:
        # 提供商不可用，尝试降级
        logger.warning(f"提供商不可用，尝试降级: {e}")
        return fallback_process(episode_id)
```

---

## 7. Worker 部署配置

### 7.1 启动Worker

```bash
# 启动AI任务Worker(高优先级队列)
celery -A celery_config worker \
    --queue=ai_tasks \
    --concurrency=4 \
    --loglevel=info \
    --max-tasks-per-child=50 \
    --time-limit=360 \
    --soft-time-limit=300

# 启动资产处理Worker(普通队列)
celery -A celery_config worker \
    --queue=asset_tasks \
    --concurrency=8 \
    --loglevel=info

# 启动清理任务Worker(低优先级队列)
celery -A celery_config worker \
    --queue=cleanup_tasks \
    --concurrency=2 \
    --loglevel=warning
```

### 7.2 Supervisor配置

**supervisor.conf:**

```ini
[program:celery_ai_worker]
command=/path/to/venv/bin/celery -A celery_config worker --queue=ai_tasks --concurrency=4
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/ai_worker.log

[program:celery_beat]
command=/path/to/venv/bin/celery -A celery_config beat --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

---

## 8. 定时任务

### 8.1 Celery Beat配置

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # 每天凌晨2点清理过期任务结果
    'cleanup-expired-results': {
        'task': 'tasks.cleanup.cleanup_expired_results',
        'schedule': crontab(hour=2, minute=0),
    },

    # 每小时重置配额(如果是按小时计费)
    'reset-hourly-quota': {
        'task': 'tasks.quota.reset_hourly_quota',
        'schedule': crontab(minute=0),
    },

    # 每月1号重置月度配额
    'reset-monthly-quota': {
        'task': 'tasks.quota.reset_monthly_quota',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),
    },

    # 每5分钟检查任务健康状态
    'health-check': {
        'task': 'tasks.monitoring.health_check',
        'schedule': 300.0,  # 300秒
    },
}
```

### 8.2 定时任务示例

```python
@celery_app.task(name='tasks.cleanup.cleanup_expired_results')
def cleanup_expired_results():
    """清理过期的任务结果"""
    from celery.result import AsyncResult
    from datetime import datetime, timedelta

    # 清理24小时前的结果
    cutoff = datetime.utcnow() - timedelta(hours=24)

    # 从Redis清理
    # (Celery会自动清理，这里可以添加额外的清理逻辑)

    logger.info("清理过期任务结果完成")
```

---

下一部分将详细分析：认证授权系统(JWT双Token机制)、API设计规范、限流策略等内容。是否继续?

