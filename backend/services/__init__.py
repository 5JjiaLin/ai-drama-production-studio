"""
AI资产提取服务模块
"""
from .ai_service import AIService, AIModel, get_ai_service
from .deduplication_service import AssetDeduplication, get_deduplication_service

__all__ = [
    'AIService', 'AIModel', 'get_ai_service',
    'AssetDeduplication', 'get_deduplication_service'
]
