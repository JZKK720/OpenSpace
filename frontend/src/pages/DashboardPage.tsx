import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { externalAgentsApi, overviewApi, standaloneAppsApi, type ExternalAgentStatus, type OverviewResponse, type StandaloneAppStatus } from '../api';
import ExternalAgentCard from '../components/ExternalAgentCard';
import MetricCard from '../components/MetricCard';
import EmptyState from '../components/EmptyState';
import SpotlightIcon from '../components/SpotlightIcon';
import { formatDate, formatInstruction, formatPercent } from '../utils/format';

export default function DashboardPage() {
  const { t } = useTranslation();
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agents, setAgents] = useState<ExternalAgentStatus[]>([]);
  const [agentsChecking, setAgentsChecking] = useState(true);
  const [apps, setApps] = useState<StandaloneAppStatus[]>([]);
  const [appsChecking, setAppsChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const overview = await overviewApi.getOverview();
        if (!cancelled) {
          setData(overview);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t('dashboard.failedToLoad'));
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

  useEffect(() => {
    let cancelled = false;
    const loadAgents = async () => {
      try {
        const items = await externalAgentsApi.getExternalAgents();
        if (!cancelled) {
          setAgents(items);
        }
      } catch {
        // non-fatal: agents section shows empty state
      } finally {
        if (!cancelled) {
          setAgentsChecking(false);
        }
      }
    };
    void loadAgents();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadApps = async () => {
      try {
        const items = await standaloneAppsApi.getStandaloneApps();
        if (!cancelled) {
          setApps(items);
        }
      } catch {
        // non-fatal: apps section shows empty state
      } finally {
        if (!cancelled) {
          setAppsChecking(false);
        }
      }
    };
    void loadApps();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <div className="p-6 text-sm text-muted">{t('dashboard.loadingDashboard')}</div>;
  }

  if (error || !data) {
    return <div className="p-6 text-sm text-danger">{error ?? t('dashboard.dashboardUnavailable')}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold font-serif">{t('dashboard.title')}</h1>
      <section className="metrics-row">
        <MetricCard label={t('dashboard.totalSkills')} value={data.skills.summary.total_skills_all} hint={t('dashboard.activeHint', { count: data.skills.summary.total_skills })} />
        <MetricCard label={t('dashboard.avgSkillScore')} value={data.skills.average_score.toFixed(1)} hint={t('dashboard.avgScoreHint')} />
        <MetricCard label={t('dashboard.workflowSessions')} value={data.workflows.total} hint={t('dashboard.recordedUnder', { location: data.health.db_path.includes('.openspace') ? t('dashboard.localRepo') : t('dashboard.workspace') })} />
        <MetricCard label={t('dashboard.workflowSuccess')} value={`${data.workflows.average_success_rate.toFixed(1)}%`} hint={t('dashboard.avgSuccessHint')} />
      </section>

      <section>
        <div className="panel-surface px-4 py-2.5 flex items-center gap-3 text-xs text-muted">
          <span className="uppercase tracking-[0.14em]">{t('dashboard.health')}</span>
          <span className="w-px h-3 bg-[color:var(--color-border)] shrink-0" />
          <span className="font-medium text-ink">{data.health.status}</span>
          <span>·</span>
          <span className="truncate">{data.health.db_path}</span>
          <span className="ml-auto shrink-0">{data.health.workflow_count} {t('dashboard.workflowCount').toLowerCase()}</span>
        </div>
      </section>

      <section>
        <div className="panel-surface p-5 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.agentAppsKicker')}</div>
              {!appsChecking ? (
                <div className="text-xs text-muted mt-1">{t('dashboard.agentAppsCount', { count: apps.length })}</div>
              ) : null}
            </div>
            <Link to="/showcase" className="text-xs text-muted hover:text-ink transition-colors">{t('dashboard.agentAppsViewAll')}</Link>
          </div>

          {appsChecking ? (
            <div className="text-sm text-muted">{t('dashboard.agentAppsChecking')}</div>
          ) : apps.length === 0 ? (
            <EmptyState title={t('dashboard.agentAppsEmptyTitle')} description={t('dashboard.agentAppsEmptyDescription')} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
              {apps.map((app) => {
                const isHarness = app.id === 'openharness';
                const inner = (
                  <div className={`record-card border border-[color:var(--color-border)] bg-[color:var(--color-bg-page)] p-4 space-y-3 h-full transition-opacity ${app.available ? '' : 'opacity-50'}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] border border-[color:var(--color-border)] bg-surface ${app.available ? 'text-primary' : 'text-muted'}`}>
                          <SpotlightIcon icon={app.icon} className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-bold truncate">{app.name}</div>
                          {app.tags.length > 0 ? (
                            <div className="mt-1 flex flex-wrap gap-1">
                              {app.tags.slice(0, 3).map((tag) => (
                                <span key={`${app.id}-${tag}`} className="chip text-xs">{tag}</span>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      </div>
                      <span className={`tag px-2 py-0.5 text-xs shrink-0 ${app.available ? 'text-success' : 'text-muted'}`}>
                        {app.available ? t('showcase.statusLive') : t('showcase.statusDown')}
                      </span>
                    </div>
                    <p className="text-sm text-muted line-clamp-2">{app.description}</p>
                    <div className="flex items-center justify-between gap-2 text-xs text-muted">
                      {app.latencyMs !== null ? <span>{app.latencyMs}ms</span> : <span />}
                      {app.available ? (
                        <span className="font-medium text-primary">{t('dashboard.agentAppsOpen')}</span>
                      ) : (
                        <span>{t('showcase.statusDown')}</span>
                      )}
                    </div>
                  </div>
                );

                if (!app.available) {
                  return <div key={app.id} className="block h-full cursor-not-allowed">{inner}</div>;
                }

                return isHarness ? (
                  <Link key={app.id} to="/harness-agent" className="block h-full">
                    {inner}
                  </Link>
                ) : (
                  <a key={app.id} href={app.publicUrl} target="_blank" rel="noopener noreferrer" className="block h-full">
                    {inner}
                  </a>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <section>
        <div className="panel-surface p-5 space-y-4">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.externalAgentsKicker')}</div>
            {!agentsChecking ? (
              <div className="text-xs text-muted mt-1">{t('dashboard.externalAgentsCount', { count: agents.length })}</div>
            ) : null}
          </div>
          {agentsChecking ? (
            <div className="text-sm text-muted">{t('dashboard.externalAgentsChecking')}</div>
          ) : agents.length === 0 ? (
            <EmptyState title={t('dashboard.externalAgentsEmptyTitle')} description={t('dashboard.externalAgentsEmptyDescription')} />
          ) : (
            <div className="grid grid-cols-2 gap-4 items-start">
              {agents.map((agent) => (
                <ExternalAgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="grid grid-cols-2 gap-6">
        <div className="panel-surface p-5 space-y-4">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.skillsSection')}</div>
            <h2 className="text-2xl font-bold font-serif mt-1">{t('dashboard.topScoredSkills')}</h2>
          </div>
          {data.skills.top.length === 0 ? (
            <EmptyState title={t('dashboard.noSkillsYet')} description={t('dashboard.noSkillsDesc')} />
          ) : (
            <div className="space-y-3">
              {data.skills.top.map((skill) => (
                <Link key={skill.skill_id} to={`/skills/${encodeURIComponent(skill.skill_id)}`} className="record-card block p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="font-bold truncate">{skill.name}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-2xl font-bold font-serif">{skill.score.toFixed(1)}</div>
                      <div className="text-xs text-muted">{t('common.score')}</div>
                    </div>
                  </div>
                  <div className="mt-3 flex gap-3 text-xs text-muted">
                    <span>{t('dashboard.effective', { value: formatPercent(skill.effective_rate) })}</span>
                    <span>{t('dashboard.applied', { value: formatPercent(skill.applied_rate) })}</span>
                    <span>{t('dashboard.selections', { count: skill.total_selections })}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="panel-surface p-5 space-y-4">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.workflowsSection')}</div>
            <h2 className="text-2xl font-bold font-serif mt-1">{t('dashboard.recentSessions')}</h2>
          </div>
          {data.workflows.recent.length === 0 ? (
            <EmptyState title={t('dashboard.noWorkflowSessions')} description={t('dashboard.noWorkflowDesc')} />
          ) : (
            <div className="space-y-3">
              {data.workflows.recent.map((workflow) => (
                <Link key={workflow.id} to={`/workflows/${encodeURIComponent(workflow.id)}`} className="record-card block p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 space-y-1">
                      <div className="font-bold truncate">{workflow.task_name}</div>
                      <div className="text-sm text-muted line-clamp-2">{formatInstruction(workflow.instruction, 160, t('format.noInstruction'))}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-lg font-bold font-serif">{(workflow.success_rate * 100).toFixed(1)}%</div>
                      <div className="text-xs text-muted">{t('common.success')}</div>
                    </div>
                  </div>
                  <div className="mt-3 flex gap-3 text-xs text-muted">
                    <span>{t('common.steps', { count: workflow.total_steps })}</span>
                    <span>{t('common.agentActions', { count: workflow.agent_action_count })}</span>
                    <span>{formatDate(workflow.start_time)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
