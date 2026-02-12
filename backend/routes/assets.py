"""
资产管理路由
"""
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from database.init_db import get_connection
from services.ai_service import get_ai_service, AIModel
from services.asset_service import get_asset_service

assets_bp = Blueprint('assets', __name__, url_prefix='/api/projects')


@assets_bp.route('/<int:project_id>/episodes/<int:episode_id>/extract-assets', methods=['POST'])
@token_required
def extract_assets(current_user, project_id, episode_id):
    """提取或重新提取资产"""
    conn = None
    try:
        data = request.get_json()
        model_name = data.get('model', 'claude')  # 默认使用Claude
        feedback = data.get('feedback')  # 优化反馈（可选）

        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和剧集存在
        cursor.execute('''
            SELECT e.id, e.script_content, e.episode_number
            FROM episodes e
            JOIN projects p ON e.project_id = p.id
            WHERE e.id = ? AND e.project_id = ? AND p.user_id = ?
        ''', (episode_id, project_id, current_user))

        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': '剧集不存在'}), 404

        script_content = row[1]
        episode_number = row[2]

        # 获取当前已有的资产数据（用于优化）
        current_data = None
        if feedback:
            cursor.execute('''
                SELECT asset_type, name, description, gender, age, voice, role
                FROM assets
                WHERE project_id = ? AND is_deleted = 0
            ''', (project_id,))

            characters = []
            props = []
            scenes = []

            for asset_row in cursor.fetchall():
                asset_type = asset_row[0]
                asset_dict = {
                    'name': asset_row[1],
                    'description': asset_row[2]
                }

                if asset_type == 'CHARACTER':
                    asset_dict.update({
                        'gender': asset_row[3],
                        'age': asset_row[4],
                        'voice': asset_row[5],
                        'role': asset_row[6]
                    })
                    characters.append(asset_dict)
                elif asset_type == 'PROP':
                    props.append(asset_dict)
                elif asset_type == 'SCENE':
                    scenes.append(asset_dict)

            current_data = {
                'characters': characters,
                'props': props,
                'scenes': scenes
            }

        # 选择AI模型（支持新的模型标识符和旧的简单名称）
        # 新格式：'claude-sonnet-4-5', 'deepseek-chat', 'gemini-2.0-flash', 'gpt-4'
        # 旧格式：'claude', 'deepseek', 'gemini', 'gpt4'（会自动映射到默认模型）
        ai_service = get_ai_service(model_name)
        extracted_assets = ai_service.extract_assets(
            script_content,
            episode_number=episode_number,
            feedback=feedback,
            current_data=current_data
        )

        # 创建版本记录
        asset_service = get_asset_service()
        version_id = asset_service.create_version(
            project_id=project_id,
            model_used=model_name,
            extraction_type='optimization' if feedback else 'initial',
            feedback=feedback,
            episode_id=episode_id
        )

        # 如果是优化模式，删除旧资产（不关联版本的资产）
        if feedback and current_data:
            cursor.execute('DELETE FROM assets WHERE project_id = ? AND version_id IS NULL', (project_id,))

        # 插入资产，关联到版本ID
        for character in extracted_assets.get('characters', []):
            cursor.execute('''
                INSERT INTO assets (
                    project_id, asset_type, name, description,
                    gender, age, voice, role, first_appeared_episode_id, version_id
                ) VALUES (?, 'CHARACTER', ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                character['name'],
                character['description'],
                character.get('gender', ''),
                character.get('age', ''),
                character.get('voice', ''),
                character.get('role', ''),
                episode_id,
                version_id
            ))

        for prop in extracted_assets.get('props', []):
            cursor.execute('''
                INSERT INTO assets (
                    project_id, asset_type, name, description, first_appeared_episode_id, version_id
                ) VALUES (?, 'PROP', ?, ?, ?, ?)
            ''', (project_id, prop['name'], prop['description'], episode_id, version_id))

        for scene in extracted_assets.get('scenes', []):
            cursor.execute('''
                INSERT INTO assets (
                    project_id, asset_type, name, description, first_appeared_episode_id, version_id
                ) VALUES (?, 'SCENE', ?, ?, ?, ?)
            ''', (project_id, scene['name'], scene['description'], episode_id, version_id))

        conn.commit()

        # 更新版本的资产数量
        asset_service.update_version_asset_count(version_id)

        # 自动创建资产快照
        cursor.execute('SELECT COUNT(*) FROM assets WHERE project_id = ? AND is_deleted = 0', (project_id,))
        asset_count = cursor.fetchone()[0]

        # 创建快照
        from datetime import datetime
        snapshot_name = f"资产拆解-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        cursor.execute('''
            INSERT INTO asset_snapshots (project_id, snapshot_name, asset_count)
            VALUES (?, ?, ?)
        ''', (project_id, snapshot_name, asset_count))

        snapshot_id = cursor.lastrowid

        # 更新项目的当前快照ID
        cursor.execute('''
            UPDATE projects
            SET current_snapshot_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (snapshot_id, project_id))

        conn.commit()

        return jsonify({
            'success': True,
            'data': {
                'assets': extracted_assets,
                'version_id': version_id,
                'snapshot_id': snapshot_id,
                'snapshot_name': snapshot_name,
                'message': '资产优化成功，快照已创建' if feedback else '资产提取成功，快照已创建'
            }
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@assets_bp.route('/<int:project_id>/assets', methods=['GET'])
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

        # 获取资产列表（只获取最新版本的资产）
        cursor.execute('''
            SELECT id, asset_type, name, description, gender, age, voice, role, created_at
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
            ORDER BY asset_type, name
        ''', (project_id,))

        assets = []
        for row in cursor.fetchall():
            asset = {
                'id': row[0],
                'asset_type': row[1],
                'name': row[2],
                'description': row[3],
                'created_at': row[8]
            }

            if row[1] == 'CHARACTER':
                asset.update({
                    'gender': row[4],
                    'age': row[5],
                    'voice': row[6],
                    'role': row[7]
                })

            assets.append(asset)

        return jsonify({'success': True, 'data': {'assets': assets}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@assets_bp.route('/<int:project_id>/asset-versions', methods=['GET'])
@token_required
def get_asset_versions(current_user, project_id):
    """获取项目的资产版本历史"""
    try:
        # 验证项目所有权
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        conn.close()

        # 获取版本历史
        asset_service = get_asset_service()
        versions = asset_service.get_version_history(project_id, limit=5)

        return jsonify({
            'success': True,
            'data': {'versions': versions}
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@assets_bp.route('/<int:project_id>/asset-versions/<int:version_id>', methods=['GET'])
@token_required
def get_version_assets(current_user, project_id, version_id):
    """获取指定版本的资产"""
    try:
        # 验证项目所有权
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 验证版本属于该项目
        cursor.execute('''
            SELECT id FROM asset_extraction_versions
            WHERE id = ? AND project_id = ?
        ''', (version_id, project_id))

        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '版本不存在'}), 404
        conn.close()

        # 获取版本资产
        asset_service = get_asset_service()
        assets = asset_service.get_version_assets(version_id)

        return jsonify({
            'success': True,
            'data': {'assets': assets}
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@assets_bp.route('/<int:project_id>/assets/<int:asset_id>', methods=['DELETE'])
@token_required
def delete_asset(current_user, project_id, asset_id):
    """删除单个资产（软删除）"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和资产存在
        cursor.execute('''
            SELECT a.id, a.name
            FROM assets a
            JOIN projects p ON a.project_id = p.id
            WHERE a.id = ? AND a.project_id = ? AND p.user_id = ? AND a.is_deleted = 0
        ''', (asset_id, project_id, current_user))

        asset = cursor.fetchone()
        if not asset:
            return jsonify({'success': False, 'error': '资产不存在'}), 404

        # 软删除资产
        cursor.execute('''
            UPDATE assets
            SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (asset_id,))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'资产 "{asset[1]}" 已删除'
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
