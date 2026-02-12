"""
AI剧本批量拆解系统 - Flask后端
Version: 2.0
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from pathlib import Path
from dotenv import load_dotenv

# 获取当前文件所在目录
BASE_DIR = Path(__file__).resolve().parent

# 加载环境变量 - 明确指定.env文件路径
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

# 调试：打印环境变量加载状态
print(f"[DEBUG] .env文件路径: {env_path}")
print(f"[DEBUG] .env文件是否存在: {env_path.exists()}")
print(f"[DEBUG] DEEPSEEK_API_KEY已加载: {'是' if os.getenv('DEEPSEEK_API_KEY') else '否'}")

# 导入数据库初始化
from database.init_db import init_database, get_connection

# 导入AI服务
from services.ai_service import get_ai_service, AIModel

# 导入去重服务
from services.deduplication_service import get_deduplication_service

# 导入认证路由
from routes.auth import auth_bp, token_required

# 导入风格模板路由
from routes.style_templates import style_templates_bp

# 导入项目管理路由
from routes.projects import projects_bp

# 导入剧集管理路由
from routes.episodes import episodes_bp

# 导入分镜管理路由
from routes.storyboards import storyboards_bp

# 导入资产管理路由
from routes.assets import assets_bp

# 导入模型配置路由
from routes.models import models_bp

# 导入管理员路由
from routes.admin import admin_bp

# 创建Flask应用
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)  # 允许跨域请求

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(style_templates_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(episodes_bp)
app.register_blueprint(storyboards_bp)
app.register_blueprint(assets_bp)
app.register_blueprint(models_bp)
app.register_blueprint(admin_bp)

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


@app.route('/admin.html')
def admin_page():
    """管理后台页面"""
    return app.send_static_file('admin.html')


@app.route('/admin-login.html')
def admin_login_page():
    """管理员登录页面"""
    return app.send_static_file('admin-login.html')


@app.route('/api/config/check', methods=['GET'])
def check_config():
    """检查API密钥配置状态"""
    # 调试：打印实际的环境变量值
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    print(f"[DEBUG] check_config - DEEPSEEK_API_KEY: {deepseek_key}")
    print(f"[DEBUG] check_config - DEEPSEEK_API_KEY type: {type(deepseek_key)}")
    print(f"[DEBUG] check_config - DEEPSEEK_API_KEY bool: {bool(deepseek_key)}")

    config_status = {
        "claude_api_key": "已配置" if os.getenv('CLAUDE_API_KEY') else "未配置",
        "deepseek_api_key": "已配置" if os.getenv('DEEPSEEK_API_KEY') else "未配置",
        "gemini_api_key": "已配置" if os.getenv('GEMINI_API_KEY') else "未配置",
        "openai_api_key": "已配置" if os.getenv('OPENAI_API_KEY') else "未配置",
    }
    return success_response(config_status)


@app.route('/api/projects', methods=['GET'])
@token_required
def get_projects(current_user_id):
    """获取项目列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, description, status,
                created_at, updated_at
            FROM projects
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (current_user_id,))

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
@token_required
def create_project(current_user_id):
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
                INSERT INTO projects (user_id, name, description)
                VALUES (?, ?, ?)
            """, (current_user_id, name, description))
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
@token_required
def get_project(current_user_id, project_id):
    """获取项目详情"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 获取项目基本信息（验证用户权限）
        cursor.execute("""
            SELECT id, name, description, status, created_at, updated_at
            FROM projects WHERE id = ? AND user_id = ?
        """, (project_id, current_user_id))

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
@token_required
def upload_episode(current_user_id, project_id):
    """上传剧集"""
    try:
        # 验证项目所有权
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, current_user_id))
        if not cursor.fetchone():
            conn.close()
            return error_response("项目不存在或无权访问", 404)
        conn.close()
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
@token_required
def get_project_assets(current_user_id, project_id):
    """获取项目资产列表"""
    try:
        # 验证项目所有权
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, current_user_id))
        if not cursor.fetchone():
            conn.close()
            return error_response("项目不存在或无权访问", 404)

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


@app.route('/api/episodes/<int:episode_id>/extract-assets', methods=['POST'])
@token_required
def extract_assets_from_episode(current_user_id, episode_id):
    """从剧集中提取资产（调用AI）"""
    try:
        # 验证剧集所有权
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id FROM episodes e
            JOIN projects p ON e.project_id = p.id
            WHERE e.id = ? AND p.user_id = ?
        """, (episode_id, current_user_id))
        if not cursor.fetchone():
            conn.close()
            return error_response("剧集不存在或无权访问", 404)
        conn.close()

        data = request.get_json() or {}
        model_name = data.get('model', 'claude')

        # 验证模型
        try:
            model = AIModel(model_name.lower())
        except ValueError:
            return error_response(f"不支持的模型: {model_name}", 400)

        conn = get_db()
        cursor = conn.cursor()

        # 获取剧集信息
        cursor.execute("""
            SELECT e.id, e.project_id, e.episode_number, e.script_content, e.upload_status
            FROM episodes e
            WHERE e.id = ?
        """, (episode_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return error_response("剧集不存在", 404)

        episode_id_db, project_id, episode_number, script_content, upload_status = row

        # 检查是否已提取
        if upload_status == 'COMPLETED':
            conn.close()
            return error_response("该剧集已提取过资产，请勿重复提取", 400)

        # 更新提取状态为处理中
        cursor.execute("""
            UPDATE episodes
            SET upload_status = 'ANALYZING', uploaded_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (episode_id,))
        conn.commit()

        try:
            # 调用AI服务提取资产
            ai_service = get_ai_service(model)
            extraction_result = ai_service.extract_assets(script_content, episode_number)

            # 插入资产到数据库
            inserted_assets = {
                'characters': [],
                'props': [],
                'scenes': []
            }

            # 插入角色
            for char in extraction_result.get('characters', []):
                cursor.execute("""
                    INSERT INTO assets (
                        project_id, asset_type, name, description,
                        gender, age, voice, role,
                        first_appeared_episode_id, importance_score
                    ) VALUES (?, 'CHARACTER', ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id, char['name'], char.get('description', ''),
                    char.get('gender'), char.get('age'), char.get('voice'),
                    char.get('role'), episode_id, char.get('importance', 5)
                ))
                asset_id = cursor.lastrowid

                # 记录提取记录
                cursor.execute("""
                    INSERT INTO asset_extraction_records (
                        asset_id, episode_id, ai_model, raw_response
                    ) VALUES (?, ?, ?, ?)
                """, (asset_id, episode_id, model.value, str(char)))

                inserted_assets['characters'].append({
                    'id': asset_id,
                    'name': char['name']
                })

            # 插入道具
            for prop in extraction_result.get('props', []):
                cursor.execute("""
                    INSERT INTO assets (
                        project_id, asset_type, name, description,
                        first_appeared_episode_id, importance_score
                    ) VALUES (?, 'PROP', ?, ?, ?, ?)
                """, (
                    project_id, prop['name'], prop.get('description', ''),
                    episode_id, prop.get('importance', 5)
                ))
                asset_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO asset_extraction_records (
                        asset_id, episode_id, ai_model, raw_response
                    ) VALUES (?, ?, ?, ?)
                """, (asset_id, episode_id, model.value, str(prop)))

                inserted_assets['props'].append({
                    'id': asset_id,
                    'name': prop['name']
                })

            # 插入场景
            for scene in extraction_result.get('scenes', []):
                cursor.execute("""
                    INSERT INTO assets (
                        project_id, asset_type, name, description,
                        first_appeared_episode_id, importance_score
                    ) VALUES (?, 'SCENE', ?, ?, ?, ?)
                """, (
                    project_id, scene['name'], scene.get('description', ''),
                    episode_id, scene.get('importance', 5)
                ))
                asset_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO asset_extraction_records (
                        asset_id, episode_id, ai_model, raw_response
                    ) VALUES (?, ?, ?, ?)
                """, (asset_id, episode_id, model.value, str(scene)))

                inserted_assets['scenes'].append({
                    'id': asset_id,
                    'name': scene['name']
                })

            # 更新提取状态为完成
            cursor.execute("""
                UPDATE episodes
                SET upload_status = 'COMPLETED', uploaded_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (episode_id,))

            conn.commit()
            conn.close()

            return success_response({
                "episode_id": episode_id,
                "episode_number": episode_number,
                "model": model.value,
                "extracted_assets": inserted_assets,
                "total": {
                    "characters": len(inserted_assets['characters']),
                    "props": len(inserted_assets['props']),
                    "scenes": len(inserted_assets['scenes'])
                }
            }, "资产提取成功")

        except Exception as ai_error:
            # AI调用失败，回滚提取状态
            cursor.execute("""
                UPDATE episodes
                SET upload_status = 'FAILED', uploaded_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (episode_id,))
            conn.commit()
            conn.close()
            raise ai_error

    except Exception as e:
        return error_response(f"资产提取失败: {str(e)}", 500)


@app.route('/api/projects/<int:project_id>/assets/duplicates', methods=['GET'])
@token_required
def detect_duplicate_assets(current_user_id, project_id):
    """检测项目中的重复资产"""
    try:
        # 获取相似度阈值参数
        threshold = request.args.get('threshold', 0.8, type=float)

        if not 0 <= threshold <= 1:
            return error_response("相似度阈值必须在0-1之间", 400)

        conn = get_db()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, current_user_id))
        if not cursor.fetchone():
            conn.close()
            return error_response("项目不存在", 404)

        # 获取项目所有资产
        cursor.execute("""
            SELECT
                id, asset_type, name, description,
                gender, age, voice, role,
                first_appeared_episode_id, importance_score
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
            ORDER BY first_appeared_episode_id, id
        """, (project_id,))

        assets = []
        for row in cursor.fetchall():
            asset = {
                "id": row[0],
                "asset_type": row[1],
                "name": row[2],
                "description": row[3],
                "first_appeared_episode_id": row[8],
                "importance_score": row[9]
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

        if len(assets) < 2:
            return success_response({
                "duplicate_groups": [],
                "total_groups": 0,
                "threshold": threshold
            }, "资产数量不足，无需去重")

        # 使用去重服务检测
        dedup_service = get_deduplication_service(threshold)
        duplicate_groups = dedup_service.find_duplicates(assets)

        # 为每组生成合并建议
        for group in duplicate_groups:
            group['merge_suggestion'] = dedup_service.suggest_merge(group['assets'])

        return success_response({
            "duplicate_groups": duplicate_groups,
            "total_groups": len(duplicate_groups),
            "threshold": threshold,
            "total_assets": len(assets)
        })

    except Exception as e:
        return error_response(f"检测重复资产失败: {str(e)}", 500)


@app.route('/api/assets/merge', methods=['POST'])
@token_required
def merge_assets(current_user_id):
    """合并资产"""
    try:
        data = request.get_json()
        primary_asset_id = data.get('primary_asset_id')
        merge_asset_ids = data.get('merge_asset_ids', [])

        if not primary_asset_id:
            return error_response("主资产ID不能为空", 400)

        if not merge_asset_ids or not isinstance(merge_asset_ids, list):
            return error_response("待合并资产ID列表不能为空", 400)

        conn = get_db()
        cursor = conn.cursor()

        try:
            # 验证主资产所有权
            cursor.execute("""
                SELECT a.id, a.project_id, a.name, a.asset_type
                FROM assets a
                JOIN projects p ON a.project_id = p.id
                WHERE a.id = ? AND a.is_deleted = 0 AND p.user_id = ?
            """, (primary_asset_id, current_user_id))

            primary = cursor.fetchone()
            if not primary:
                conn.close()
                return error_response("主资产不存在或无权访问", 404)

            primary_id, project_id, primary_name, asset_type = primary

            # 检查所有待合并资产
            for merge_id in merge_asset_ids:
                cursor.execute("""
                    SELECT id, project_id, asset_type
                    FROM assets WHERE id = ? AND is_deleted = 0
                """, (merge_id,))

                merge_asset = cursor.fetchone()
                if not merge_asset:
                    conn.close()
                    return error_response(f"资产ID {merge_id} 不存在", 404)

                if merge_asset[1] != project_id:
                    conn.close()
                    return error_response(f"资产ID {merge_id} 不属于同一项目", 400)

                if merge_asset[2] != asset_type:
                    conn.close()
                    return error_response(f"资产ID {merge_id} 类型不匹配", 400)

            # 执行合并操作
            for merge_id in merge_asset_ids:
                # 记录合并历史
                cursor.execute("""
                    INSERT INTO asset_merge_history (
                        primary_asset_id, merged_asset_id
                    ) VALUES (?, ?)
                """, (primary_id, merge_id))

                # 更新分镜引用（将引用转移到主资产）
                cursor.execute("""
                    UPDATE storyboard_asset_references
                    SET asset_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE asset_id = ?
                """, (primary_id, merge_id))

                # 软删除被合并的资产
                cursor.execute("""
                    UPDATE assets
                    SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (merge_id,))

            conn.commit()

            # 获取更新后的主资产信息
            cursor.execute("""
                SELECT id, name, description, asset_type
                FROM assets WHERE id = ?
            """, (primary_id,))

            result = cursor.fetchone()
            conn.close()

            return success_response({
                "primary_asset": {
                    "id": result[0],
                    "name": result[1],
                    "description": result[2],
                    "asset_type": result[3]
                },
                "merged_count": len(merge_asset_ids),
                "merged_ids": merge_asset_ids
            }, "资产合并成功")

        except Exception as db_error:
            conn.rollback()
            conn.close()
            raise db_error

    except Exception as e:
        return error_response(f"合并资产失败: {str(e)}", 500)


@app.route('/api/projects/<int:project_id>/status', methods=['PUT'])
@token_required
def update_project_status(current_user_id, project_id):
    """
    更新项目状态

    状态转换规则:
    ASSET_BUILDING → ASSET_LOCKED (锁定资产库)
    ASSET_LOCKED → STORYBOARD_GENERATION (开始分镜生成)
    STORYBOARD_GENERATION → COMPLETED (完成项目)
    """
    try:
        data = request.get_json()
        new_status = data.get('status')

        allowed_statuses = ['ASSET_BUILDING', 'ASSET_LOCKED', 'STORYBOARD_GENERATION', 'COMPLETED']
        if new_status not in allowed_statuses:
            return error_response(f"无效的状态值，允许的状态: {', '.join(allowed_statuses)}", 400)

        conn = get_db()
        cursor = conn.cursor()

        try:
            # 验证项目所有权并获取当前状态
            cursor.execute("""
                SELECT id, name, status FROM projects WHERE id = ? AND user_id = ?
            """, (project_id,))

            project = cursor.fetchone()
            if not project:
                conn.close()
                return error_response("项目不存在", 404)

            current_status = project[2]

            # 验证状态转换
            valid_transitions = {
                'ASSET_BUILDING': ['ASSET_LOCKED'],
                'ASSET_LOCKED': ['ASSET_BUILDING', 'STORYBOARD_GENERATION'],
                'STORYBOARD_GENERATION': ['COMPLETED'],
                'COMPLETED': []
            }

            if new_status not in valid_transitions.get(current_status, []):
                conn.close()
                return error_response(
                    f"不允许从 {current_status} 转换到 {new_status}",
                    400
                )

            # 特殊检查：锁定资产库前必须有资产
            if new_status == 'ASSET_LOCKED':
                cursor.execute("""
                    SELECT COUNT(*) FROM assets
                    WHERE project_id = ? AND is_deleted = 0
                """, (project_id,))
                asset_count = cursor.fetchone()[0]

                if asset_count == 0:
                    conn.close()
                    return error_response("资产库为空，无法锁定", 400)

                # 创建资产库快照
                cursor.execute("""
                    INSERT INTO asset_snapshots (
                        project_id, snapshot_name, asset_count
                    ) VALUES (?, ?, ?)
                """, (project_id, f"锁定快照-{project[1]}", asset_count))

                snapshot_id = cursor.lastrowid

                # 更新项目的当前快照ID
                cursor.execute("""
                    UPDATE projects
                    SET status = ?, current_snapshot_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_status, snapshot_id, project_id))
            else:
                # 普通状态更新
                cursor.execute("""
                    UPDATE projects
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_status, project_id))

            conn.commit()

            # 获取更新后的项目信息
            cursor.execute("""
                SELECT id, name, status, current_snapshot_id, updated_at
                FROM projects WHERE id = ?
            """, (project_id,))

            result = cursor.fetchone()
            conn.close()

            return success_response({
                "id": result[0],
                "name": result[1],
                "status": result[2],
                "current_snapshot_id": result[3],
                "updated_at": result[4],
                "previous_status": current_status
            }, f"项目状态已更新为 {new_status}")

        except Exception as db_error:
            conn.rollback()
            conn.close()
            raise db_error

    except Exception as e:
        return error_response(f"更新项目状态失败: {str(e)}", 500)


@app.route('/api/projects/<int:project_id>/snapshots', methods=['GET'])
@token_required
def get_project_snapshots(current_user_id, project_id):
    """获取项目的资产快照历史"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, current_user_id))
        if not cursor.fetchone():
            conn.close()
            return error_response("项目不存在", 404)

        # 获取快照列表
        cursor.execute("""
            SELECT
                id, snapshot_name, asset_count,
                created_at, is_locked
            FROM asset_snapshots
            WHERE project_id = ?
            ORDER BY created_at DESC
        """, (project_id,))

        snapshots = []
        for row in cursor.fetchall():
            snapshots.append({
                "id": row[0],
                "snapshot_name": row[1],
                "asset_count": row[2],
                "created_at": row[3],
                "is_locked": bool(row[4])
            })

        conn.close()

        return success_response({
            "snapshots": snapshots,
            "total": len(snapshots)
        })

    except Exception as e:
        return error_response(f"获取快照列表失败: {str(e)}", 500)


@app.route('/api/projects/<int:project_id>/statistics', methods=['GET'])
@token_required
def get_project_statistics(current_user_id, project_id):
    """获取项目统计信息"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute("""
            SELECT id, name, status, created_at
            FROM projects WHERE id = ? AND user_id = ?
        """, (project_id, current_user_id))

        project = cursor.fetchone()
        if not project:
            conn.close()
            return error_response("项目不存在", 404)

        # 统计剧集信息
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN upload_status = 'COMPLETED' THEN 1 ELSE 0 END) as extracted
            FROM episodes
            WHERE project_id = ?
        """, (project_id,))
        episode_stats = cursor.fetchone()

        # 统计资产信息
        cursor.execute("""
            SELECT
                asset_type,
                COUNT(*) as count
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
            GROUP BY asset_type
        """, (project_id,))

        asset_stats = {}
        total_assets = 0
        for row in cursor.fetchall():
            asset_stats[row[0]] = row[1]
            total_assets += row[1]

        # 统计合并历史
        cursor.execute("""
            SELECT COUNT(DISTINCT primary_asset_id)
            FROM asset_merge_history h
            JOIN assets a ON h.primary_asset_id = a.id
            WHERE a.project_id = ?
        """, (project_id,))
        merged_groups = cursor.fetchone()[0]

        # 统计分镜信息
        cursor.execute("""
            SELECT COUNT(*)
            FROM storyboards s
            JOIN episodes e ON s.episode_id = e.id
            WHERE e.project_id = ?
        """, (project_id,))
        storyboard_count = cursor.fetchone()[0]

        conn.close()

        return success_response({
            "project": {
                "id": project[0],
                "name": project[1],
                "status": project[2],
                "created_at": project[3]
            },
            "episodes": {
                "total": episode_stats[0],
                "extracted": episode_stats[1],
                "pending": episode_stats[0] - episode_stats[1]
            },
            "assets": {
                "total": total_assets,
                "by_type": asset_stats,
                "merged_groups": merged_groups
            },
            "storyboards": {
                "total": storyboard_count
            }
        })

    except Exception as e:
        return error_response(f"获取项目统计失败: {str(e)}", 500)


# ===================================
# 启动应用
# ===================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
