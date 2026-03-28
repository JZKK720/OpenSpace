import axios from 'axios';
import apiClient from './client';

export interface ExternalAgentStatus {
  id: string;
  name: string;
  description: string;
  kind: string;
  protocol: string;
  capabilities: string[];
  handoffMode: string;
  historyMode: string;
  standaloneAppId: string;
  mcpServerName: string;
  tags: string[];
  publicUrl: string;
  internalUrl: string;
  healthUrl: string;
  actionUrl: string;
  mcpUrl: string;
  hasActionUrl: boolean;
  hasMcpUrl: boolean;
  supportsHandoff: boolean;
  supportsHistory: boolean;
  supportsMcp: boolean;
  available: boolean;
  status: 'up' | 'down';
  statusCode: number;
  latencyMs: number | null;
  error: string | null;
}

export interface ExternalAgentTurn {
  turn_number: number;
  user_input: string | null;
  response: string | null;
  state: string;
  started_at: string | null;
  completed_at: string | null;
  tool_calls: unknown[];
}

export interface ExternalAgentHistoryResponse {
  agentId: string;
  threadId: string;
  hasMore: boolean;
  turns: ExternalAgentTurn[];
  latestTurn: ExternalAgentTurn | null;
}

export interface ExternalAgentHandoffResponse extends ExternalAgentHistoryResponse {
  actionUrl: string;
  messageId: string;
  status: string;
  threadCreated: boolean;
}

interface ExternalAgentsResponse {
  items: ExternalAgentStatus[];
  count: number;
}

interface ExternalAgentHandoffPayload {
  prompt: string;
  threadId?: string;
  timezone?: string;
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

export const externalAgentsApi = {
  async getExternalAgents(): Promise<ExternalAgentStatus[]> {
    try {
      const response = await apiClient.get<ExternalAgentsResponse>('/external-agents');
      return response.data.items || [];
    } catch (error) {
      throw createApiError(error, 'Failed to load connected agents');
    }
  },

  async handoffToAgent(agentId: string, payload: ExternalAgentHandoffPayload): Promise<ExternalAgentHandoffResponse> {
    try {
      const response = await apiClient.post<ExternalAgentHandoffResponse>(`/external-agents/${encodeURIComponent(agentId)}/handoff`, payload);
      return response.data;
    } catch (error) {
      throw createApiError(error, 'Failed to send work to the connected agent');
    }
  },

  async getExternalAgentHistory(agentId: string, threadId: string, limit = 10): Promise<ExternalAgentHistoryResponse> {
    try {
      const response = await apiClient.get<ExternalAgentHistoryResponse>(`/external-agents/${encodeURIComponent(agentId)}/history`, {
        params: { thread_id: threadId, limit },
      });
      return response.data;
    } catch (error) {
      throw createApiError(error, 'Failed to refresh connected agent history');
    }
  },
};