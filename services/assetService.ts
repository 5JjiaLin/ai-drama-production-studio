/**
 * 资产管理服务
 */

import { authService } from './authService';

const API_BASE_URL = 'http://127.0.0.1:5000/api';

export interface Asset {
  id: number;
  project_id: number;
  asset_type: 'CHARACTER' | 'PROP' | 'SCENE';
  name: string;
  description: string;
  // 角色专用字段
  gender?: string;
  age?: string;
  voice?: string;
  role?: string;
  // 元数据
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExtractAssetsRequest {
  script_content: string;
  episode_number?: number;
  model?: string;
}

export interface OptimizeAssetsRequest {
  feedback: string;
  model?: string;
}

export interface UpdateAssetRequest {
  name?: string;
  description?: string;
  gender?: string;
  age?: string;
  voice?: string;
  role?: string;
}

class AssetService {
  async getAssets(projectId: number): Promise<Asset[]> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/assets`
    );
    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '获取资产列表失败');
    }

    return data.data.assets;
  }

  async extractAssets(projectId: number, request: ExtractAssetsRequest): Promise<Asset[]> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/extract-assets`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }
    );

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '资产提取失败');
    }

    return data.data.assets;
  }

  async optimizeAssets(projectId: number, request: OptimizeAssetsRequest): Promise<Asset[]> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/extract-assets`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          feedback: request.feedback,
          model: request.model,
        }),
      }
    );

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '资产优化失败');
    }

    return data.data.assets;
  }

  async updateAsset(
    projectId: number,
    assetId: number,
    request: UpdateAssetRequest
  ): Promise<void> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/assets/${assetId}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }
    );

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '更新资产失败');
    }
  }

  async deleteAsset(projectId: number, assetId: number): Promise<void> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/assets/${assetId}`,
      {
        method: 'DELETE',
      }
    );

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '删除资产失败');
    }
  }

  // 导出为CSV
  exportToCSV(assets: Asset[]): string {
    const headers = ['类型', '名称', '描述', '性别', '年龄', '声线', '角色类型'];
    const rows = assets.map(asset => [
      asset.asset_type === 'CHARACTER' ? '角色' : asset.asset_type === 'PROP' ? '道具' : '场景',
      asset.name,
      asset.description,
      asset.gender || '',
      asset.age || '',
      asset.voice || '',
      asset.role || '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
    ].join('\n');

    return csvContent;
  }

  // 复制到剪贴板（返回文本格式）
  copyToClipboard(assets: Asset[]): string {
    const headers = ['类型', '名称', '描述', '性别', '年龄', '声线', '角色类型'];
    const rows = assets.map(asset => [
      asset.asset_type === 'CHARACTER' ? '角色' : asset.asset_type === 'PROP' ? '道具' : '场景',
      asset.name,
      asset.description,
      asset.gender || '',
      asset.age || '',
      asset.voice || '',
      asset.role || '',
    ]);

    return [
      headers.join('\t'),
      ...rows.map(row => row.join('\t')),
    ].join('\n');
  }
}

export const assetService = new AssetService();
