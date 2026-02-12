"""
资产去重检测服务
使用相似度算法识别可能重复的资产
"""
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
import re


class AssetDeduplication:
    """资产去重检测器"""

    def __init__(self, similarity_threshold: float = 0.8):
        """
        初始化去重检测器

        Args:
            similarity_threshold: 相似度阈值（0-1），默认0.8
        """
        self.similarity_threshold = similarity_threshold

    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        计算名称相似度

        使用SequenceMatcher算法
        """
        if not name1 or not name2:
            return 0.0

        # 统一格式：去除空格、转小写
        name1_normalized = re.sub(r'\s+', '', name1.lower())
        name2_normalized = re.sub(r'\s+', '', name2.lower())

        # 完全相同
        if name1_normalized == name2_normalized:
            return 1.0

        # 计算序列相似度
        return SequenceMatcher(None, name1_normalized, name2_normalized).ratio()

    def calculate_description_similarity(self, desc1: str, desc2: str) -> float:
        """
        计算描述相似度

        使用关键词重叠率
        """
        if not desc1 or not desc2:
            return 0.0

        # 提取关键词（简单分词）
        words1 = set(re.findall(r'[\u4e00-\u9fa5]+|\w+', desc1.lower()))
        words2 = set(re.findall(r'[\u4e00-\u9fa5]+|\w+', desc2.lower()))

        if not words1 or not words2:
            return 0.0

        # Jaccard相似度
        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def calculate_overall_similarity(self, asset1: Dict, asset2: Dict) -> float:
        """
        计算资产整体相似度

        综合名称和描述的相似度
        """
        # 名称相似度权重 0.7
        name_sim = self.calculate_name_similarity(
            asset1.get('name', ''),
            asset2.get('name', '')
        )

        # 描述相似度权重 0.3
        desc_sim = self.calculate_description_similarity(
            asset1.get('description', ''),
            asset2.get('description', '')
        )

        return name_sim * 0.7 + desc_sim * 0.3

    def is_duplicate_asset(self, new_asset: Dict, existing_assets: List[Dict]) -> bool:
        """
        检查新资产是否与现有资产重复

        Args:
            new_asset: 待检查的新资产
            existing_assets: 现有资产列表

        Returns:
            True 如果发现重复，False 否则
        """
        if not existing_assets:
            return False

        new_asset_type = new_asset.get('asset_type')

        # 只与相同类型的资产比较
        for existing_asset in existing_assets:
            if existing_asset.get('asset_type') != new_asset_type:
                continue

            similarity = self.calculate_overall_similarity(new_asset, existing_asset)

            if similarity >= self.similarity_threshold:
                return True

        return False

    def find_duplicates(self, assets: List[Dict]) -> List[Dict]:
        """
        在资产列表中查找可能重复的资产组

        Args:
            assets: 资产列表，每个资产需包含 id, name, description, asset_type

        Returns:
            重复组列表，每组包含:
            {
                "group_id": "角色-张三",
                "asset_type": "CHARACTER",
                "assets": [
                    {
                        "id": 1,
                        "name": "张三",
                        "description": "...",
                        "similarity": 0.95
                    },
                    ...
                ],
                "suggestion": "MERGE" | "KEEP_SEPARATE"
            }
        """
        if not assets:
            return []

        # 按资产类型分组
        assets_by_type = {}
        for asset in assets:
            asset_type = asset.get('asset_type', 'UNKNOWN')
            if asset_type not in assets_by_type:
                assets_by_type[asset_type] = []
            assets_by_type[asset_type].append(asset)

        duplicate_groups = []

        # 对每种类型的资产进行去重检测
        for asset_type, type_assets in assets_by_type.items():
            if len(type_assets) < 2:
                continue

            # 已处理的资产ID集合
            processed = set()

            for i, asset1 in enumerate(type_assets):
                if asset1['id'] in processed:
                    continue

                # 当前组
                current_group = [asset1]
                max_similarity = 0.0

                # 与其他资产比较
                for j, asset2 in enumerate(type_assets):
                    if i == j or asset2['id'] in processed:
                        continue

                    similarity = self.calculate_overall_similarity(asset1, asset2)

                    if similarity >= self.similarity_threshold:
                        current_group.append({
                            **asset2,
                            'similarity': similarity
                        })
                        processed.add(asset2['id'])
                        max_similarity = max(max_similarity, similarity)

                # 如果找到重复组（至少2个资产）
                if len(current_group) > 1:
                    # 添加相似度到第一个资产
                    current_group[0]['similarity'] = 1.0

                    # 生成建议
                    suggestion = "MERGE" if max_similarity >= 0.9 else "REVIEW"

                    duplicate_groups.append({
                        "group_id": f"{asset_type}-{asset1['name']}",
                        "asset_type": asset_type,
                        "assets": current_group,
                        "suggestion": suggestion,
                        "max_similarity": max_similarity
                    })

                    processed.add(asset1['id'])

        return duplicate_groups

    def suggest_merge(self, assets: List[Dict]) -> Dict:
        """
        建议如何合并资产

        选择最详细的描述、最早出现的资产为主资产
        """
        if not assets or len(assets) < 2:
            return {}

        # 按描述长度和首次出现集数排序
        sorted_assets = sorted(
            assets,
            key=lambda x: (
                -len(x.get('description', '')),  # 描述越长越优先
                x.get('first_appeared_episode_id', 999)  # 越早出现越优先
            )
        )

        primary = sorted_assets[0]
        to_merge = sorted_assets[1:]

        return {
            "primary_asset_id": primary['id'],
            "primary_asset_name": primary['name'],
            "merge_asset_ids": [a['id'] for a in to_merge],
            "merged_description": primary.get('description', ''),
            "reason": "选择描述最详细且最早出现的资产作为主资产"
        }


# 单例
_dedup_instance: Optional[AssetDeduplication] = None


def get_deduplication_service(threshold: float = 0.8) -> AssetDeduplication:
    """获取去重服务单例"""
    global _dedup_instance
    if _dedup_instance is None or _dedup_instance.similarity_threshold != threshold:
        _dedup_instance = AssetDeduplication(threshold)
    return _dedup_instance


if __name__ == "__main__":
    # 测试代码
    test_assets = [
        {"id": 1, "name": "张三", "description": "30岁左右的男性，穿着西装", "asset_type": "CHARACTER", "first_appeared_episode_id": 1},
        {"id": 2, "name": "老张", "description": "中年男人，西装革履", "asset_type": "CHARACTER", "first_appeared_episode_id": 2},
        {"id": 3, "name": "李四", "description": "年轻女性侦探", "asset_type": "CHARACTER", "first_appeared_episode_id": 1},
        {"id": 4, "name": "咖啡馆", "description": "市中心的咖啡馆", "asset_type": "SCENE", "first_appeared_episode_id": 1},
        {"id": 5, "name": "咖啡厅", "description": "位于市中心的一家咖啡厅", "asset_type": "SCENE", "first_appeared_episode_id": 3},
    ]

    service = AssetDeduplication(threshold=0.75)
    duplicates = service.find_duplicates(test_assets)

    print("发现的重复组：")
    for group in duplicates:
        print(f"\n组: {group['group_id']}")
        print(f"建议: {group['suggestion']}")
        print(f"最大相似度: {group['max_similarity']:.2f}")
        print("资产:")
        for asset in group['assets']:
            print(f"  - ID:{asset['id']} {asset['name']} (相似度: {asset['similarity']:.2f})")

        # 生成合并建议
        merge_suggestion = service.suggest_merge(group['assets'])
        print(f"合并建议: {merge_suggestion}")
