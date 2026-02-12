"""
资产管理服务
处理资产拆解、版本管理等业务逻辑
"""
from database.init_db import get_connection
from datetime import datetime
from typing import Dict, List, Optional


class AssetService:
    """资产管理服务类"""

    def __init__(self):
        pass

    def create_version(self, project_id: int, model_used: str,
                      extraction_type: str = 'initial',
                      feedback: Optional[str] = None,
                      episode_id: Optional[int] = None) -> int:
        """
        创建新的资产拆解版本
        自动管理版本数量，最多保留5轮

        Args:
            project_id: 项目ID
            model_used: 使用的AI模型
            extraction_type: 拆解类型 ('initial' 或 'optimization')
            feedback: 优化反馈（可选）
            episode_id: 剧集ID（可选）

        Returns:
            version_id: 新创建的版本ID
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # 1. 检查现有版本数量
            cursor.execute('''
                SELECT COUNT(*) FROM asset_extraction_versions
                WHERE project_id = ?
            ''', (project_id,))
            version_count = cursor.fetchone()[0]

            # 2. 如果已有5个版本，删除最旧的
            if version_count >= 5:
                self._delete_oldest_version(cursor, project_id)

            # 3. 计算新版本号
            cursor.execute('''
                SELECT COALESCE(MAX(version_number), 0) FROM asset_extraction_versions
                WHERE project_id = ?
            ''', (project_id,))
            max_version = cursor.fetchone()[0]
            new_version_number = max_version + 1 if max_version < 5 else 5

            # 4. 创建新版本记录
            cursor.execute('''
                INSERT INTO asset_extraction_versions (
                    project_id, episode_id, version_number, model_used,
                    extraction_type, feedback, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, episode_id, new_version_number, model_used,
                  extraction_type, feedback, datetime.utcnow()))

            version_id = cursor.lastrowid
            conn.commit()

            return version_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _delete_oldest_version(self, cursor, project_id: int):
        """删除最旧的版本及其关联资产"""
        # 查找最旧的版本
        cursor.execute('''
            SELECT id FROM asset_extraction_versions
            WHERE project_id = ?
            ORDER BY created_at ASC
            LIMIT 1
        ''', (project_id,))

        oldest = cursor.fetchone()
        if oldest:
            oldest_version_id = oldest[0]

            # 删除该版本的所有资产
            cursor.execute('''
                DELETE FROM assets
                WHERE version_id = ?
            ''', (oldest_version_id,))

            # 删除版本记录
            cursor.execute('''
                DELETE FROM asset_extraction_versions
                WHERE id = ?
            ''', (oldest_version_id,))

    def update_version_asset_count(self, version_id: int):
        """更新版本的资产数量"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT COUNT(*) FROM assets
                WHERE version_id = ? AND is_deleted = 0
            ''', (version_id,))
            asset_count = cursor.fetchone()[0]

            cursor.execute('''
                UPDATE asset_extraction_versions
                SET asset_count = ?
                WHERE id = ?
            ''', (asset_count, version_id))

            conn.commit()
        finally:
            conn.close()

    def get_version_history(self, project_id: int, limit: int = 5) -> List[Dict]:
        """
        获取项目的版本历史

        Args:
            project_id: 项目ID
            limit: 返回的版本数量限制

        Returns:
            版本历史列表，按创建时间倒序
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT
                    id, version_number, model_used, extraction_type,
                    feedback, asset_count, created_at
                FROM asset_extraction_versions
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (project_id, limit))

            versions = []
            for row in cursor.fetchall():
                versions.append({
                    'id': row[0],
                    'version_number': row[1],
                    'model_used': row[2],
                    'extraction_type': row[3],
                    'feedback': row[4],
                    'asset_count': row[5],
                    'created_at': row[6]
                })

            return versions

        finally:
            conn.close()

    def get_version_assets(self, version_id: int) -> Dict[str, List[Dict]]:
        """
        获取指定版本的所有资产

        Args:
            version_id: 版本ID

        Returns:
            资产字典，包含 characters, props, scenes
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT
                    id, asset_type, name, description,
                    gender, age, voice, role
                FROM assets
                WHERE version_id = ? AND is_deleted = 0
                ORDER BY asset_type, name
            ''', (version_id,))

            assets = {
                'characters': [],
                'props': [],
                'scenes': []
            }

            for row in cursor.fetchall():
                asset = {
                    'id': row[0],
                    'name': row[2],
                    'description': row[3]
                }

                asset_type = row[1]
                if asset_type == 'CHARACTER':
                    asset.update({
                        'gender': row[4],
                        'age': row[5],
                        'voice': row[6],
                        'role': row[7]
                    })
                    assets['characters'].append(asset)
                elif asset_type == 'PROP':
                    assets['props'].append(asset)
                elif asset_type == 'SCENE':
                    assets['scenes'].append(asset)

            return assets

        finally:
            conn.close()

    def get_current_version(self, project_id: int) -> Optional[Dict]:
        """
        获取项目的当前版本（最新版本）

        Args:
            project_id: 项目ID

        Returns:
            当前版本信息，如果没有版本则返回None
        """
        versions = self.get_version_history(project_id, limit=1)
        return versions[0] if versions else None


# 创建全局服务实例
_asset_service = None

def get_asset_service() -> AssetService:
    """获取资产服务单例"""
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service
