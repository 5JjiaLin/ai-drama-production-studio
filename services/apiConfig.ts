// API配置模块
let globalApiKey = '';
let globalBaseUrl = '/api'; // 使用Vite代理

export const setApiConfig = (apiKey: string, baseUrl?: string) => {
  globalApiKey = apiKey;
  if (baseUrl) globalBaseUrl = baseUrl;
};

export const getApiConfig = () => ({
  apiKey: globalApiKey,
  baseUrl: globalBaseUrl
});
