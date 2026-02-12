/**
 * 项目管理服务
 */

import { authService } from './authService';

const API_BASE_URL = 'http://127.0.0.1:5000/api';

export interface Project {
  id: number;
  user_id: number;
  name: string;
  description: string;
  status: 'ASSET_BUILDING' | 'ASSET_LOCKED' | 'STORYBOARD_GENERATION' | 'COMPLETED';
  current_snapshot_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectData {
  name: string;
  description?: string;
}

class ProjectService {
  async getProjects(): Promise<Project[]> {
    const response = await authService.fetchWithAuth(`${API_BASE_URL}/projects`);
    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '获取项目列表失败');
    }

    return data.data.projects;
  }

  async getProject(projectId: number): Promise<Project> {
    const response = await authService.fetchWithAuth(`${API_BASE_URL}/projects/${projectId}`);
    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '获取项目详情失败');
    }

    return data.data;
  }

  async createProject(projectData: CreateProjectData): Promise<Project> {
    const response = await authService.fetchWithAuth(`${API_BASE_URL}/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(projectData),
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '创建项目失败');
    }

    return data.data.project;
  }

  async updateProject(projectId: number, projectData: Partial<CreateProjectData>): Promise<void> {
    const response = await authService.fetchWithAuth(`${API_BASE_URL}/projects/${projectId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(projectData),
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '更新项目失败');
    }
  }

  async deleteProject(projectId: number): Promise<void> {
    const response = await authService.fetchWithAuth(`${API_BASE_URL}/projects/${projectId}`, {
      method: 'DELETE',
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '删除项目失败');
    }
  }
}

export const projectService = new ProjectService();
