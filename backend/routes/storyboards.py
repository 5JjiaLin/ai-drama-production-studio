"""
分镜管理路由
"""
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from database.init_db import get_connection
from services.ai_service import get_ai_service

storyboards_bp = Blueprint('storyboards', __name__, url_prefix='/api/projects')


@storyboards_bp.route('/<int:project_id>/generate-storyboards', methods=['POST'])
@token_required
def generate_storyboards(current_user, project_id):
    """生成分镜"""
    conn = None
    try:
        data = request.get_json()
        episode_id = data.get('episode_id')
        min_shots = data.get('min_shots', 10)
        max_shots = data.get('max_shots', 30)
        model_name = data.get('model', 'claude-sonnet-4-5')  # 默认使用Claude Sonnet 4.5

        if not episode_id:
            return jsonify({'success': False, 'error': '剧集ID不能为空'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和剧集存在
        cursor.execute('''
            SELECT e.id, e.script_content, p.current_snapshot_id
            FROM episodes e
            JOIN projects p ON e.project_id = p.id
            WHERE e.id = ? AND e.project_id = ? AND p.user_id = ?
        ''', (episode_id, project_id, current_user))

        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': '剧集不存在'}), 404

        script_content = row[1]
        snapshot_id = row[2]

        # 如果没有快照，自动创建一个
        if not snapshot_id:
            # 获取项目的所有资产
            cursor.execute('''
                SELECT id, name, description, asset_type, gender, age, voice, role
                FROM assets
                WHERE project_id = ? AND is_deleted = 0
                ORDER BY asset_type, name
            ''', (project_id,))

            assets_rows = cursor.fetchall()

            # 检查是否有资产
            if not assets_rows:
                return jsonify({'success': False, 'error': '项目中没有资产，请先进行资产拆解'}), 400

            # 构建资产数据JSON
            assets_data = {
                'characters': [],
                'props': [],
                'scenes': []
            }

            for row_asset in assets_rows:
                asset_obj = {
                    'id': row_asset[0],
                    'name': row_asset[1],
                    'description': row_asset[2] or '',
                    'asset_type': row_asset[3]
                }

                if row_asset[3] == 'CHARACTER':
                    asset_obj.update({
                        'gender': row_asset[4] or '',
                        'age': row_asset[5] or '',
                        'voice': row_asset[6] or '',
                        'role': row_asset[7] or ''
                    })
                    assets_data['characters'].append(asset_obj)
                elif row_asset[3] == 'PROP':
                    assets_data['props'].append(asset_obj)
                elif row_asset[3] == 'SCENE':
                    assets_data['scenes'].append(asset_obj)

            # 创建快照
            import json
            snapshot_name = f"自动快照 - {episode_id}"
            cursor.execute('''
                INSERT INTO asset_snapshots (project_id, snapshot_name, description, assets_data, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (project_id, snapshot_name, '分镜生成时自动创建', json.dumps(assets_data, ensure_ascii=False)))

            snapshot_id = cursor.lastrowid

            # 更新项目的current_snapshot_id
            cursor.execute('''
                UPDATE projects
                SET current_snapshot_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (snapshot_id, project_id))

            conn.commit()

        # 获取项目的资产库信息
        cursor.execute('''
            SELECT id, name, description, asset_type, gender, age, voice, role
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
            ORDER BY asset_type, name
        ''', (project_id,))

        assets_rows = cursor.fetchall()

        # 按类型分组资产
        characters = []
        props = []
        scenes = []

        for row in assets_rows:
            asset_data = {
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'asset_type': row[3]
            }

            if row[3] == 'CHARACTER':
                asset_data.update({
                    'gender': row[4] or '',
                    'age': row[5] or '',
                    'voice': row[6] or '',
                    'role': row[7] or ''
                })
                characters.append(asset_data)
            elif row[3] == 'PROP':
                props.append(asset_data)
            elif row[3] == 'SCENE':
                scenes.append(asset_data)

        assets_library = {
            'characters': characters,
            'props': props,
            'scenes': scenes
        }

        # 使用AI服务生成分镜（支持新的模型标识符和旧的简单名称）
        ai_service = get_ai_service(model_name)
        generated_storyboards = ai_service.generate_storyboards(
            script_content,
            min_shots=min_shots,
            max_shots=max_shots,
            assets=assets_library
        )

        # 插入分镜
        for sb in generated_storyboards:
            cursor.execute('''
                INSERT INTO storyboards (
                    episode_id, snapshot_id, shot_number, voice_character,
                    emotion, intensity, asset_mapping, dialogue, fusion_prompt, motion_prompt,
                    generation_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT')
            ''', (
                episode_id,
                snapshot_id,
                sb['shot_number'],
                sb.get('voice_character', ''),
                sb.get('emotion', ''),
                sb.get('intensity', ''),
                sb.get('asset_mapping', ''),
                sb.get('dialogue', ''),
                sb.get('fusion_prompt', ''),
                sb.get('motion_prompt', '')
            ))

        conn.commit()

        # 返回生成的分镜
        cursor.execute('''
            SELECT id, episode_id, snapshot_id, shot_number, voice_character,
                   emotion, intensity, asset_mapping, dialogue, fusion_prompt, motion_prompt,
                   generation_status, created_at, updated_at
            FROM storyboards
            WHERE snapshot_id = ?
            ORDER BY shot_number
        ''', (snapshot_id,))

        storyboards = []
        for row in cursor.fetchall():
            storyboards.append({
                'id': row[0],
                'episode_id': row[1],
                'snapshot_id': row[2],
                'shot_number': row[3],
                'voice_character': row[4],
                'emotion': row[5],
                'intensity': row[6],
                'asset_mapping': row[7],
                'dialogue': row[8],
                'fusion_prompt': row[9],
                'motion_prompt': row[10],
                'generation_status': row[11],
                'created_at': row[12],
                'updated_at': row[13]
            })

        return jsonify({'success': True, 'data': {'storyboards': storyboards}}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@storyboards_bp.route('/<int:project_id>/episodes/<int:episode_id>/storyboards', methods=['GET'])
@token_required
def get_storyboards(current_user, project_id, episode_id):
    """获取剧集的分镜列表"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和剧集存在
        cursor.execute('''
            SELECT e.id
            FROM episodes e
            JOIN projects p ON e.project_id = p.id
            WHERE e.id = ? AND e.project_id = ? AND p.user_id = ?
        ''', (episode_id, project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '剧集不存在'}), 404

        # 获取最新快照的分镜
        cursor.execute('''
            SELECT s.id, s.episode_id, s.snapshot_id, s.shot_number, s.voice_character,
                   s.emotion, s.intensity, s.asset_mapping, s.dialogue, s.fusion_prompt, s.motion_prompt,
                   s.generation_status, s.created_at, s.updated_at
            FROM storyboards s
            WHERE s.episode_id = ? AND s.snapshot_id = (
                SELECT MAX(snapshot_id) FROM storyboards WHERE episode_id = ?
            )
            ORDER BY s.shot_number
        ''', (episode_id, episode_id))

        storyboards = []
        for row in cursor.fetchall():
            storyboards.append({
                'id': row[0],
                'episode_id': row[1],
                'snapshot_id': row[2],
                'shot_number': row[3],
                'voice_character': row[4],
                'emotion': row[5],
                'intensity': row[6],
                'asset_mapping': row[7],
                'dialogue': row[8],
                'fusion_prompt': row[9],
                'motion_prompt': row[10],
                'generation_status': row[11],
                'created_at': row[12],
                'updated_at': row[13]
            })

        return jsonify({'success': True, 'data': {'storyboards': storyboards}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@storyboards_bp.route('/<int:project_id>/episodes/<int:episode_id>/storyboards/<int:storyboard_id>', methods=['PUT'])
@token_required
def update_storyboard(current_user, project_id, episode_id, storyboard_id):
    """更新分镜"""
    conn = None
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和分镜存在
        cursor.execute('''
            SELECT s.id
            FROM storyboards s
            JOIN episodes e ON s.episode_id = e.id
            JOIN projects p ON e.project_id = p.id
            WHERE s.id = ? AND s.episode_id = ? AND e.project_id = ? AND p.user_id = ?
        ''', (storyboard_id, episode_id, project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '分镜不存在'}), 404

        # 更新分镜
        update_fields = []
        params = []

        if 'voice_character' in data:
            update_fields.append('voice_character = ?')
            params.append(data['voice_character'])

        if 'emotion' in data:
            update_fields.append('emotion = ?')
            params.append(data['emotion'])

        if 'intensity' in data:
            update_fields.append('intensity = ?')
            params.append(data['intensity'])

        if 'dialogue' in data:
            update_fields.append('dialogue = ?')
            params.append(data['dialogue'])

        if 'fusion_prompt' in data:
            update_fields.append('fusion_prompt = ?')
            params.append(data['fusion_prompt'])

        if 'motion_prompt' in data:
            update_fields.append('motion_prompt = ?')
            params.append(data['motion_prompt'])

        if not update_fields:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400

        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(storyboard_id)

        cursor.execute(f'''
            UPDATE storyboards
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', params)

        conn.commit()

        return jsonify({'success': True, 'message': '分镜更新成功'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@storyboards_bp.route('/<int:project_id>/episodes/<int:episode_id>/storyboards/<int:storyboard_id>', methods=['DELETE'])
@token_required
def delete_storyboard(current_user, project_id, episode_id, storyboard_id):
    """删除分镜"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和分镜存在
        cursor.execute('''
            SELECT s.id
            FROM storyboards s
            JOIN episodes e ON s.episode_id = e.id
            JOIN projects p ON e.project_id = p.id
            WHERE s.id = ? AND s.episode_id = ? AND e.project_id = ? AND p.user_id = ?
        ''', (storyboard_id, episode_id, project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '分镜不存在'}), 404

        # 删除分镜
        cursor.execute('DELETE FROM storyboards WHERE id = ?', (storyboard_id,))
        conn.commit()

        return jsonify({'success': True, 'message': '分镜删除成功'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@storyboards_bp.route('/<int:project_id>/episodes/<int:episode_id>/optimize-storyboards', methods=['POST'])
@token_required
def optimize_storyboards(current_user, project_id, episode_id):
    """优化分镜"""
    conn = None
    try:
        data = request.get_json()
        feedback = data.get('feedback')
        min_shots = data.get('min_shots', 10)
        max_shots = data.get('max_shots', 30)
        model_name = data.get('model', 'claude-sonnet-4-5')  # 默认使用Claude Sonnet 4.5

        if not feedback:
            return jsonify({'success': False, 'error': '优化反馈不能为空'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和剧集存在
        cursor.execute('''
            SELECT e.id, e.script_content, p.current_snapshot_id
            FROM episodes e
            JOIN projects p ON e.project_id = p.id
            WHERE e.id = ? AND e.project_id = ? AND p.user_id = ?
        ''', (episode_id, project_id, current_user))

        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': '剧集不存在'}), 404

        script_content = row[1]
        snapshot_id = row[2]

        # 如果没有快照，自动创建一个
        if not snapshot_id:
            # 获取项目的所有资产
            cursor.execute('''
                SELECT id, name, description, asset_type, gender, age, voice, role
                FROM assets
                WHERE project_id = ? AND is_deleted = 0
                ORDER BY asset_type, name
            ''', (project_id,))

            assets_rows = cursor.fetchall()

            # 检查是否有资产
            if not assets_rows:
                return jsonify({'success': False, 'error': '项目中没有资产，请先进行资产拆解'}), 400

            # 构建资产数据JSON
            assets_data = {
                'characters': [],
                'props': [],
                'scenes': []
            }

            for row_asset in assets_rows:
                asset_obj = {
                    'id': row_asset[0],
                    'name': row_asset[1],
                    'description': row_asset[2] or '',
                    'asset_type': row_asset[3]
                }

                if row_asset[3] == 'CHARACTER':
                    asset_obj.update({
                        'gender': row_asset[4] or '',
                        'age': row_asset[5] or '',
                        'voice': row_asset[6] or '',
                        'role': row_asset[7] or ''
                    })
                    assets_data['characters'].append(asset_obj)
                elif row_asset[3] == 'PROP':
                    assets_data['props'].append(asset_obj)
                elif row_asset[3] == 'SCENE':
                    assets_data['scenes'].append(asset_obj)

            # 创建快照
            import json
            snapshot_name = f"自动快照 - 优化分镜"
            cursor.execute('''
                INSERT INTO asset_snapshots (project_id, snapshot_name, description, assets_data, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (project_id, snapshot_name, '优化分镜时自动创建', json.dumps(assets_data, ensure_ascii=False)))

            snapshot_id = cursor.lastrowid

            # 更新项目的current_snapshot_id
            cursor.execute('''
                UPDATE projects
                SET current_snapshot_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (snapshot_id, project_id))

            conn.commit()

        # 获取项目的资产库信息
        cursor.execute('''
            SELECT id, name, description, asset_type, gender, age, voice, role
            FROM assets
            WHERE project_id = ? AND is_deleted = 0
            ORDER BY asset_type, name
        ''', (project_id,))

        assets_rows = cursor.fetchall()

        # 按类型分组资产
        characters = []
        props = []
        scenes = []

        for row in assets_rows:
            asset_data = {
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'asset_type': row[3]
            }

            if row[3] == 'CHARACTER':
                asset_data.update({
                    'gender': row[4] or '',
                    'age': row[5] or '',
                    'voice': row[6] or '',
                    'role': row[7] or ''
                })
                characters.append(asset_data)
            elif row[3] == 'PROP':
                props.append(asset_data)
            elif row[3] == 'SCENE':
                scenes.append(asset_data)

        assets_library = {
            'characters': characters,
            'props': props,
            'scenes': scenes
        }

        # 获取当前已有的分镜数据
        cursor.execute('''
            SELECT shot_number, voice_character, emotion, intensity, dialogue,
                   fusion_prompt, motion_prompt
            FROM storyboards
            WHERE episode_id = ? AND snapshot_id = ?
            ORDER BY shot_number
        ''', (episode_id, snapshot_id))

        current_shots = []
        for row in cursor.fetchall():
            current_shots.append({
                'shotNumber': row[0],
                'voiceCharacter': row[1],
                'emotion': row[2],
                'intensity': row[3],
                'dialogue': row[4],
                'fusionPrompt': row[5],
                'motionPrompt': row[6]
            })

        if not current_shots:
            return jsonify({'success': False, 'error': '没有找到现有分镜，请先生成分镜'}), 404

        # 使用AI服务优化分镜（支持新的模型标识符和旧的简单名称）
        ai_service = get_ai_service(model_name)
        optimized_storyboards = ai_service.generate_storyboards(
            script_content,
            min_shots=min_shots,
            max_shots=max_shots,
            feedback=feedback,
            current_shots=current_shots,
            assets=assets_library
        )

        # 删除旧分镜
        cursor.execute('DELETE FROM storyboards WHERE episode_id = ? AND snapshot_id = ?',
                      (episode_id, snapshot_id))

        # 插入优化后的分镜
        for sb in optimized_storyboards:
            cursor.execute('''
                INSERT INTO storyboards (
                    episode_id, snapshot_id, shot_number, voice_character,
                    emotion, intensity, asset_mapping, dialogue, fusion_prompt, motion_prompt,
                    generation_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT')
            ''', (
                episode_id,
                snapshot_id,
                sb['shot_number'],
                sb.get('voice_character', ''),
                sb.get('emotion', ''),
                sb.get('intensity', ''),
                sb.get('asset_mapping', ''),
                sb.get('dialogue', ''),
                sb.get('fusion_prompt', ''),
                sb.get('motion_prompt', '')
            ))

        conn.commit()

        # 返回优化后的分镜
        cursor.execute('''
            SELECT id, episode_id, snapshot_id, shot_number, voice_character,
                   emotion, intensity, asset_mapping, dialogue, fusion_prompt, motion_prompt,
                   generation_status, created_at, updated_at
            FROM storyboards
            WHERE episode_id = ? AND snapshot_id = ?
            ORDER BY shot_number
        ''', (episode_id, snapshot_id))

        storyboards = []
        for row in cursor.fetchall():
            storyboards.append({
                'id': row[0],
                'episode_id': row[1],
                'snapshot_id': row[2],
                'shot_number': row[3],
                'voice_character': row[4],
                'emotion': row[5],
                'intensity': row[6],
                'asset_mapping': row[7],
                'dialogue': row[8],
                'fusion_prompt': row[9],
                'motion_prompt': row[10],
                'generation_status': row[11],
                'created_at': row[12],
                'updated_at': row[13]
            })

        return jsonify({'success': True, 'data': {'storyboards': storyboards, 'message': '分镜优化成功'}}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
