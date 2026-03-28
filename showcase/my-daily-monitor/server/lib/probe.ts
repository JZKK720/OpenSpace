export interface HttpProbeResult {
  url: string;
  status: number;
  ok: boolean;
  latencyMs: number;
  error?: string;
}

export async function probeHttpUrl(url: string, timeoutMs: number): Promise<HttpProbeResult> {
  const probeOnce = async (method: 'HEAD' | 'GET'): Promise<HttpProbeResult> => {
    const start = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        signal: controller.signal,
        method,
        headers: { 'User-Agent': 'AgentsMonitor/1.0' },
      });

      const reachable = response.status >= 200 && response.status < 500;
      return {
        url,
        status: response.status,
        ok: reachable,
        latencyMs: Date.now() - start,
      };
    } finally {
      clearTimeout(timeout);
    }
  };

  try {
    const headResult = await probeOnce('HEAD');
    if (headResult.ok || ![405, 501].includes(headResult.status)) {
      return headResult;
    }

    return await probeOnce('GET');
  } catch (err: any) {
    return { url, status: 0, ok: false, latencyMs: timeoutMs, error: err.message };
  }
}