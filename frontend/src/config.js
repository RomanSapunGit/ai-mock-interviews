export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const API_WS_URL = import.meta.env.VITE_API_WS_URL || API_BASE_URL.replace(/^http/, 'ws');
