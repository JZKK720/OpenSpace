import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { standaloneAppsApi, type StandaloneAppStatus } from '../api';
import SpotlightIcon from '../components/SpotlightIcon';
import EmptyState from '../components/EmptyState';
import { useExternalAgentsAvailability } from '../hooks/useExternalAgentsAvailability';
import { useI18n } from '../i18n';

export default function ShowcasePage() {
  const { t } = useI18n();
  const externalAgents = useExternalAgentsAvailability();
  const [apps, setApps] = useState<StandaloneAppStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const items = await standaloneAppsApi.getStandaloneApps();
        if (!cancelled) {
          setApps(items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t('showcase.unavailable'));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [t]);

  const liveAppsCount = useMemo(() => apps.filter((app) => app.available).length, [apps]);

  if (loading) {
    return <div className="p-6 text-sm text-muted">{t('showcase.loading')}</div>;
  }

  if (error) {
    return <div className="p-6 text-sm text-danger">{error ?? t('showcase.unavailable')}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <section className="panel-surface p-6 lg:p-8 space-y-6">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-4">
            <div className="kicker">{t('showcase.kicker')}</div>
            <h1 className="text-4xl font-bold font-serif">{t('showcase.title')}</h1>
            <div className="flex flex-wrap gap-3">
              <Link className="btn-outline-ink text-sm" to="/dashboard">
                {t('showcase.backToDashboard')}
              </Link>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 xl:min-w-[34rem]">
            <div className="panel-subtle bg-[color:var(--color-bg-page)] p-4 space-y-1">
              <div className="text-xs uppercase tracking-[0.14em] text-muted">{t('showcase.appsMetric')}</div>
              <div className="text-3xl font-bold font-serif">{apps.length}</div>
            </div>
            <div className="panel-subtle bg-[color:var(--color-bg-page)] p-4 space-y-1">
              <div className="text-xs uppercase tracking-[0.14em] text-muted">{t('showcase.liveMetric')}</div>
              <div className="text-3xl font-bold font-serif">{liveAppsCount}</div>
            </div>
            <div className="panel-subtle bg-[color:var(--color-bg-page)] p-4 space-y-1">
              <div className="text-xs uppercase tracking-[0.14em] text-muted">{t('showcase.externalMetric')}</div>
              <div className="text-3xl font-bold font-serif">{externalAgents.agents.length}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="panel-surface p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('showcase.appsKicker')}</div>
            <h2 className="text-2xl font-bold font-serif mt-1">{t('showcase.appsTitle')}</h2>
          </div>
          <div className="text-sm text-muted">{t('showcase.appsCountSummary', { live: liveAppsCount, total: apps.length })}</div>
        </div>

        {apps.length === 0 ? (
          <EmptyState title={t('showcase.appsEmptyTitle')} description={t('showcase.appsEmptyDescription')} />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
            {apps.map((app) => (
              <article key={app.id} className="record-card border border-[color:var(--color-border)] bg-[color:var(--color-bg-page)] p-5 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex min-w-0 items-center gap-4">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] border border-[color:var(--color-border)] bg-surface text-primary">
                      <SpotlightIcon icon={app.icon} className="h-7 w-7" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-bold text-xl truncate">{app.name}</div>
                      {app.tags.length > 0 ? (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {app.tags.map((tag) => (
                            <span key={`${app.id}-${tag}`} className="chip text-xs">{tag}</span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                  <span className="tag px-3 py-1 text-xs">
                    {app.available ? t('showcase.statusLive') : t('showcase.statusDown')}
                  </span>
                </div>

                <div className="grid gap-2 text-sm">
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-muted">{t('showcase.appUrl')}</span>
                    <span className="text-right break-all">{app.publicUrl || t('common.unavailable')}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-muted">{t('showcase.appHealth')}</span>
                    <span>{app.available ? t('showcase.monitorHealthy') : t('showcase.monitorUnhealthy')}</span>
                  </div>
                  {app.latencyMs !== null ? (
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-muted">{t('showcase.appLatency')}</span>
                      <span>{app.latencyMs}ms</span>
                    </div>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-3">
                  {app.publicUrl ? (
                    <a
                      className="btn-primary text-sm"
                      href={app.publicUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {t('showcase.openApp')}
                    </a>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel-surface p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('showcase.agentsKicker')}</div>
            <h2 className="text-2xl font-bold font-serif mt-1">{t('showcase.agentsTitle')}</h2>
          </div>
          <div className="text-sm text-muted">
            {externalAgents.checking ? t('showcase.agentsChecking') : t('showcase.agentsCount', { count: externalAgents.agents.length })}
          </div>
        </div>

        {externalAgents.agents.length === 0 ? (
          externalAgents.checking ? (
            <div className="text-sm text-muted">{t('showcase.agentsChecking')}</div>
          ) : (
            <EmptyState
              title={t('showcase.agentsEmptyTitle')}
              description={t('showcase.agentsEmptyDescription')}
            />
          )
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {externalAgents.agents.map((agent) => (
              <div key={agent.id} className="record-card border border-[color:var(--color-border)] p-4 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px] border border-[color:var(--color-border)] bg-[color:var(--color-bg-page)] text-accent">
                      <SpotlightIcon icon="bot" className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 space-y-2">
                      <div className="font-bold truncate">{agent.name}</div>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2 text-xs text-muted">
                    {agent.latencyMs !== null ? <span>{agent.latencyMs}ms</span> : null}
                    <span className="tag px-3 py-1 text-xs">
                      {agent.available ? t('showcase.statusLive') : t('showcase.statusDown')}
                    </span>
                  </div>
                </div>

                <div className="min-w-0 space-y-2">
                  <div className="flex flex-wrap gap-2">
                    {agent.tags.map((tag) => (
                      <span key={`${agent.id}-${tag}`} className="chip text-xs">{tag}</span>
                    ))}
                  </div>

                  <div className="grid gap-2 text-sm">
                    <div className="flex items-start justify-between gap-4">
                      <span className="text-muted">{t('showcase.appUrl')}</span>
                      <span className="text-right break-all">{agent.publicUrl || t('common.unavailable')}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-muted">{t('showcase.appHealth')}</span>
                      <span>{agent.available ? t('showcase.monitorHealthy') : t('showcase.monitorUnhealthy')}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    {agent.publicUrl ? (
                      <a
                        className="btn-outline-ink text-xs"
                        href={agent.publicUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {t('showcase.openAgent')}
                      </a>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}