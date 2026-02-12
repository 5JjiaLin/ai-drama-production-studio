"""
模型配置路由
"""
from flask import Blueprint, jsonify
from services.ai_service import get_available_models

models_bp = Blueprint('models', __name__, url_prefix='/api/models')


@models_bp.route('', methods=['GET'])
def get_models():
    """获取所有可用的AI模型配置"""
    try:
        models = get_available_models()
        return jsonify({'success': True, 'data': {'models': models}}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
