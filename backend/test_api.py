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

    # 测试剧本内容
    script_content = """
【第1场】咖啡馆 - 下午

张三坐在窗边，手里拿着一封泛黄的信件，表情凝重。他是一位30多岁的中年男性，穿着深色西装。

张三：（低声自语）终于找到了...这封信藏了二十年。

李四推门而入，径直走向张三。李四是一位女性侦探，25岁左右，穿着干练的风衣。

李四：找到什么了？
张三：（递过信件）你自己看。

李四接过信件，仔细阅读。信纸上的字迹已经模糊不清。

【第2场】警察局审讯室 - 晚上

审讯室里只有一张桌子和两把椅子，墙上挂着一面镜子。

警官王五走进来，他是一位40岁的老警察，头发已经花白。

王五：说吧，那晚你在哪里？
张三：我已经说过很多遍了，我在家里。
"""

    data = {
        "episode_number": 1,
        "title": "第一集 - 真相浮现",
        "script_content": script_content
    }
    response = requests.post(f"{BASE_URL}/projects/{project_id}/episodes", data=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()
    return result['data']['episode_id'] if result['success'] else None


def test_extract_assets(episode_id):
    """测试AI资产提取"""
    print(f"🤖 测试AI资产提取 (剧集ID: {episode_id})...")
    data = {
        "model": "claude"  # 可选: claude, deepseek, gemini, gpt4
    }
    response = requests.post(f"{BASE_URL}/episodes/{episode_id}/extract-assets", json=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()


def test_get_project_assets(project_id):
    """测试获取项目资产"""
    print(f"📦 测试获取项目{project_id}的资产列表...")
    response = requests.get(f"{BASE_URL}/projects/{project_id}/assets")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()


def test_detect_duplicates(project_id):
    """测试检测重复资产"""
    print(f"🔍 测试检测项目{project_id}的重复资产...")
    response = requests.get(f"{BASE_URL}/projects/{project_id}/assets/duplicates?threshold=0.75")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()
    return result.get('data', {}).get('duplicate_groups', [])


def test_merge_assets(duplicate_groups):
    """测试合并资产"""
    if not duplicate_groups:
        print("⏭️  没有重复资产，跳过合并测试")
        return

    # 取第一组进行测试
    first_group = duplicate_groups[0]
    merge_suggestion = first_group.get('merge_suggestion', {})

    if not merge_suggestion:
        print("⏭️  没有合并建议，跳过合并测试")
        return

    print(f"🔀 测试合并资产...")
    data = {
        "primary_asset_id": merge_suggestion['primary_asset_id'],
        "merge_asset_ids": merge_suggestion['merge_asset_ids']
    }
    print(f"合并数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

    response = requests.post(f"{BASE_URL}/assets/merge", json=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()


def test_project_status_update(project_id):
    """测试更新项目状态"""
    print(f"🔄 测试更新项目{project_id}状态...")

    # 先锁定资产库
    data = {"status": "ASSET_LOCKED"}
    response = requests.put(f"{BASE_URL}/projects/{project_id}/status", json=data)
    print(f"锁定资产库 - 状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()


def test_project_statistics(project_id):
    """测试获取项目统计"""
    print(f"📊 测试获取项目{project_id}统计信息...")
    response = requests.get(f"{BASE_URL}/projects/{project_id}/statistics")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()


def test_project_snapshots(project_id):
    """测试获取项目快照"""
    print(f"📸 测试获取项目{project_id}快照列表...")
    response = requests.get(f"{BASE_URL}/projects/{project_id}/snapshots")
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
        episode_id = test_upload_episode(project_id)

        # 测试获取项目详情
        test_get_project_detail(project_id)

        if episode_id:
            # 测试AI资产提取（需要配置API密钥）
            print("⚠️  提示: AI资产提取需要配置API密钥，请确保.env文件已配置")
            user_input = input("是否测试AI资产提取? (y/n): ")
            if user_input.lower() == 'y':
                test_extract_assets(episode_id)
                # 查看提取的资产
                test_get_project_assets(project_id)

                # 测试去重检测
                print("\n" + "=" * 50)
                print("测试资产去重功能")
                print("=" * 50 + "\n")
                duplicate_groups = test_detect_duplicates(project_id)

                # 测试资产合并
                if duplicate_groups:
                    user_input = input("是否测试资产合并? (y/n): ")
                    if user_input.lower() == 'y':
                        test_merge_assets(duplicate_groups)
                        # 查看合并后的资产
                        test_get_project_assets(project_id)

        # 测试项目管理功能
        print("\n" + "=" * 50)
        print("测试项目管理功能")
        print("=" * 50 + "\n")

        # 项目统计
        test_project_statistics(project_id)

        # 测试状态更新
        user_input = input("是否测试项目状态更新? (y/n): ")
        if user_input.lower() == 'y':
            test_project_status_update(project_id)
            # 查看快照
            test_project_snapshots(project_id)
            # 查看更新后的项目详情
            test_get_project_detail(project_id)

    print("=" * 50)
    print("测试完成！")
    print("=" * 50)
