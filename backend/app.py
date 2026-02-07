"""
AI剧本批量拆解系统 - Flask后端
Version: 2.0
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from pathlib import Path

# 导入数据库初始化
from database.init_db import init_database, get_connection

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['STORAGE_PATH'] = 'storage/projects'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB最大上传

# 确保存储目录存在
Path(app.config['STORAGE_PATH']).mkdir(parents=True, exist_ok=True)

# 初始化数据库
default_db = os.path.join(app.config['STORAGE_PATH'], 'default.db')
init_database(default_db)


# ===================================
# 辅助函数
# ===================================

def get_db():
    """获取数据库连接"""
    return get_connection(default_db)


def success_response(data=None, message="操作成功"):
    """成功响应"""
    from datetime import datetime
    return jsonify({
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })


def error_response(message="操作失败", status_code=400):
    """错误响应"""
    from datetime import datetime
    return jsonify({
        "success": False,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }), status_code


# ===================================
# API路由
# ===================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return success_response({"status": "healthy"})


@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取项目列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, description, status,
                created_at, updated_at
            FROM projects
            ORDER BY updated_at DESC
        """)

        projects = []
        for row in cursor.fetchall():
            projects.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            })

        conn.close()
        return success_response({"projects": projects, "total": len(projects)})
    except Exception as e:
        return error_response(f"获取项目列表失败: {str(e)}", 500)


@app.route('/api/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')

        if not name:
            return error_response("项目名称不能为空", 400)

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO projects (name, description)
                VALUES (?, ?)
            """, (name, description))
            conn.commit()

            project_id = cursor.lastrowid

            cursor.execute("""
                SELECT id, name, description, status, created_at
                FROM projects WHERE id = ?
            """, (project_id,))

            row = cursor.fetchone()
            project = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "created_at": row[4]
            }

            conn.close()
            return success_response(project, "项目创建成功")
        except Exception as e:
            conn.rollback()
            conn.close()
            if "UNIQUE constraint failed" in str(e):
                return error_response("项目名称已存在", 400)
            raise e
    except Exception as e:
        return error_response(f"创建项目失败: {str(e)}", 500)


@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """获取项目详情"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 获取项目基本信息
        cursor.execute("""
            SELECT id, name, description, status, created_at, updated_at
            FROM projects WHERE id = ?
        """, (project_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return error_response("项目不存在", 404)

        project = {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "status": row[3],
            "created_at": row[4],
            "updated_at": row[5]
        }

        # 获取统计信息
        cursor.execute("""
            SELECT COUNT(*) FROM episodes WHERE project_id = ?
        """, (project_id,))
        project['episode_count'] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM assets
            WHERE project_id = ? AND is_deleted = 0
        """, (project_id,))
        project['asset_count'] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM storyboards s
            JOIN episodes e ON s.episode_id = e.id
            WHERE e.project_id = ?
        """, (project_id,))
        project['storyboard_count'] = cursor.fetchone()[0]

        conn.close()
        return success_response(project)
    except Exception as e:
        return error_response(f"获取项目详情失败: {str(e)}", 500)


@app.route('/api/projects/<int:project_id>/episodes', methods=['POST'])
def upload_episode(project_id):
    """上传剧集"""
    try:
        episode_number = request.form.get('episode_number', type=int)
        title = request.form.get('title', '')
        script_content = request.form.get('script_content', '')

        if not episode_number:
            return error_response("集数不能为空", 400)

        if not script_content:
            # 检查是否有文件上传
            if 'script_file' in request.files:
                file = request.files['script_file']
                script_content = file.read().decode('utf-8')
            else:
                return error_response("剧本内容不能为空", 400)

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO episodes (project_id, episode_number, title, script_content)
                VALUES (?, ?, ?, ?)
            """, (project_id, episode_number, title, script_content))
            conn.commit()

            episode_id = cursor.lastrowid
            conn.close()

            return success_response({
                "episode_id": episode_id,
                "episode_number": episode_number,
                "upload_status": "UPLOADED"
            }, "剧集上传成功")
        except Exception as e:
            conn.rollback()
            conn.close()
            if "UNIQUE constraint failed" in str(e):
                return error_response(f"第{episode_number}集已存在", 400)
            raise e
    except Exception as e:
        return error_response(f"上传剧集失败: {str(e)}", 500)


@app.route('/api/projects/<int:project_id>/assets', methods=['GET'])
def get_project_assets(project_id):
    """获取项目资产列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, asset_type, name, description,
                gender, age, voice, role,
                first_appeared_episode_id, created_at
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
        """, (project_id,))

        assets = []
        for row in cursor.fetchall():
            asset = {
                "id": row[0],
                "asset_type": row[1],
                "name": row[2],
                "description": row[3],
                "created_at": row[9]
            }

            # 角色专用字段
            if row[1] == 'CHARACTER':
                asset.update({
                    "gender": row[4],
                    "age": row[5],
                    "voice": row[6],
                    "role": row[7]
                })

            assets.append(asset)

        conn.close()
        return success_response({"assets": assets, "total": len(assets)})
    except Exception as e:
        return error_response(f"获取资产列表失败: {str(e)}", 500)


# ===================================
# 启动应用
# ===================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
