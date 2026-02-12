/**
 * 剧集管理服务
 */

import { authService } from './authService';

const API_BASE_URL = 'http://127.0.0.1:5000/api';

export interface Episode {
  id: number;
  project_id: number;
  episode_number: number;
  title: string;
  script_content: string;
  upload_status: 'UPLOADED' | 'ANALYZING' | 'COMPLETED' | 'FAILED';
  ai_analysis_result?: string;
  uploaded_at: string;
}

export interface CreateEpisodeRequest {
  episode_number: number;
  title: string;
  script_content: string;
}

class EpisodeService {
  async getEpisodes(projectId: number): Promise<Episode[]> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/episodes`
    );
    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '获取剧集列表失败');
    }

    return data.data.episodes;
  }

  async createEpisode(projectId: number, request: CreateEpisodeRequest): Promise<Episode> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/episodes`,
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
      throw new Error(data.error || '创建剧集失败');
    }

    return data.data;
  }

  async getEpisode(projectId: number, episodeId: number): Promise<Episode> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/episodes/${episodeId}`
    );
    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '获取剧集详情失败');
    }

    return data.data;
  }

  async deleteEpisode(projectId: number, episodeId: number): Promise<void> {
    const response = await authService.fetchWithAuth(
      `${API_BASE_URL}/projects/${projectId}/episodes/${episodeId}`,
      {
        method: 'DELETE',
      }
    );

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '删除剧集失败');
    }
  }
}

export const episodeService = new EpisodeService();
