# API设计规范与最佳实践

## 1. RESTful API设计原则

### 1.1 资源命名规范

**基本规则:**
- 使用名词复数形式
- 使用小写字母和连字符
- 避免动词(动作通过HTTP方法表达)

**正确示例:**
```
GET    /api/projects              # 获取项目列表
GET    /api/projects/123          # 获取单个项目
POST   /api/projects              # 创建项目
PUT    /api/projects/123          # 更新项目
DELETE /api/projects/123          # 删除项目

GET    /api/projects/123/episodes # 获取项目的剧集
POST   /api/episodes/456/extract-assets  # 提取资产(特殊操作)
```

**错误示例:**
```
❌ GET  /api/getProjects
❌ POST /api/createProject
❌ GET  /api/project/123          # 应该用复数
❌ GET  /api/projects_list        # 避免下划线
```

### 1.2 HTTP方法语义

| 方法 | 语义 | 幂等性 | 安全性 | 示例 |
|------|------|--------|--------|------|
| GET | 获取资源 | ✅ | ✅ | 查询项目列表 |
| POST | 创建资源 | ❌ | ❌ | 创建新项目 |
| PUT | 完整更新 | ✅ | ❌ | 更新项目全部字段 |
| PATCH | 部分更新 | ❌ | ❌ | 更新项目部分字段 |
| DELETE | 删除资源 | ✅ | ❌ | 删除项目 |

### 1.3 HTTP状态码规范

**成功响应 (2xx):**
```python
200 OK              # 请求成功(GET/PUT/PATCH)
201 Created         # 资源创建成功(POST)
204 No Content      # 请求成功但无返回内容(DELETE)
```

**客户端错误 (4xx):**
```python
400 Bad Request     # 请求参数错误
401 Unauthorized    # 未认证
403 Forbidden       # 无权限
404 Not Found       # 资源不存在
409 Conflict        # 资源冲突(如重复创建)
422 Unprocessable Entity  # 验证失败
429 Too Many Requests     # 请求过多
```

**服务器错误 (5xx):**
```python
500 Internal Server Error  # 服务器内部错误
502 Bad Gateway           # 网关错误
503 Service Unavailable   # 服务不可用
504 Gateway Timeout       # 网关超时
```

---

## 2. 统一响应格式

### 2.1 成功响应

```python
from flask import jsonify
from datetime import datetime
from typing import Any, Optional

def success_response(
    data: Any = None,
    message: str = "操作成功",
    meta: Optional[dict] = None
) -> tuple:
    """
    统一成功响应格式

    Args:
        data: 响应数据
        message: 提示信息
        meta: 元数据(分页、统计等)

    Returns:
        (response, status_code)
    """
    response = {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if meta:
        response["meta"] = meta

    return jsonify(response), 200
```

**示例响应:**
```json
{
  "success": true,
  "message": "获取项目列表成功",
  "data": {
    "projects": [
      {
        "id": 1,
        "name": "项目A",
        "status": "ASSET_BUILDING"
      }
    ]
  },
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2.2 错误响应

```python
class APIError(Exception):
    """API错误基类"""
    status_code = 400
    error_code = "BAD_REQUEST"

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}

class ValidationError(APIError):
    status_code = 422
    error_code = "VALIDATION_ERROR"

class NotFoundError(APIError):
    status_code = 404
    error_code = "NOT_FOUND"

class UnauthorizedError(APIError):
    status_code = 401
    error_code = "UNAUTHORIZED"

def error_response(
    error: APIError,
    include_traceback: bool = False
) -> tuple:
    """
    统一错误响应格式

    Args:
        error: API错误对象
        include_traceback: 是否包含堆栈信息(仅开发环境)

    Returns:
        (response, status_code)
    """
    response = {
        "success": False,
        "error": {
            "code": error.error_code,
            "message": error.message,
            "details": error.details
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if include_traceback and current_app.debug:
        import traceback
        response["error"]["traceback"] = traceback.format_exc()

    return jsonify(response), error.status_code
```

**示例错误响应:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "email": ["邮箱格式无效"],
      "password": ["密码长度至少8位"]
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2.3 全局错误处理器

```python
from flask import Flask
from werkzeug.exceptions import HTTPException

def register_error_handlers(app: Flask):
    """注册全局错误处理器"""

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """处理自定义API错误"""
        return error_response(error)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """处理HTTP异常"""
        api_error = APIError(
            message=error.description or str(error),
        )
        api_error.status_code = error.code
        api_error.error_code = error.name.upper().replace(' ', '_')
        return error_response(api_error)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        """处理未预期的错误"""
        logger.error(f"未处理的异常: {str(error)}", exc_info=True)

        api_error = APIError(
            message="服务器内部错误，请稍后重试"
        )
        api_error.status_code = 500
        api_error.error_code = "INTERNAL_SERVER_ERROR"

        return error_response(api_error, include_traceback=app.debug)
```

---

## 3. 请求验证

### 3.1 使用Pydantic进行验证

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional

class CreateProjectRequest(BaseModel):
    """创建项目请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(None, max_length=500, description="项目描述")

    @validator('name')
    def validate_name(cls, v):
        """验证项目名称"""
        if not v.strip():
            raise ValueError("项目名称不能为空")
        return v.strip()

class UpdateProjectRequest(BaseModel):
    """更新项目请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, regex="^(ASSET_BUILDING|ASSET_LOCKED|STORYBOARD_GENERATION|COMPLETED)$")

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    order: str = Field("desc", regex="^(asc|desc)$", description="排序方向")
```

### 3.2 验证装饰器

```python
from functools import wraps
from flask import request
from pydantic import ValidationError as PydanticValidationError

def validate_request(schema: BaseModel):
    """
    请求验证装饰器

    使用方式:
    @app.route('/api/projects', methods=['POST'])
    @validate_request(CreateProjectRequest)
    def create_project():
        data = g.validated_data
        # ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # 验证JSON请求体
                if request.is_json:
                    data = request.get_json()
                    validated = schema(**data)
                    g.validated_data = validated.dict()
                else:
                    raise ValidationError("请求必须是JSON格式")

            except PydanticValidationError as e:
                # 格式化验证错误
                errors = {}
                for error in e.errors():
                    field = error['loc'][0]
                    errors[field] = [error['msg']]

                raise ValidationError(
                    message="请求参数验证失败",
                    details=errors
                )

            return f(*args, **kwargs)

        return decorated_function
    return decorator
```

---

## 4. 分页设计

### 4.1 基于偏移量的分页

```python
from sqlalchemy import func

def paginate_query(
    query,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100
):
    """
    分页查询

    Args:
        query: SQLAlchemy查询对象
        page: 页码(从1开始)
        page_size: 每页数量
        max_page_size: 最大每页数量

    Returns:
        {
            'items': [...],
            'total': 100,
            'page': 1,
            'page_size': 20,
            'total_pages': 5,
            'has_next': True,
            'has_prev': False
        }
    """
    # 限制page_size
    page_size = min(page_size, max_page_size)

    # 计算总数
    total = query.count()

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    # 查询当前页数据
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1
    }
```

### 4.2 基于游标的分页(推荐)

```python
def cursor_paginate(
    query,
    cursor: Optional[str] = None,
    limit: int = 20,
    order_by='id'
):
    """
    游标分页(适合大数据集)

    Args:
        query: SQLAlchemy查询对象
        cursor: 游标(上一页最后一条记录的ID)
        limit: 每页数量
        order_by: 排序字段

    Returns:
        {
            'items': [...],
            'next_cursor': 'abc123',
            'has_more': True
        }
    """
    # 如果有游标，从游标位置开始查询
    if cursor:
        query = query.filter(getattr(query.column_descriptions[0]['type'], order_by) > cursor)

    # 多查询一条，判断是否还有下一页
    items = query.order_by(order_by).limit(limit + 1).all()

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    # 生成下一页游标
    next_cursor = None
    if has_more and items:
        next_cursor = str(getattr(items[-1], order_by))

    return {
        'items': items,
        'next_cursor': next_cursor,
        'has_more': has_more
    }
```

---

## 5. API版本管理

### 5.1 URL版本控制(推荐)

```python
# 方式1: 路径版本
@app.route('/api/v1/projects', methods=['GET'])
def get_projects_v1():
    """V1版本API"""
    pass

@app.route('/api/v2/projects', methods=['GET'])
def get_projects_v2():
    """V2版本API(新增字段)"""
    pass

# 方式2: 使用Blueprint
from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

@api_v1.route('/projects', methods=['GET'])
def get_projects():
    pass

app.register_blueprint(api_v1)
app.register_blueprint(api_v2)
```

### 5.2 Header版本控制

```python
def get_api_version():
    """从请求头获取API版本"""
    version = request.headers.get('X-API-Version', 'v1')
    return version

@app.route('/api/projects', methods=['GET'])
def get_projects():
    version = get_api_version()

    if version == 'v1':
        return get_projects_v1()
    elif version == 'v2':
        return get_projects_v2()
    else:
        raise ValidationError(f"不支持的API版本: {version}")
```

### 5.3 版本弃用策略

```python
from datetime import datetime, timedelta

DEPRECATED_VERSIONS = {
    'v1': {
        'deprecated_at': '2024-01-01',
        'sunset_at': '2024-06-01',
        'migration_guide': 'https://docs.example.com/migration/v1-to-v2'
    }
}

def check_version_deprecation(version: str):
    """检查版本是否已弃用"""
    if version in DEPRECATED_VERSIONS:
        info = DEPRECATED_VERSIONS[version]
        sunset_date = datetime.fromisoformat(info['sunset_at'])

        # 添加弃用警告头
        response.headers['X-API-Deprecated'] = 'true'
        response.headers['X-API-Sunset-Date'] = info['sunset_at']
        response.headers['X-API-Migration-Guide'] = info['migration_guide']

        # 如果已过期，返回410 Gone
        if datetime.utcnow() > sunset_date:
            raise APIError(
                message=f"API版本{version}已停止服务",
                details={'migration_guide': info['migration_guide']}
            )
```

---

## 6. 过滤、排序、搜索

### 6.1 查询参数设计

```python
@app.route('/api/projects', methods=['GET'])
@login_required
def get_projects():
    """
    获取项目列表

    查询参数:
    - status: 项目状态(ASSET_BUILDING/ASSET_LOCKED等)
    - search: 搜索关键词(项目名称)
    - sort_by: 排序字段(created_at/updated_at/name)
    - order: 排序方向(asc/desc)
    - page: 页码
    - page_size: 每页数量
    """
    # 基础查询
    query = Project.query.filter_by(user_id=g.current_user_id)

    # 过滤
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    # 搜索
    search = request.args.get('search')
    if search:
        query = query.filter(Project.name.ilike(f'%{search}%'))

    # 排序
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')

    if hasattr(Project, sort_by):
        order_column = getattr(Project, sort_by)
        if order == 'desc':
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

    # 分页
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    result = paginate_query(query, page, page_size)

    return success_response(
        data={
            'projects': [p.to_dict() for p in result['items']]
        },
        meta={
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'total_pages': result['total_pages']
        }
    )
```

---

下一部分将详细分析：限流策略、日志监控架构。是否继续?
