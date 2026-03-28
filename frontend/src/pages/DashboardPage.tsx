import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { overviewApi, type OverviewResponse } from '../api';
import ExternalAgentCard from '../components/ExternalAgentCard';
import MetricCard from '../components/MetricCard';
import EmptyState from '../components/EmptyState';
import { useExternalAgentsAvailability } from '../hooks/useExternalAgentsAvailability';
import { useI18n } from '../i18n';
import { formatDate, formatInstruction, formatPercent, truncate } from '../utils/format';

export default function DashboardPage() {
  const { t } = useI18n();
  const externalAgents = useExternalAgentsAvailability();
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          setError(err instanceof Error ? err.message : t('dashboard.errorLoadOverview'));
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
  }, []);

  if (loading) {
    return <div className="p-6 text-sm text-muted">{t('dashboard.loading')}</div>;
  }

  if (error || !data) {
    return <div className="p-6 text-sm text-danger">{error ?? t('dashboard.unavailable')}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold font-serif">{t('dashboard.title')}</h1>
      <section className="metrics-row">
        <MetricCard label={t('dashboard.totalSkills')} value={data.skills.summary.total_skills_all} hint={t('dashboard.totalSkillsHint', { active: data.skills.summary.total_skills })} />
        <MetricCard label={t('dashboard.averageSkillScore')} value={data.skills.average_score.toFixed(1)} hint={t('dashboard.averageSkillScoreHint')} />
        <MetricCard label={t('dashboard.workflowSessions')} value={data.workflows.total} hint={t(data.health.db_path.includes('.openspace') ? 'dashboard.workflowSessionsHintLocal' : 'dashboard.workflowSessionsHintWorkspace')} />
        <MetricCard label={t('dashboard.workflowSuccess')} value={`${data.workflows.average_success_rate.toFixed(1)}%`} hint={t('dashboard.workflowSuccessHint')} />
      </section>

      <section>
        <div className="panel-surface p-5 space-y-4">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.health')}</div>
            <h2 className="text-2xl font-bold font-serif mt-1">{t('dashboard.runtimeSnapshot')}</h2>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between"><span className="text-muted">{t('dashboard.status')}</span><span>{data.health.status}</span></div>
            <div className="flex items-center justify-between"><span className="text-muted">{t('dashboard.dbPath')}</span><span className="text-right break-all">{data.health.db_path}</span></div>
            <div className="flex items-center justify-between"><span className="text-muted">{t('dashboard.workflowCount')}</span><span>{data.health.workflow_count}</span></div>
            <div className="flex items-center justify-between"><span className="text-muted">{t('dashboard.builtFrontend')}</span><span>{data.health.frontend_dist_exists ? t('common.yes') : t('common.no')}</span></div>
          </div>
        </div>
      </section>

      <section>
        <div className="panel-surface p-5 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.externalAgentsKicker')}</div>
              <h2 className="text-2xl font-bold font-serif mt-1">{t('dashboard.externalAgentsTitle')}</h2>
            </div>
            <div className="text-sm text-muted">
              {externalAgents.checking ? t('dashboard.externalAgentsChecking') : t('dashboard.externalAgentsCount', { count: externalAgents.agents.length })}
            </div>
          </div>
          {externalAgents.agents.length === 0 ? (
            externalAgents.checking ? (
              <div className="text-sm text-muted">{t('dashboard.externalAgentsChecking')}</div>
            ) : (
              <EmptyState title={t('dashboard.externalAgentsEmptyTitle')} description={t('dashboard.externalAgentsEmptyDescription')} />
            )
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {externalAgents.agents.map((agent) => (
                <ExternalAgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="grid grid-cols-2 gap-6">
        <div className="panel-surface p-5 space-y-4">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.skills')}</div>
            <h2 className="text-2xl font-bold font-serif mt-1">{t('dashboard.topSkills')}</h2>
          </div>
          {data.skills.top.length === 0 ? (
            <EmptyState title={t('dashboard.noSkillsTitle')} description={t('dashboard.noSkillsDescription')} />
          ) : (
            <div className="space-y-3">
              {data.skills.top.map((skill) => (
                <Link key={skill.skill_id} to={`/skills/${encodeURIComponent(skill.skill_id)}`} className="record-card block p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 space-y-1">
                      <div className="font-bold truncate">{skill.name}</div>
                      <div className="text-sm text-muted">{truncate(skill.description || t('common.noDescription'), 110)}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-2xl font-bold font-serif">{skill.score.toFixed(1)}</div>
                      <div className="text-xs text-muted">{t('dashboard.score')}</div>
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
            <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('dashboard.workflows')}</div>
            <h2 className="text-2xl font-bold font-serif mt-1">{t('dashboard.recentSessions')}</h2>
          </div>
          {data.workflows.recent.length === 0 ? (
            <EmptyState title={t('dashboard.noSessionsTitle')} description={t('dashboard.noSessionsDescription')} />
          ) : (
            <div className="space-y-3">
              {data.workflows.recent.map((workflow) => (
                <Link key={workflow.id} to={`/workflows/${encodeURIComponent(workflow.id)}`} className="record-card block p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 space-y-1">
                      <div className="font-bold truncate">{workflow.task_name}</div>
                      <div className="text-sm text-muted line-clamp-2">{formatInstruction(workflow.instruction, 160)}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-lg font-bold font-serif">{(workflow.success_rate * 100).toFixed(1)}%</div>
                      <div className="text-xs text-muted">{t('dashboard.success')}</div>
                    </div>
                  </div>
                  <div className="mt-3 flex gap-3 text-xs text-muted">
                    <span>{t('dashboard.steps', { count: workflow.total_steps })}</span>
                    <span>{t('dashboard.agentActions', { count: workflow.agent_action_count })}</span>
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
