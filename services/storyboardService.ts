/**
 * 分镜管理服务
 */

import { authService } from './authService';

const API_BASE_URL = 'http://127.0.0.1:5000/api';

export interface Storyboard {
  id: number;
  episode_id: number;
  snapshot_id: number;
  shot_number: number;
  voice_character: string;
  emotion: string;
  intensity: string;
  asset_mapping: string;  // 场景角色道具(@MAPPING)
  dialogue: string;
  fusion_prompt: string;
  motion_prompt: string;
  generation_status: 'DRAFT' | 'GENERATED' | 'APPROVED';
  created_at: string;
  updated_at: string;
}

export interface GenerateStoryboardRequest {
  episode_id: number;
  min_shots?: number;
  max_shots?: number;
  model?: string;
  style_preferences?: string;
}

export interface UpdateStoryboardRequest {
  voice_character?: string;
  emotion?: string;
  intensity?: string;
  dialogue?: string;
  fusion_prompt?: string;
  motion_prompt?: string;
}

class StoryboardService {
  async getStoryboards(projectId: number, episodeId: number): Promise<Storyboard[]> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/episodes/${episodeId}/storyboards`
    );
    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '获取分镜列表失败');
    }

    return data.data.storyboards;
  }

  async generateStoryboards(
    projectId: number,
    request: GenerateStoryboardRequest
  ): Promise<Storyboard[]> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/generate-storyboards`,
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
      throw new Error(data.error || '生成分镜失败');
    }

    return data.data.storyboards;
  }

  async updateStoryboard(
    projectId: number,
    episodeId: number,
    storyboardId: number,
    request: UpdateStoryboardRequest
  ): Promise<void> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/episodes/${episodeId}/storyboards/${storyboardId}`,
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
      throw new Error(data.error || '更新分镜失败');
    }
  }

  async deleteStoryboard(
    projectId: number,
    episodeId: number,
    storyboardId: number
  ): Promise<void> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/episodes/${episodeId}/storyboards/${storyboardId}`,
      {
        method: 'DELETE',
      }
    );

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '删除分镜失败');
    }
  }

  // 导出为CSV
  exportToCSV(storyboards: Storyboard[]): string {
    const headers = ['序号', '配音角色', '情绪', '强度', '场景角色道具', '文案', '关键帧提示词', '动态提示词'];
    const rows = storyboards.map(sb => [
      sb.shot_number,
      sb.voice_character,
      sb.emotion,
      sb.intensity,
      sb.asset_mapping,
      sb.dialogue,
      sb.fusion_prompt,
      sb.motion_prompt,
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
    ].join('\n');

    return csvContent;
  }

  // 复制到剪贴板
  copyToClipboard(storyboards: Storyboard[]): string {
    const headers = ['序号', '配音角色', '情绪', '强度', '场景角色道具', '文案', '关键帧提示词', '动态提示词'];
    const rows = storyboards.map(sb => [
      sb.shot_number,
      sb.voice_character,
      sb.emotion,
      sb.intensity,
      sb.asset_mapping,
      sb.dialogue,
      sb.fusion_prompt,
      sb.motion_prompt,
    ]);

    return [
      headers.join('\t'),
      ...rows.map(row => row.join('\t')),
    ].join('\n');
  }
}

export const storyboardService = new StoryboardService();
