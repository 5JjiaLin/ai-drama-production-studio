"""
后端API测试脚本
"""
import requests
import json

BASE_URL = "http://localhost:5000/api"


def test_health():
    """测试健康检查"""
    print("📡 测试健康检查...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()


def test_create_project():
    """测试创建项目"""
    print("📝 测试创建项目...")
    data = {
        "name": "测试项目-西游记",
        "description": "这是一个测试项目"
    }
    response = requests.post(f"{BASE_URL}/projects", json=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()
    return result['data']['id'] if result['success'] else None


def test_get_projects():
    """测试获取项目列表"""
    print("📋 测试获取项目列表...")
    response = requests.get(f"{BASE_URL}/projects")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()


def test_upload_episode(project_id):
    """测试上传剧集"""
    print(f"📤 测试上传剧集到项目{project_id}...")
    data = {
        "episode_number": 1,
        "title": "第一集",
        "script_content": "这是第一集的剧本内容..."
    }
    response = requests.post(f"{BASE_URL}/projects/{project_id}/episodes", data=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()


def test_get_project_detail(project_id):
    """测试获取项目详情"""
    print(f"🔍 测试获取项目{project_id}详情...")
    response = requests.get(f"{BASE_URL}/projects/{project_id}")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("开始测试后端API")
    print("=" * 50)
    print()

    # 测试健康检查
    test_health()

    # 测试创建项目
    project_id = test_create_project()

    # 测试获取项目列表
    test_get_projects()

    if project_id:
        # 测试上传剧集
        test_upload_episode(project_id)

        # 测试获取项目详情
        test_get_project_detail(project_id)

    print("=" * 50)
    print("测试完成！")
    print("=" * 50)
