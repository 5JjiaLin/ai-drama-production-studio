"""
风格模板路由
实现风格模板的CRUD功能
"""
from datetime import datetime
from flask import Blueprint, request, jsonify

# 创建蓝图
style_templates_bp = Blueprint('style_templates', __name__, url_prefix='/api/style-templates')


def verify_token():
    """验证token并返回用户ID"""
    from routes.auth import decode_token

    token = None
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return None, '无效的Authorization头'

    if not token:
        return None, '缺少认证token'

    payload, error = decode_token(token)
    if error:
        return None, error

    return payload['user_id'], None


@style_templates_bp.route('', methods=['POST'])
def create_style_template():
    """创建风格模板"""
    from app import get_db

    # 验证token
    user_id, error = verify_token()
    if error:
        return jsonify({'success': False, 'error': error}), 401

    data = request.get_json()

    # 验证必填字段
    required_fields = ['name', 'art_style', 'prompt_template']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field}为必填项'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO style_templates (
                user_id, name, description, art_style, color_tone,
                lighting, camera_angle, mood, prompt_template, negative_prompt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, data['name'], data.get('description', ''),
            data['art_style'], data.get('color_tone', ''),
            data.get('lighting', ''), data.get('camera_angle', ''),
            data.get('mood', ''), data['prompt_template'],
            data.get('negative_prompt', '')
        ))

        template_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': '风格模板创建成功',
            'data': {'id': template_id, 'name': data['name']}
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'error': f'创建风格模板失败: {str(e)}'}), 500


@style_templates_bp.route('', methods=['GET'])
def get_style_templates():
    """获取用户的风格模板列表"""
    from app import get_db

    # 验证token
    user_id, error = verify_token()
    if error:
        return jsonify({'success': False, 'error': error}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, description, art_style, color_tone,
                   lighting, camera_angle, mood, prompt_template,
                   negative_prompt, is_public, usage_count, created_at
            FROM style_templates
            WHERE user_id = ? OR is_public = 1
            ORDER BY created_at DESC
        """, (user_id,))

        templates = []
        for row in cursor.fetchall():
            templates.append({
                'id': row[0], 'name': row[1], 'description': row[2],
                'art_style': row[3], 'color_tone': row[4], 'lighting': row[5],
                'camera_angle': row[6], 'mood': row[7], 'prompt_template': row[8],
                'negative_prompt': row[9], 'is_public': row[10],
                'usage_count': row[11], 'created_at': row[12]
            })

        conn.close()
        return jsonify({'success': True, 'data': {'templates': templates, 'total': len(templates)}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'获取风格模板列表失败: {str(e)}'}), 500


@style_templates_bp.route('/<int:template_id>', methods=['GET'])
def get_style_template(template_id):
    """获取单个风格模板"""
    from app import get_db

    # 验证token
    user_id, error = verify_token()
    if error:
        return jsonify({'success': False, 'error': error}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, name, description, art_style, color_tone,
                   lighting, camera_angle, mood, prompt_template,
                   negative_prompt, is_public, usage_count, created_at
            FROM style_templates
            WHERE id = ? AND (user_id = ? OR is_public = 1)
        """, (template_id, user_id))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'success': False, 'error': '风格模板不存在或无权访问'}), 404

        return jsonify({
            'success': True,
            'data': {
                'id': row[0], 'user_id': row[1], 'name': row[2],
                'description': row[3], 'art_style': row[4], 'color_tone': row[5],
                'lighting': row[6], 'camera_angle': row[7], 'mood': row[8],
                'prompt_template': row[9], 'negative_prompt': row[10],
                'is_public': row[11], 'usage_count': row[12], 'created_at': row[13]
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'获取风格模板失败: {str(e)}'}), 500


@style_templates_bp.route('/<int:template_id>', methods=['PUT'])
def update_style_template(template_id):
    """更新风格模板"""
    from app import get_db

    # 验证token
    user_id, error = verify_token()
    if error:
        return jsonify({'success': False, 'error': error}), 401

    data = request.get_json()

    try:
        conn = get_db()
        cursor = conn.cursor()

        # 验证所有权
        cursor.execute("SELECT id FROM style_templates WHERE id = ? AND user_id = ?",
                      (template_id, user_id))

        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '风格模板不存在或无权修改'}), 404

        # 更新模板
        cursor.execute("""
            UPDATE style_templates
            SET name = ?, description = ?, art_style = ?, color_tone = ?,
                lighting = ?, camera_angle = ?, mood = ?, prompt_template = ?,
                negative_prompt = ?, updated_at = ?
            WHERE id = ?
        """, (
            data.get('name'), data.get('description', ''), data.get('art_style'),
            data.get('color_tone', ''), data.get('lighting', ''),
            data.get('camera_angle', ''), data.get('mood', ''),
            data.get('prompt_template'), data.get('negative_prompt', ''),
            datetime.utcnow(), template_id
        ))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '风格模板更新成功'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'更新风格模板失败: {str(e)}'}), 500


@style_templates_bp.route('/<int:template_id>', methods=['DELETE'])
def delete_style_template(template_id):
    """删除风格模板"""
    from app import get_db

    # 验证token
    user_id, error = verify_token()
    if error:
        return jsonify({'success': False, 'error': error}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        # 验证所有权
        cursor.execute("SELECT id FROM style_templates WHERE id = ? AND user_id = ?",
                      (template_id, user_id))

        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '风格模板不存在或无权删除'}), 404

        # 删除模板
        cursor.execute("DELETE FROM style_templates WHERE id = ?", (template_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '风格模板删除成功'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'删除风格模板失败: {str(e)}'}), 500
