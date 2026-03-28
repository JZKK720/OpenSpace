import type { IncomingHttpHeaders } from 'node:http';
import { handleCalendarRequest } from './calendar';
import { handleEmailRequest } from './email';
import { handleExternalAgentsRequest } from './externalAgents';
import { handleFeishuRequest } from './feishu';
import { handleFinanceRequest } from './finance';
import { handleGithubRequest } from './github';
import { handleHealthRequest } from './health';
import { handleNewsRequest } from './news';
import { handleOfficeRequest } from './office';
import { handleSocialRequest } from './social';
import { handleStockRequest } from './stock';
import { handleSystemRequest } from './system';

export type RouteHandler = (
  query: Record<string, string>,
  body: string,
  headers: IncomingHttpHeaders,
) => Promise<unknown>;

export const routeHandlers: Record<string, RouteHandler> = {
  '/api/calendar': handleCalendarRequest,
  '/api/emails': handleEmailRequest,
  '/api/external-agents': handleExternalAgentsRequest,
  '/api/feishu': handleFeishuRequest,
  '/api/finance': handleFinanceRequest,
  '/api/github': handleGithubRequest,
  '/api/health': handleHealthRequest,
  '/api/news': handleNewsRequest,
  '/api/office': handleOfficeRequest,
  '/api/social': handleSocialRequest,
  '/api/stocks': handleStockRequest,
  '/api/system': handleSystemRequest,
};