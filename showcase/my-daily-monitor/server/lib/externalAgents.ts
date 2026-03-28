import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { probeHttpUrl } from './probe';

interface ExternalAgentConfigEntry {
  id?: string;
  name?: string;
  description?: string;
  kind?: string;
  tags?: string[];
  public_url?: string;
  public_url_env?: string;
  internal_url?: string;
  internal_url_env?: string;
  health_url?: string;
  health_url_env?: string;
  action_url?: string;
  action_url_env?: string;
  mcp_url?: string;
  mcp_url_env?: string;
}

interface ExternalAgentRegistry {
  version?: number;
  agents?: ExternalAgentConfigEntry[];
}

export interface ExternalAgentStatus {
  id: string;
  name: string;
  description: string;
  kind: string;
  tags: string[];
  publicUrl: string;
  internalUrl: string;
  healthUrl: string;
  actionUrl: string;
  mcpUrl: string;
  hasActionUrl: boolean;
  hasMcpUrl: boolean;
  available: boolean;
  status: 'up' | 'down';
  statusCode: number;
  latencyMs: number | null;
  error: string | null;
}

export async function getExternalAgentsStatus(): Promise<ExternalAgentStatus[]> {
  const registry = loadRegistry();
  const agents = Array.isArray(registry.agents) ? registry.agents : [];

  const statuses = await Promise.all(
    agents
      .map(resolveAgent)
      .filter((agent): agent is Omit<ExternalAgentStatus, 'available' | 'status' | 'statusCode' | 'latencyMs' | 'error'> => Boolean(agent))
      .map(async (agent) => {
        const probeUrl = agent.healthUrl || agent.internalUrl || agent.publicUrl;
        if (!probeUrl) {
          return {
            ...agent,
            available: false,
            status: 'down' as const,
            statusCode: 0,
            latencyMs: null,
            error: 'No probe URL configured',
          };
        }

        const probe = await probeHttpUrl(probeUrl, 5000);
        return {
          ...agent,
          available: probe.ok,
          status: probe.ok ? 'up' as const : 'down' as const,
          statusCode: probe.status,
          latencyMs: probe.latencyMs,
          error: probe.error ?? null,
        };
      })
  );

  return statuses;
}

function resolveAgent(entry: ExternalAgentConfigEntry): Omit<ExternalAgentStatus, 'available' | 'status' | 'statusCode' | 'latencyMs' | 'error'> | null {
  const id = `${entry.id || ''}`.trim();
  if (!id) return null;

  const publicUrl = resolveUrl(entry, 'public_url');
  const internalUrl = resolveUrl(entry, 'internal_url') || publicUrl;
  const healthUrl = resolveUrl(entry, 'health_url') || internalUrl || publicUrl;
  const actionUrl = resolveUrl(entry, 'action_url') || publicUrl;
  const mcpUrl = resolveUrl(entry, 'mcp_url');

  return {
    id,
    name: `${entry.name || id.replace(/-/g, ' ')}`.trim(),
    description: `${entry.description || ''}`.trim(),
    kind: `${entry.kind || 'external-agent'}`.trim(),
    tags: Array.isArray(entry.tags) ? entry.tags.filter(Boolean).map((tag) => `${tag}`.trim()).filter(Boolean) : [],
    publicUrl,
    internalUrl,
    healthUrl,
    actionUrl,
    mcpUrl,
    hasActionUrl: Boolean(actionUrl),
    hasMcpUrl: Boolean(mcpUrl),
  };
}

function resolveUrl(entry: ExternalAgentConfigEntry, key: 'public_url' | 'internal_url' | 'health_url' | 'action_url' | 'mcp_url'): string {
  const envKey = `${entry[`${key}_env` as keyof ExternalAgentConfigEntry] || ''}`.trim();
  if (envKey) {
    const envValue = `${process.env[envKey] || ''}`.trim();
    if (envValue) return envValue;
  }

  return `${entry[key] || ''}`.trim();
}

function loadRegistry(): ExternalAgentRegistry {
  const configPath = resolveConfigPath();
  if (!configPath) return {};

  try {
    return JSON.parse(readFileSync(configPath, 'utf-8')) as ExternalAgentRegistry;
  } catch {
    return {};
  }
}

function resolveConfigPath(): string | null {
  const candidates = [
    process.env.OPENSPACE_EXTERNAL_AGENTS_CONFIG,
    join(process.cwd(), 'openspace', 'config', 'external_agents.json'),
    join(process.cwd(), '..', '..', 'openspace', 'config', 'external_agents.json'),
  ].filter((candidate): candidate is string => Boolean(candidate));

  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }

  return null;
}