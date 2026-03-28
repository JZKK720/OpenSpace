import axios from 'axios';
import apiClient from './client';

export interface StandaloneAppStatus {
  id: string;
  name: string;
  description: string;
  kind: string;
  icon: string;
  tags: string[];
  publicUrl: string;
  internalUrl: string;
  healthUrl: string;
  available: boolean;
  status: 'up' | 'down';
  statusCode: number;
  latencyMs: number | null;
  error: string | null;
}

interface StandaloneAppsResponse {
  items: StandaloneAppStatus[];
  count: number;
}

function createApiError(error: unknown, fallback: string): Error {
  if (axios.isAxiosError(error)) {
    const apiMessage = (error.response?.data as { error?: string } | undefined)?.error;
    return new Error(apiMessage || error.message || fallback);
  }
  if (error instanceof Error) {
    return error;
  }
  return new Error(fallback);
}

export const standaloneAppsApi = {
  async getStandaloneApps(): Promise<StandaloneAppStatus[]> {
    try {
      const response = await apiClient.get<StandaloneAppsResponse>('/standalone-apps');
      return response.data.items || [];
    } catch (error) {
      throw createApiError(error, 'Failed to load standalone apps');
    }
  },

  async getStandaloneApp(appId: string): Promise<StandaloneAppStatus> {
    try {
      const response = await apiClient.get<StandaloneAppStatus>(`/standalone-apps/${encodeURIComponent(appId)}`);
      return response.data;
    } catch (error) {
      throw createApiError(error, 'Failed to load standalone app status');
    }
  },
};