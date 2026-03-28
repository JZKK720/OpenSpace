import type { IncomingHttpHeaders } from 'node:http';
import { getExternalAgentsStatus } from '../lib/externalAgents';

export async function handleExternalAgentsRequest(
  _query: Record<string, string>,
  _body: string,
  _headers: IncomingHttpHeaders,
): Promise<unknown> {
  const items = await getExternalAgentsStatus();
  return {
    items,
    count: items.length,
  };
}