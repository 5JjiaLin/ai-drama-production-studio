/**
 * 认证服务
 * 处理用户登录、注册、token管理
 */

const API_BASE_URL = 'http://127.0.0.1:5000/api';

interface LoginResponse {
  success: boolean;
  data?: {
    access_token: string;
    refresh_token: string;
    user: {
      id: number;
      username: string;
      email: string;
      full_name: string;
    };
  };
  error?: string;
}

interface RegisterResponse {
  success: boolean;
  data?: {
    access_token: string;
    refresh_token: string;
    user: {
      id: number;
      username: string;
      email: string;
      full_name: string;
    };
  };
  error?: string;
  message?: string;
}

class AuthService {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    // 从localStorage加载token
    this.loadTokens();
  }

  private loadTokens() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  private saveTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  private clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  async login(username: string, password: string): Promise<LoginResponse['data']> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    const data: LoginResponse = await response.json();

    if (!data.success || !data.data) {
      throw new Error(data.error || '登录失败');
    }

    this.saveTokens(data.data.access_token, data.data.refresh_token);
    localStorage.setItem('user', JSON.stringify(data.data.user));

    return data.data;
  }

  async register(
    username: string,
    email: string,
    password: string,
    fullName: string
  ): Promise<RegisterResponse['data']> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        email,
        password,
        full_name: fullName,
      }),
    });

    const data: RegisterResponse = await response.json();

    if (!data.success || !data.data) {
      throw new Error(data.error || '注册失败');
    }

    this.saveTokens(data.data.access_token, data.data.refresh_token);
    localStorage.setItem('user', JSON.stringify(data.data.user));

    return data.data;
  }

  logout() {
    this.clearTokens();
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  getUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  async refreshAccessToken(): Promise<string> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.refreshToken}`,
      },
    });

    const data = await response.json();

    if (!data.success || !data.data) {
      this.clearTokens();
      throw new Error('Token refresh failed');
    }

    this.accessToken = data.data.access_token;
    localStorage.setItem('access_token', data.data.access_token);

    return data.data.access_token;
  }

  async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    if (!this.accessToken) {
      throw new Error('Not authenticated');
    }

    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${this.accessToken}`,
    };

    let response = await fetch(url, { ...options, headers });

    // 如果token过期，尝试刷新
    if (response.status === 401) {
      try {
        await this.refreshAccessToken();
        headers['Authorization'] = `Bearer ${this.accessToken}`;
        response = await fetch(url, { ...options, headers });
      } catch (error) {
        this.clearTokens();
        throw new Error('Session expired, please login again');
      }
    }

    return response;
  }
}

export const authService = new AuthService();
