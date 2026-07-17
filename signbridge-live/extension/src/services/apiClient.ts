import axios, { AxiosInstance } from 'axios';

class ApiClient {
  private instance: AxiosInstance;

  constructor() {
    this.instance = axios.create({
      timeout: 10000, // 10 seconds timeout
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add interceptors for token injection and error handling
    this.instance.interceptors.request.use(
      async (config) => {
        // Read API key or token from chrome.storage
        if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
          const { apiKey } = await chrome.storage.local.get('apiKey');
          if (apiKey && config.headers) {
            config.headers['Authorization'] = `Bearer ${apiKey}`;
          }
          
          const { backendUrl } = await chrome.storage.local.get('backendUrl');
          if (backendUrl) {
            config.baseURL = backendUrl;
          }
        }
        
        if (!config.baseURL) {
          config.baseURL = 'http://localhost:8000';
        }
        
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.instance.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        
        // Simple retry logic on network errors or 5xx responses (up to 3 retries)
        if (
          error.code === 'ECONNABORTED' ||
          !error.response ||
          (error.response.status >= 500 && error.response.status <= 599)
        ) {
          originalRequest._retryCount = originalRequest._retryCount || 0;
          if (originalRequest._retryCount < 3) {
            originalRequest._retryCount += 1;
            // Backoff delay: 1s, 2s, 4s
            const delay = Math.pow(2, originalRequest._retryCount) * 500;
            await new Promise((resolve) => setTimeout(resolve, delay));
            return this.instance(originalRequest);
          }
        }
        
        return Promise.reject(error);
      }
    );
  }

  public getClient(): AxiosInstance {
    return this.instance;
  }
}

export const apiClient = new ApiClient().getClient();
export default apiClient;
