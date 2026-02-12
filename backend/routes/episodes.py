"""
剧集管理路由
"""
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from database.init_db import get_connection
from werkzeug.utils import secure_filename
import os

episodes_bp = Blueprint('episodes', __name__, url_prefix='/api/projects')


def parse_script_file(file):
    """
    解析剧本文件（支持.txt和.docx格式）

    Args:
        file: Flask上传的文件对象

    Returns:
        str: 解析后的文本内容
    """
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()

    if file_ext == '.txt':
        # 读取txt文件
        content = file.read().decode('utf-8')
        return content
    elif file_ext == '.docx':
        # 读取docx文件
        try:
            from docx import Document
            from io import BytesIO

            # 将文件内容读入内存
            file_content = BytesIO(file.read())
            doc = Document(file_content)

            # 提取所有段落的文本
            paragraphs = [para.text for para in doc.paragraphs]
            content = '\n'.join(paragraphs)
            return content
        except ImportError:
            raise ValueError("python-docx库未安装，无法解析.docx文件。请运行: pip install python-docx")
        except Exception as e:
            raise ValueError(f"解析.docx文件失败: {str(e)}")
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}。仅支持.txt和.docx格式")


@episodes_bp.route('/<int:project_id>/episodes/upload', methods=['POST'])
@token_required
def upload_episode(current_user, project_id):
    """上传剧集文件（支持.txt和.docx格式）"""
    conn = None
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'}), 400

        # 获取其他参数
        episode_number = request.form.get('episode_number')
        title = request.form.get('title')  # 标题可选

        if not episode_number:
            return jsonify({'success': False, 'error': '剧集编号不能为空'}), 400

        # 解析文件内容
        try:
            script_content = parse_script_file(file)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        if not script_content or not script_content.strip():
            return jsonify({'success': False, 'error': '文件内容为空'}), 400

        # 如果没有提供标题，自动生成
        if not title:
            title = f"第{episode_number}集"

        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute('''
            SELECT id FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 创建剧集
        cursor.execute('''
            INSERT INTO episodes (project_id, episode_number, title, script_content)
            VALUES (?, ?, ?, ?)
        ''', (project_id, episode_number, title, script_content))

        episode_id = cursor.lastrowid
        conn.commit()

        # 获取创建的剧集
        cursor.execute('''
            SELECT id, project_id, episode_number, title, script_content, upload_status, uploaded_at
            FROM episodes WHERE id = ?
        ''', (episode_id,))

        row = cursor.fetchone()
        episode = {
            'id': row[0],
            'project_id': row[1],
            'episode_number': row[2],
            'title': row[3],
            'script_content': row[4],
            'upload_status': row[5],
            'uploaded_at': row[6]
        }

        return jsonify({'success': True, 'data': {'episode': episode}}), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@episodes_bp.route('/<int:project_id>/episodes', methods=['POST'])
@token_required
def create_episode(current_user, project_id):
    """创建剧集"""
    conn = None
    try:
        data = request.get_json()
        episode_number = data.get('episode_number')
        title = data.get('title')  # 标题可选
        script_content = data.get('script_content')

        if not episode_number or not script_content:
            return jsonify({'success': False, 'error': '剧集编号和剧本内容不能为空'}), 400

        # 如果没有提供标题，自动生成
        if not title:
            title = f"第{episode_number}集"

        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权
        cursor.execute('''
            SELECT id FROM projects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        ''', (project_id, current_user))

        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 创建剧集
        cursor.execute('''
            INSERT INTO episodes (project_id, episode_number, title, script_content)
            VALUES (?, ?, ?, ?)
        ''', (project_id, episode_number, title, script_content))

        episode_id = cursor.lastrowid
        conn.commit()

        # 获取创建的剧集
        cursor.execute('''
            SELECT id, project_id, episode_number, title, script_content, upload_status, uploaded_at
            FROM episodes WHERE id = ?
        ''', (episode_id,))

        row = cursor.fetchone()
        episode = {
            'id': row[0],
            'project_id': row[1],
            'episode_number': row[2],
            'title': row[3],
            'script_content': row[4],
            'upload_status': row[5],
            'uploaded_at': row[6]
        }

        return jsonify({'success': True, 'data': {'episode': episode}}), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@episodes_bp.route('/<int:project_id>/episodes', methods=['GET'])
@token_required
def get_episodes(current_user, project_id):
    """获取项目的剧集列表"""
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

        # 获取剧集列表
        cursor.execute('''
            SELECT id, project_id, episode_number, title, script_content, upload_status, uploaded_at
            FROM episodes
            WHERE project_id = ?
            ORDER BY episode_number
        ''', (project_id,))

        episodes = []
        for row in cursor.fetchall():
            episodes.append({
                'id': row[0],
                'project_id': row[1],
                'episode_number': row[2],
                'title': row[3],
                'script_content': row[4],
                'upload_status': row[5],
                'uploaded_at': row[6]
            })

        return jsonify({'success': True, 'data': {'episodes': episodes}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@episodes_bp.route('/<int:project_id>/episodes/<int:episode_id>', methods=['GET'])
@token_required
def get_episode(current_user, project_id, episode_id):
    """获取剧集详情"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和剧集存在
        cursor.execute('''
            SELECT e.id, e.project_id, e.episode_number, e.title, e.script_content, e.upload_status, e.uploaded_at
            FROM episodes e
            JOIN projects p ON e.project_id = p.id
            WHERE e.id = ? AND e.project_id = ? AND p.user_id = ?
        ''', (episode_id, project_id, current_user))

        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': '剧集不存在'}), 404

        episode = {
            'id': row[0],
            'project_id': row[1],
            'episode_number': row[2],
            'title': row[3],
            'script_content': row[4],
            'upload_status': row[5],
            'uploaded_at': row[6]
        }

        return jsonify({'success': True, 'data': {'episode': episode}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@episodes_bp.route('/<int:project_id>/episodes/<int:episode_id>', methods=['DELETE'])
@token_required
def delete_episode(current_user, project_id, episode_id):
    """删除剧集（硬删除，同时删除关联的分镜）"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 验证项目所有权和剧集存在
        cursor.execute('''
            SELECT e.id, e.title
            FROM episodes e
            JOIN projects p ON e.project_id = p.id
            WHERE e.id = ? AND e.project_id = ? AND p.user_id = ?
        ''', (episode_id, project_id, current_user))

        episode = cursor.fetchone()
        if not episode:
            return jsonify({'success': False, 'error': '剧集不存在'}), 404

        # 删除关联的分镜
        cursor.execute('''
            DELETE FROM storyboards
            WHERE episode_id = ?
        ''', (episode_id,))

        # 删除剧集
        cursor.execute('''
            DELETE FROM episodes
            WHERE id = ?
        ''', (episode_id,))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'剧集 "{episode[1]}" 及其关联分镜已删除'
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
