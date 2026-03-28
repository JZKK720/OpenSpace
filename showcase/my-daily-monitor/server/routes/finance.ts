import type { IncomingHttpHeaders } from 'node:http';

export async function handleFinanceRequest(
  _query: Record<string, string>,
  _body: string,
  _headers: IncomingHttpHeaders,
): Promise<unknown> {
  return {
    transactions: [],
  };
}