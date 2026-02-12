"""
项目管理路由
"""
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from database.init_db import get_connection
from services.ai_service import get_ai_service, AIModel
from services.deduplication_service import get_deduplication_service
import json
from datetime import datetime

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

# ===================================
# 项目管理端点
# ===================================

@projects_bp.route('', methods=['POST'])
@token_required
def create_project(current_user):
    """创建新项目"""
    conn = None
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')

        if not name:
            return jsonify({'success': False, 'error': '项目名称不能为空'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # 检查是否存在同名的未删除项目
        cursor.execute('''
            SELECT id FROM projects
            WHERE user_id = ? AND name = ? AND is_deleted = 0
        ''', (current_user, name))

        if cursor.fetchone():
            return jsonify({'success': False, 'error': f'项目名称"{name}"已存在，请使用其他名称'}), 400

        cursor.execute('''
            INSERT INTO projects (user_id, name, description, status)
            VALUES (?, ?, ?, 'ASSET_BUILDING')
        ''', (current_user, name, description))

        project_id = cursor.lastrowid
        conn.commit()

        # 获取创建的项目
        cursor.execute('''
            SELECT id, user_id, name, description, status, created_at, updated_at
            FROM projects WHERE id = ?
        ''', (project_id,))

        row = cursor.fetchone()
        project = {
            'id': row[0],
            'user_id': row[1],
            'name': row[2],
            'description': row[3],
            'status': row[4],
            'created_at': row[5],
            'updated_at': row[6]
        }

        return jsonify({'success': True, 'data': {'project': project}}), 201

    except Exception as e:
        if conn:
            conn.rollback()

        # 处理重复项目名称错误
        error_msg = str(e)
        if 'UNIQUE constraint failed' in error_msg and 'projects.name' in error_msg:
            return jsonify({'success': False, 'error': f'项目名称"{name}"已存在，请使用其他名称'}), 400

        return jsonify({'success': False, 'error': error_msg}), 500
    finally:
        if conn:
            conn.close()


@projects_bp.route('', methods=['GET'])
@token_required
def get_projects(current_user):
    """获取用户的项目列表"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, user_id, name, description, status, created_at, updated_at
            FROM projects
            WHERE user_id = ? AND is_deleted = 0
            ORDER BY updated_at DESC
        ''', (current_user,))

        projects = []
        for row in cursor.fetchall():
            projects.append({
                'id': row[0],
                'user_id': row[1],
                'name': row[2],
                'description': row[3],
                'status': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            })

        return jsonify({'success': True, 'data': {'projects': projects}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@projects_bp.route('/<int:project_id>', methods=['GET'])
@token_required
def get_project(current_user, project_id):
    """获取项目详情"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, user_id, name, description, status, created_at, updated_at
            FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        project = {
            'id': row[0],
            'user_id': row[1],
            'name': row[2],
            'description': row[3],
            'status': row[4],
            'created_at': row[5],
            'updated_at': row[6]
        }

        return jsonify({'success': True, 'data': {'project': project}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@token_required
def update_project(current_user, project_id):
    """更新项目"""
    conn = None
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute('''
            SELECT id FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 更新项目
        update_fields = []
        params = []

        if 'name' in data:
            update_fields.append('name = ?')
            params.append(data['name'])

        if 'description' in data:
            update_fields.append('description = ?')
            params.append(data['description'])

        if 'status' in data:
            update_fields.append('status = ?')
            params.append(data['status'])

        if not update_fields:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400

        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(project_id)

        cursor.execute(f'''
            UPDATE projects
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', params)

        conn.commit()

        return jsonify({'success': True, 'message': '项目更新成功'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@token_required
def delete_project(current_user, project_id):
    """删除项目（软删除）"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute('''
            SELECT id, name FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        project = cursor.fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 软删除项目
        cursor.execute('''
            UPDATE projects
            SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (project_id,))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'项目 "{project[1]}" 已删除'
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# ===================================
# 资产管理端点
# ===================================

@projects_bp.route('/<int:project_id>/extract-assets', methods=['POST'])
@token_required
def extract_assets(current_user, project_id):
    """提取或优化资产"""
    conn = None
    try:
        data = request.get_json()
        script_content = data.get('script_content')
        model_name = data.get('model', 'claude-sonnet-4-5')  # 默认使用Claude Sonnet 4.5
        feedback = data.get('feedback')  # 优化反馈（可选）

        # 如果是优化模式，不需要script_content
        if not feedback and not script_content:
            return jsonify({'success': False, 'error': '剧本内容不能为空'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute('''
            SELECT id FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 获取现有资产（用于去重或优化）
        cursor.execute('''
            SELECT id, asset_type, name, description, gender, age, voice, role
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
        ''', (project_id,))

        existing_assets = []
        current_data = {'characters': [], 'props': [], 'scenes': []}

        for row in cursor.fetchall():
            asset_dict = {
                'id': row[0],
                'asset_type': row[1],
                'name': row[2],
                'description': row[3],
                'gender': row[4],
                'age': row[5],
                'voice': row[6],
                'role': row[7]
            }
            existing_assets.append(asset_dict)

            # 构建current_data用于优化
            if feedback:
                asset_data = {
                    'name': row[2],
                    'description': row[3]
                }
                if row[1] == 'CHARACTER':
                    asset_data.update({
                        'gender': row[4],
                        'age': row[5],
                        'voice': row[6],
                        'role': row[7]
                    })
                    current_data['characters'].append(asset_data)
                elif row[1] == 'PROP':
                    current_data['props'].append(asset_data)
                elif row[1] == 'SCENE':
                    current_data['scenes'].append(asset_data)

        # 使用AI服务提取或优化资产（支持新的模型标识符和旧的简单名称）
        ai_service = get_ai_service(model_name)

        if feedback:
            # 优化模式：传递当前数据和反馈
            extraction_result = ai_service.extract_assets(
                script_content or '',  # 优化时可能不需要script_content
                feedback=feedback,
                current_data=current_data
            )
            # 删除旧资产
            cursor.execute('DELETE FROM assets WHERE project_id = ?', (project_id,))
        else:
            # 初始提取模式
            extraction_result = ai_service.extract_assets(script_content)

        # 使用去重服务（仅在非优化模式下）
        dedup_service = get_deduplication_service()

        # 处理角色资产
        for character in extraction_result.get('characters', []):
            asset = {
                'asset_type': 'CHARACTER',
                'name': character['name'],
                'description': character.get('description', ''),
                'gender': character.get('gender'),
                'age': character.get('age'),
                'voice': character.get('voice'),
                'role': character.get('role')
            }
            # 优化模式下不去重，直接插入
            if feedback or not dedup_service.is_duplicate_asset(asset, existing_assets):
                cursor.execute('''
                    INSERT INTO assets (
                        project_id, asset_type, name, description,
                        gender, age, voice, role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id,
                    asset['asset_type'],
                    asset['name'],
                    asset['description'],
                    asset.get('gender'),
                    asset.get('age'),
                    asset.get('voice'),
                    asset.get('role')
                ))
                if not feedback:
                    asset['id'] = cursor.lastrowid
                    existing_assets.append(asset)

        # 处理道具资产
        for prop in extraction_result.get('props', []):
            asset = {
                'asset_type': 'PROP',
                'name': prop['name'],
                'description': prop.get('description', ''),
                'gender': None,
                'age': None,
                'voice': None,
                'role': None
            }
            if feedback or not dedup_service.is_duplicate_asset(asset, existing_assets):
                cursor.execute('''
                    INSERT INTO assets (
                        project_id, asset_type, name, description,
                        gender, age, voice, role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id,
                    asset['asset_type'],
                    asset['name'],
                    asset['description'],
                    None, None, None, None
                ))
                if not feedback:
                    asset['id'] = cursor.lastrowid
                    existing_assets.append(asset)

        # 处理场景资产
        for scene in extraction_result.get('scenes', []):
            asset = {
                'asset_type': 'SCENE',
                'name': scene['name'],
                'description': scene.get('description', ''),
                'gender': None,
                'age': None,
                'voice': None,
                'role': None
            }
            if feedback or not dedup_service.is_duplicate_asset(asset, existing_assets):
                cursor.execute('''
                    INSERT INTO assets (
                        project_id, asset_type, name, description,
                        gender, age, voice, role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id,
                    asset['asset_type'],
                    asset['name'],
                    asset.get('description', ''),
                    asset.get('gender'),
                    asset.get('age'),
                    asset.get('voice'),
                    asset.get('role')
                ))

                if not feedback:
                    asset['id'] = cursor.lastrowid
                    existing_assets.append(asset)

        conn.commit()

        # 返回所有资产
        cursor.execute('''
            SELECT id, project_id, asset_type, name, description,
                   gender, age, voice, role, is_deleted, created_at, updated_at
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
            ORDER BY asset_type, id
        ''', (project_id,))

        assets = []
        for row in cursor.fetchall():
            assets.append({
                'id': row[0],
                'project_id': row[1],
                'asset_type': row[2],
                'name': row[3],
                'description': row[4],
                'gender': row[5],
                'age': row[6],
                'voice': row[7],
                'role': row[8],
                'is_deleted': row[9],
                'created_at': row[10],
                'updated_at': row[11]
            })

        return jsonify({'success': True, 'data': {'assets': assets}}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@projects_bp.route('/<int:project_id>/assets', methods=['GET'])
@token_required
def get_assets(current_user, project_id):
    """获取项目的资产列表"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute('''
            SELECT id FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 获取资产列表
        cursor.execute('''
            SELECT id, project_id, asset_type, name, description,
                   gender, age, voice, role, is_deleted, created_at, updated_at
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
            ORDER BY asset_type, id
        ''', (project_id,))

        assets = []
        for row in cursor.fetchall():
            assets.append({
                'id': row[0],
                'project_id': row[1],
                'asset_type': row[2],
                'name': row[3],
                'description': row[4],
                'gender': row[5],
                'age': row[6],
                'voice': row[7],
                'role': row[8],
                'is_deleted': row[9],
                'created_at': row[10],
                'updated_at': row[11]
            })

        return jsonify({'success': True, 'data': {'assets': assets}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@projects_bp.route('/<int:project_id>/assets/<int:asset_id>', methods=['PUT'])
@token_required
def update_asset(current_user, project_id, asset_id):
    """更新资产"""
    conn = None
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和资产存在
        cursor.execute('''
            SELECT a.id FROM assets a
            JOIN projects p ON a.project_id = p.id
            WHERE a.id = ? AND a.project_id = ? AND p.user_id = ? AND a.is_deleted = 0
        ''', (asset_id, project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '资产不存在'}), 404

        # 更新资产
        update_fields = []
        params = []

        if 'name' in data:
            update_fields.append('name = ?')
            params.append(data['name'])

        if 'description' in data:
            update_fields.append('description = ?')
            params.append(data['description'])

        if 'gender' in data:
            update_fields.append('gender = ?')
            params.append(data['gender'])

        if 'age' in data:
            update_fields.append('age = ?')
            params.append(data['age'])

        if 'voice' in data:
            update_fields.append('voice = ?')
            params.append(data['voice'])

        if 'role' in data:
            update_fields.append('role = ?')
            params.append(data['role'])

        if not update_fields:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400

        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(asset_id)

        cursor.execute(f'''
            UPDATE assets
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', params)

        conn.commit()

        return jsonify({'success': True, 'message': '资产更新成功'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@projects_bp.route('/<int:project_id>/assets/<int:asset_id>', methods=['DELETE'])
@token_required
def delete_asset(current_user, project_id, asset_id):
    """删除资产（软删除）"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和资产存在
        cursor.execute('''
            SELECT a.id FROM assets a
            JOIN projects p ON a.project_id = p.id
            WHERE a.id = ? AND a.project_id = ? AND p.user_id = ? AND a.is_deleted = 0
        ''', (asset_id, project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '资产不存在'}), 404

        # 软删除资产
        cursor.execute('''
            UPDATE assets
            SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (asset_id,))

        conn.commit()

        return jsonify({'success': True, 'message': '资产删除成功'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
