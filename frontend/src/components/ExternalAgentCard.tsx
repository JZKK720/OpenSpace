import { useEffect, useMemo, useState } from 'react';
import { externalAgentsApi, type ExternalAgentHandoffResponse, type ExternalAgentHistoryResponse, type ExternalAgentStatus } from '../api';
import { useTranslation } from 'react-i18next';
import { formatDate, truncate } from '../utils/format';

interface ExternalAgentCardProps {
  agent: ExternalAgentStatus;
}

const ACTIVE_TURN_STATES = new Set(['pending', 'queued', 'processing', 'running', 'in_progress']);

function isTurnActive(state?: string | null) {
  return ACTIVE_TURN_STATES.has(String(state || '').trim().toLowerCase());
}

export default function ExternalAgentCard({ agent }: ExternalAgentCardProps) {
  const { t } = useTranslation();
  const [prompt, setPrompt] = useState('');
  const [handoff, setHandoff] = useState<ExternalAgentHandoffResponse | ExternalAgentHistoryResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canHandoff = agent.supportsHandoff;
  const canPollHistory = agent.supportsHistory;

  const latestTurn = handoff?.latestTurn ?? null;
  const threadId = handoff?.threadId ?? null;
  const awaitingResponse = isTurnActive(latestTurn?.state);
  const handoffStatus = handoff && 'status' in handoff ? handoff.status : null;

  useEffect(() => {
    if (!canPollHistory || !threadId || !awaitingResponse) {
      return undefined;
    }

    let active = true;
    const intervalId = window.setInterval(() => {
      void externalAgentsApi.getExternalAgentHistory(agent.id, threadId)
        .then((history) => {
          if (!active) {
            return;
          }
          setHandoff(history);
        })
        .catch((pollError) => {
          if (!active) {
            return;
          }
          const message = pollError instanceof Error ? pollError.message : t('dashboard.externalAgentsRefreshFailed');
          setError(message);
        });
    }, 4000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [agent.id, awaitingResponse, canPollHistory, t, threadId]);

  const latestResponse = useMemo(() => {
    const response = latestTurn?.response;
    return typeof response === 'string' ? response.trim() : '';
  }, [latestTurn?.response]);

  const handleSubmit = async () => {
    if (!canHandoff) {
      setError(t('dashboard.externalAgentsSubmitFailed'));
      return;
    }

    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) {
      setError(t('dashboard.externalAgentsPromptRequired'));
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const result = await externalAgentsApi.handoffToAgent(agent.id, {
        prompt: trimmedPrompt,
        threadId: handoff?.threadId,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      });
      setHandoff(result);
      setPrompt('');
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t('dashboard.externalAgentsSubmitFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRefresh = async () => {
    if (!canPollHistory || !threadId) {
      return;
    }

    setRefreshing(true);
    setError(null);

    try {
      const history = await externalAgentsApi.getExternalAgentHistory(agent.id, threadId);
      setHandoff(history);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : t('dashboard.externalAgentsRefreshFailed'));
    } finally {
      setRefreshing(false);
    }
  };

  const handleReset = () => {
    setHandoff(null);
    setError(null);
  };

  return (
    <div className="record-card p-4 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2 min-w-0">
          <div className="font-bold text-xl truncate">{agent.name}</div>
          <div className="text-sm text-muted max-w-[56ch]">{agent.description || agent.publicUrl || agent.healthUrl || t('common.unavailable')}</div>
          <div className="flex flex-wrap gap-2">
            <span className="tag px-3 py-1 text-xs text-muted">{agent.kind}</span>
            <span className={`tag px-3 py-1 text-xs ${agent.available ? '' : 'text-muted'}`}>
              {agent.available ? t('dashboard.externalAgentsReachable') : t('dashboard.externalAgentsUnavailable')}
            </span>
            {threadId ? (
              <span className="tag px-3 py-1 text-xs text-muted">{t('dashboard.externalAgentsThreadActive')}</span>
            ) : null}
          </div>
        </div>
        <div className="text-right shrink-0 text-xs text-muted space-y-1">
          <div>{agent.statusCode ? t('dashboard.externalAgentsStatusCode', { status: agent.statusCode }) : t('dashboard.externalAgentsNoProbe')}</div>
          <div>{agent.latencyMs !== null ? t('dashboard.externalAgentsLatency', { latency: agent.latencyMs }) : t('dashboard.externalAgentsNoProbe')}</div>
        </div>
      </div>

      {agent.tags.length > 0 ? (
        <div className="showcase-chip-row">
          {agent.tags.map((tag) => (
            <span key={`${agent.id}-${tag}`} className="chip">{tag}</span>
          ))}
        </div>
      ) : null}

      <div className="space-y-2 text-sm">
        <div className="flex items-start justify-between gap-4">
          <span className="text-muted">{t('dashboard.externalAgentsHealth')}</span>
          <span className="text-right break-all">{agent.healthUrl || t('common.unavailable')}</span>
        </div>
        {agent.hasActionUrl ? (
          <div className="flex items-start justify-between gap-4">
            <span className="text-muted">{t('dashboard.externalAgentsAction')}</span>
            <span className="text-right break-all">{agent.actionUrl}</span>
          </div>
        ) : null}
        {agent.hasMcpUrl ? (
          <div className="flex items-start justify-between gap-4">
            <span className="text-muted">{t('dashboard.externalAgentsMcp')}</span>
            <span className="text-right break-all">{agent.mcpUrl}</span>
          </div>
        ) : null}
      </div>

      {canHandoff ? (
        <div className="panel-subtle p-4 space-y-3 bg-[color:var(--color-bg-page)]">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.externalAgentsHandoffKicker')}</div>
            <div className="font-bold mt-1">{t('dashboard.externalAgentsHandoffTitle')}</div>
          </div>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={t('dashboard.externalAgentsPromptPlaceholder')}
            rows={4}
            className="w-full p-3 field-surface resize-y min-h-[112px]"
          />
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="btn-primary text-sm"
              disabled={submitting || !agent.available || !canHandoff}
              onClick={() => { void handleSubmit(); }}
            >
              {submitting ? t('dashboard.externalAgentsSending') : t('dashboard.externalAgentsSend')}
            </button>
            {threadId && canPollHistory ? (
              <button
                type="button"
                className="btn-outline-ink text-sm"
                disabled={refreshing}
                onClick={() => { void handleRefresh(); }}
              >
                {refreshing ? t('dashboard.externalAgentsRefreshing') : t('dashboard.externalAgentsRefresh')}
              </button>
            ) : null}
            {threadId ? (
              <button
                type="button"
                className="btn-outline-ink text-sm"
                onClick={handleReset}
              >
                {t('dashboard.externalAgentsStartFresh')}
              </button>
            ) : null}
          </div>
          {!agent.available ? <div className="text-xs text-muted">{t('dashboard.externalAgentsUnavailableHint')}</div> : null}
          {error ? <div className="text-xs text-danger">{error}</div> : null}

          {handoff ? (
            <div className="space-y-3 text-sm">
              <div className="grid gap-2 md:grid-cols-2">
                <div className="field-surface p-3 space-y-1">
                  <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.externalAgentsThread')}</div>
                  <div className="font-mono text-xs break-all">{handoff.threadId}</div>
                </div>
                <div className="field-surface p-3 space-y-1">
                  <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.externalAgentsLatestState')}</div>
                  <div>{latestTurn?.state || handoffStatus || t('common.unavailable')}</div>
                </div>
              </div>
              {latestTurn?.started_at ? (
                <div className="text-xs text-muted">{t('dashboard.externalAgentsUpdatedAt', { time: formatDate(latestTurn.completed_at || latestTurn.started_at) })}</div>
              ) : null}
              {latestTurn?.user_input ? (
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.externalAgentsLatestPrompt')}</div>
                  <div>{truncate(latestTurn.user_input, 220)}</div>
                </div>
              ) : null}
              {latestResponse ? (
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.externalAgentsLatestResponse')}</div>
                  <pre className="field-surface p-3 text-xs overflow-auto max-h-[220px] whitespace-pre-wrap break-words">{latestResponse}</pre>
                </div>
              ) : awaitingResponse ? (
                <div className="text-xs text-muted">{t('dashboard.externalAgentsAwaitingResponse')}</div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        {agent.publicUrl ? (
          <a
            className="btn-outline-ink text-sm"
            href={agent.publicUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t('dashboard.externalAgentsOpen')}
          </a>
        ) : null}
        {!agent.available && agent.error ? <div className="text-xs text-danger">{agent.error}</div> : null}
      </div>
    </div>
  );
}