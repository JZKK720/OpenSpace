import { useEffect, useMemo, useState } from 'react';
import { externalAgentsApi, type ExternalAgentHandoffResponse, type ExternalAgentHistoryResponse, type ExternalAgentStatus } from '../api';
import { useTranslation } from 'react-i18next';
import { formatDate } from '../utils/format';

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
    <div className="record-card p-3 space-y-3">
      {/* Header: name + status */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-bold truncate">{agent.name}</div>
          <div className="text-xs text-muted truncate mt-0.5">{agent.description || agent.healthUrl || t('common.unavailable')}</div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className={`tag px-2 py-0.5 text-xs ${agent.available ? 'text-primary' : 'text-muted'}`}>
            {agent.available ? t('dashboard.externalAgentsReachable') : t('dashboard.externalAgentsUnavailable')}
          </span>
          {agent.latencyMs !== null ? (
            <span className="text-[11px] text-muted">{t('dashboard.externalAgentsLatency', { latency: agent.latencyMs })}</span>
          ) : null}
        </div>
      </div>

      {/* Chat / handoff */}
      {canHandoff ? (
        <div className="space-y-2">
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={t('dashboard.externalAgentsPromptPlaceholder')}
            rows={2}
            className="w-full p-2 text-sm field-surface resize-none"
            disabled={submitting}
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-primary text-xs"
              disabled={submitting || !agent.available || !prompt.trim()}
              onClick={() => { void handleSubmit(); }}
            >
              {submitting ? t('dashboard.externalAgentsSending') : t('dashboard.externalAgentsSend')}
            </button>
            {threadId && canPollHistory ? (
              <button
                type="button"
                className="btn-outline-ink text-xs"
                disabled={refreshing}
                onClick={() => { void handleRefresh(); }}
              >
                {refreshing ? t('dashboard.externalAgentsRefreshing') : t('dashboard.externalAgentsRefresh')}
              </button>
            ) : null}
            {threadId ? (
              <button type="button" className="btn-outline-ink text-xs" onClick={handleReset}>
                {t('dashboard.externalAgentsStartFresh')}
              </button>
            ) : null}
            {agent.publicUrl ? (
              <a className="btn-outline-ink text-xs ml-auto" href={agent.publicUrl} target="_blank" rel="noopener noreferrer">
                {t('dashboard.externalAgentsOpen')}
              </a>
            ) : null}
          </div>
          {error ? <div className="text-xs text-danger">{error}</div> : null}
          {!agent.available ? <div className="text-xs text-muted">{t('dashboard.externalAgentsUnavailableHint')}</div> : null}
        </div>
      ) : null}

      {/* Response */}
      {handoff ? (
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center gap-2 text-muted">
            <span className="font-mono truncate max-w-[22ch]">{handoff.threadId}</span>
            <span className="shrink-0">·</span>
            <span className="shrink-0">{latestTurn?.state || handoffStatus || '…'}</span>
            {latestTurn?.started_at ? (
              <span className="ml-auto shrink-0">{formatDate(latestTurn.completed_at || latestTurn.started_at)}</span>
            ) : null}
          </div>
          {latestResponse ? (
            <pre className="field-surface p-2 text-xs overflow-auto max-h-[140px] whitespace-pre-wrap break-words">{latestResponse}</pre>
          ) : awaitingResponse ? (
            <div className="text-muted">{t('dashboard.externalAgentsAwaitingResponse')}</div>
          ) : null}
        </div>
      ) : null}

      {!agent.available && agent.error && !canHandoff ? (
        <div className="text-xs text-danger">{agent.error}</div>
      ) : null}
    </div>
  );
}