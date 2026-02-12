# 日志监控架构

## 1. 日志系统设计

### 1.1 日志分层策略

```
┌─────────────────────────────────────────────────────────┐
│                   Application Logs                       │
│  (业务日志、错误日志、审计日志)                            │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                   Access Logs                            │
│  (API访问日志、请求响应日志)                               │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                   System Logs                            │
│  (系统错误、性能指标、资源使用)                             │
└─────────────────────────────────────────────────────────┘
```

### 1.2 结构化日志配置

```python
import logging
import json
from datetime import datetime
from flask import request, g
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义JSON日志格式化器"""

    def add_fields(self, log_record, record, message_dict):
        """添加自定义字段"""
        super().add_fields(log_record, record, message_dict)

        # 添加时间戳
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # 添加日志级别
        log_record['level'] = record.levelname

        # 添加请求上下文
        if request:
            log_record['request'] = {
                'method': request.method,
                'path': request.path,
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')
            }

        # 添加用户信息
        if hasattr(g, 'current_user_id'):
            log_record['user_id'] = g.current_user_id

        # 添加追踪ID
        if hasattr(g, 'request_id'):
            log_record['request_id'] = g.request_id

def setup_logging(app):
    """配置日志系统"""

    # 创建日志处理器
    handler = logging.StreamHandler()
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    handler.setFormatter(formatter)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # 配置Flask日志
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    # 配置SQLAlchemy日志(生产环境关闭)
    if not app.debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
```

### 1.3 请求追踪ID

```python
import uuid
from flask import g, request

@app.before_request
def add_request_id():
    """为每个请求生成唯一ID"""
    # 优先使用客户端传递的追踪ID
    request_id = request.headers.get('X-Request-ID')

    if not request_id:
        request_id = str(uuid.uuid4())

    g.request_id = request_id

@app.after_request
def add_request_id_header(response):
    """将追踪ID添加到响应头"""
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
    return response
```

---

## 2. 访问日志中间件

### 2.1 请求日志记录

```python
import time
from flask import request, g
import logging

logger = logging.getLogger(__name__)

@app.before_request
def log_request_start():
    """记录请求开始"""
    g.request_start_time = time.time()

@app.after_request
def log_request_end(response):
    """记录请求结束"""
    if not hasattr(g, 'request_start_time'):
        return response

    # 计算请求耗时
    duration_ms = int((time.time() - g.request_start_time) * 1000)

    # 记录访问日志
    logger.info('API访问', extra={
        'event': 'api_access',
        'method': request.method,
        'path': request.path,
        'status_code': response.status_code,
        'duration_ms': duration_ms,
        'user_id': getattr(g, 'current_user_id', None),
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'request_id': getattr(g, 'request_id', None)
    })

    # 添加性能指标到响应头
    response.headers['X-Response-Time'] = f"{duration_ms}ms"

    return response
```

### 2.2 慢查询日志

```python
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """记录SQL执行开始时间"""
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """记录慢查询"""
    total_time = time.time() - conn.info['query_start_time'].pop()
    duration_ms = int(total_time * 1000)

    # 慢查询阈值: 100ms
    if duration_ms > 100:
        logger.warning('慢查询检测', extra={
            'event': 'slow_query',
            'duration_ms': duration_ms,
            'statement': statement,
            'parameters': parameters
        })
```

---

## 3. 错误日志与告警

### 3.1 错误捕获

```python
from flask import Flask
import traceback

@app.errorhandler(Exception)
def handle_exception(error):
    """全局异常处理"""

    # 记录详细错误信息
    logger.error('未处理的异常', extra={
        'event': 'unhandled_exception',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc(),
        'request_id': getattr(g, 'request_id', None),
        'user_id': getattr(g, 'current_user_id', None),
        'path': request.path,
        'method': request.method
    })

    # 发送告警(异步)
    if not isinstance(error, (ValidationError, NotFoundError)):
        from tasks.notification_tasks import send_error_alert
        send_error_alert.delay(
            error_type=type(error).__name__,
            error_message=str(error),
            request_id=getattr(g, 'request_id', None)
        )

    return error_response(error)
```

### 3.2 错误聚合

```python
class ErrorAggregator:
    """错误聚合器"""

    def __init__(self, redis_client):
        self.redis = redis_client

    def record_error(self, error_type: str, error_message: str):
        """记录错误"""
        key = f"errors:{error_type}"
        self.redis.hincrby(key, error_message, 1)
        self.redis.expire(key, 3600)  # 1小时

    def get_top_errors(self, error_type: str, limit: int = 10) -> list:
        """获取最频繁的错误"""
        key = f"errors:{error_type}"
        errors = self.redis.hgetall(key)

        sorted_errors = sorted(
            errors.items(),
            key=lambda x: int(x[1]),
            reverse=True
        )

        return sorted_errors[:limit]
```

---

## 4. 性能监控

### 4.1 性能指标收集

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# 定义指标
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

active_users = Gauge(
    'active_users_total',
    'Number of active users'
)

ai_call_count = Counter(
    'ai_calls_total',
    'Total AI API calls',
    ['provider', 'model', 'status']
)

@app.before_request
def start_timer():
    """开始计时"""
    g.start_time = time.time()

@app.after_request
def record_metrics(response):
    """记录性能指标"""
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time

        # 记录请求计数
        request_count.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()

        # 记录请求耗时
        request_duration.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown'
        ).observe(duration)

    return response
```

### 4.2 Prometheus端点

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.route('/metrics')
def metrics():
    """Prometheus指标端点"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
```

---

## 5. 分布式追踪

### 5.1 OpenTelemetry集成

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(app):
    """配置分布式追踪"""

    # 创建追踪提供者
    trace.set_tracer_provider(TracerProvider())

    # 配置Jaeger导出器
    jaeger_exporter = JaegerExporter(
        agent_host_name='localhost',
        agent_port=6831,
    )

    # 添加批处理导出器
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

    # 自动追踪Flask请求
    FlaskInstrumentor().instrument_app(app)

    # 自动追踪SQLAlchemy查询
    SQLAlchemyInstrumentor().instrument(engine=db.engine)
```

### 5.2 自定义追踪

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def extract_assets_with_tracing(episode_id: int):
    """带追踪的资产提取"""

    with tracer.start_as_current_span("extract_assets") as span:
        # 添加属性
        span.set_attribute("episode_id", episode_id)

        # 子span: 加载剧集
        with tracer.start_as_current_span("load_episode"):
            episode = Episode.query.get(episode_id)
            span.set_attribute("script_length", len(episode.script_content))

        # 子span: AI调用
        with tracer.start_as_current_span("ai_call") as ai_span:
            ai_span.set_attribute("provider", "claude")
            result = ai_service.extract_assets(episode.script_content)

        # 子span: 保存资产
        with tracer.start_as_current_span("save_assets"):
            save_assets_to_db(result)

        return result
```

---

## 6. 日志聚合方案

### 6.1 ELK Stack (推荐)

**架构:**
```
Flask App → Filebeat → Logstash → Elasticsearch → Kibana
```

**Filebeat配置 (filebeat.yml):**
```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/app/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.logstash:
  hosts: ["logstash:5044"]

processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
```

**Logstash配置 (logstash.conf):**
```ruby
input {
  beats {
    port => 5044
  }
}

filter {
  # 解析JSON日志
  json {
    source => "message"
  }

  # 添加地理位置信息
  geoip {
    source => "[request][ip]"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "app-logs-%{+YYYY.MM.dd}"
  }
}
```

### 6.2 简化方案: Loki

**优势:**
- 轻量级
- 与Grafana无缝集成
- 成本低

**Promtail配置:**
```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: app
    static_configs:
      - targets:
          - localhost
        labels:
          job: app
          __path__: /var/log/app/*.log
```

---

## 7. 告警规则

### 7.1 Prometheus告警规则

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      # 错误率告警
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API错误率过高"
          description: "5分钟内错误率超过5%"

      # 响应时间告警
      - alert: SlowResponse
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API响应缓慢"
          description: "95分位响应时间超过1秒"

      # AI调用失败告警
      - alert: AICallFailure
        expr: |
          rate(ai_calls_total{status="failed"}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "AI调用失败率过高"
```

### 7.2 告警通知

```python
import requests

def send_alert_notification(title: str, message: str, severity: str = 'warning'):
    """发送告警通知"""

    # 发送到Slack
    slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    if slack_webhook:
        requests.post(slack_webhook, json={
            'text': f"[{severity.upper()}] {title}",
            'attachments': [{
                'text': message,
                'color': 'danger' if severity == 'critical' else 'warning'
            }]
        })

    # 发送邮件
    from tasks.email_tasks import send_alert_email
    send_alert_email.delay(title, message, severity)
```

---

下一部分将输出：部署架构方案。是否继续?
