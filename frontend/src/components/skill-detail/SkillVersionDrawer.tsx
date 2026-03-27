import { useLayoutEffect, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import type { SkillDetail } from '../../api';
import { parseDiff } from '../../utils/diffParser';
import EmptyState from '../EmptyState';
import ProgressBar from '../ProgressBar';
import DiffViewer from './DiffViewer';
import { useI18n } from '../../i18n';
import { formatDate, formatPercent, truncate } from '../../utils/format';

interface SkillVersionDrawerProps {
  skill: SkillDetail | null;
  isOpen: boolean;
  onClose: () => void;
}

const DRAWER_ANIMATION_DURATION_MS = 300;
const MAX_RENDERABLE_DIFF_LENGTH = 250_000;
const APP_ROOT_SELECTOR = '#root';
const SKILL_MD_FILENAME = 'SKILL.md';

function resolveSourcePreview(skill: SkillDetail) {
  const snapshot = skill.lineage.content_snapshot;
  if (snapshot && Object.prototype.hasOwnProperty.call(snapshot, SKILL_MD_FILENAME)) {
    return {
      path: `Version snapshot - ${SKILL_MD_FILENAME}`,
      content: snapshot[SKILL_MD_FILENAME] ?? '',
    };
  }

  if (skill.source?.exists && skill.source.content !== null) {
    return {
      path: skill.source.path || skill.path || SKILL_MD_FILENAME,
      content: skill.source.content,
    };
  }

  return null;
}

function lockScroll() {
  const html = document.documentElement;
  const body = document.body;
  const appRoot = document.querySelector<HTMLElement>(APP_ROOT_SELECTOR);
  const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  const supportsStableScrollbarGutter = typeof CSS !== 'undefined' && CSS.supports?.('scrollbar-gutter: stable');

  const bodyScrollbarWidth = supportsStableScrollbarGutter ? 0 : Math.max(0, window.innerWidth - html.clientWidth);

  html.classList.add('drawer-open');
  body.classList.add('drawer-open');
  if (appRoot) {
    appRoot.inert = true;
    appRoot.setAttribute('aria-hidden', 'true');
  }
  if (bodyScrollbarWidth > 0) {
    body.style.paddingRight = `${bodyScrollbarWidth}px`;
  }

  return () => {
    html.classList.remove('drawer-open');
    body.classList.remove('drawer-open');
    body.style.removeProperty('padding-right');
    if (appRoot) {
      appRoot.inert = false;
      appRoot.removeAttribute('aria-hidden');
    }
    if (previouslyFocused && previouslyFocused !== body && previouslyFocused.isConnected) {
      previouslyFocused.focus({ preventScroll: true });
    }
  };
}

export default function SkillVersionDrawer({ skill, isOpen, onClose }: SkillVersionDrawerProps) {
  const { t } = useI18n();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const rawDiff = skill?.lineage.content_diff ?? '';
  const isOversizedDiff = rawDiff.length > MAX_RENDERABLE_DIFF_LENGTH;
  const diffFiles = useMemo(() => (isOversizedDiff ? [] : parseDiff(rawDiff)), [isOversizedDiff, rawDiff]);
  const canShowDiff = rawDiff.trim().length > 0;

  useLayoutEffect(() => {
    if (!skill) {
      return;
    }
    return lockScroll();
  }, [skill]);

  useLayoutEffect(() => {
    if (!isOpen) {
      return;
    }
    closeButtonRef.current?.focus();
  }, [isOpen]);

  useLayoutEffect(() => {
    if (!skill) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, skill]);

  if (!skill) {
    return null;
  }

  const sourcePreview = resolveSourcePreview(skill);

  const drawerContent = (
    <>
      <button
        type="button"
        aria-label={t('skillDrawer.closeAria')}
        className={`fixed inset-0 z-30 bg-[rgba(20,20,19,0.22)] transition-opacity duration-300 ${isOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'}`}
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="skill-version-drawer-title"
        className={`fixed top-0 right-0 z-40 flex h-full min-w-[28rem] max-w-[65vw] border-l-2 border-[color:var(--color-ink)] bg-[color:var(--color-surface)] shadow-lg will-change-transform ${isOpen ? 'pointer-events-auto' : 'pointer-events-none'}`}
        style={{
          width: '65vw',
          animation: `${isOpen ? 'drawer-slide-in' : 'drawer-slide-out'} ${DRAWER_ANIMATION_DURATION_MS}ms ease-in-out forwards`,
        }}
      >
        <div className="drawer-scroll flex h-full w-full flex-col overflow-hidden overscroll-contain">
          <header className="p-4 border-b-2 border-[color:var(--color-border)] flex items-start justify-between gap-3 shrink-0">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wide text-muted">{t('skillDrawer.title')}</p>
              <h2 id="skill-version-drawer-title" className="font-bold text-lg truncate">{skill.name}</h2>
              <p className="text-xs text-muted font-mono break-all">{skill.skill_id}</p>
            </div>
            <div className="flex items-center gap-2">
              <Link to={`/skills/${encodeURIComponent(skill.skill_id)}`} className="btn-outline-ink text-sm">
                {t('skillDrawer.openMain')}
              </Link>
              <button type="button" onClick={onClose} ref={closeButtonRef} className="btn-outline-ink text-sm">
                {t('skillDrawer.close')}
              </button>
            </div>
          </header>

          <main className="drawer-scroll drawer-scroll-region flex-1 overflow-y-auto overscroll-contain space-y-4 bg-bg-page p-4">
            <section className="rounded-[var(--radius)] border-2 border-[color:var(--color-border-dark)] bg-surface p-4 space-y-3">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2 min-w-0">
                  <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('skillDrawer.summary')}</div>
                  <div className="text-sm text-muted">{skill.description || t('skillDrawer.noDescription')}</div>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="tag px-2 py-1">{skill.category}</span>
                    <span className="tag px-2 py-1">{skill.origin}</span>
                    <span className="tag px-2 py-1">{t('skillDrawer.generation', { count: skill.generation })}</span>
                    <span className="tag px-2 py-1">{skill.is_active ? t('common.active') : t('common.inactive')}</span>
                    {skill.tags.map((tag) => (
                      <span key={tag} className="tag px-2 py-1">{tag}</span>
                    ))}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-4xl font-bold font-serif leading-none">{skill.score.toFixed(1)}</div>
                  <div className="text-xs uppercase tracking-[0.16em] text-muted mt-2">{t('skillDrawer.versionScore')}</div>
                </div>
              </div>
            </section>

            <section className="rounded-[var(--radius)] border-2 border-[color:var(--color-border-dark)] bg-surface p-4 space-y-4">
              <div>
                <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('skillDrawer.metrics')}</div>
                <h3 className="text-xl font-bold font-serif mt-1">{t('skillDrawer.executionQuality')}</h3>
              </div>
              <div className="space-y-4">
                <ProgressBar label={t('skillDrawer.effectiveRate')} value={skill.effective_rate} colorClass="bg-primary" />
                <ProgressBar label={t('skillDrawer.completionRate')} value={skill.completion_rate} colorClass="bg-accent" />
                <ProgressBar label={t('skillDrawer.appliedRate')} value={skill.applied_rate} colorClass="bg-teal" />
                <ProgressBar label={t('skillDrawer.fallbackRate')} value={skill.fallback_rate} colorClass="bg-danger" />
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm text-muted">
                <div><div className="font-bold text-ink">{t('skillDrawer.selections')}</div><div>{skill.total_selections}</div></div>
                <div><div className="font-bold text-ink">{t('skillDrawer.applied')}</div><div>{skill.total_applied}</div></div>
                <div><div className="font-bold text-ink">{t('skillDrawer.completions')}</div><div>{skill.total_completions}</div></div>
                <div><div className="font-bold text-ink">{t('skillDrawer.fallbacks')}</div><div>{skill.total_fallbacks}</div></div>
              </div>
            </section>

            <section className="rounded-[var(--radius)] border-2 border-[color:var(--color-border-dark)] bg-surface p-4 text-sm space-y-2">
              <h3 className="font-bold">{t('skillDrawer.metadata')}</h3>
              <p><strong>{t('skillDrawer.originLabel')}</strong> {skill.origin}</p>
              <p><strong>{t('skillDrawer.generationLabel')}</strong> {skill.generation}</p>
              <p><strong>{t('skillDrawer.visibilityLabel')}</strong> {skill.visibility}</p>
              <p><strong>{t('skillDrawer.createdLabel')}</strong> {formatDate(skill.lineage.created_at)}</p>
              <p><strong>{t('skillDrawer.firstSeenLabel')}</strong> {formatDate(skill.first_seen)}</p>
              <p><strong>{t('skillDrawer.lastUpdatedLabel')}</strong> {formatDate(skill.last_updated)}</p>
              <p><strong>{t('skillDrawer.skillPathLabel')}</strong> <span className="break-all">{skill.path || t('common.unavailable')}</span></p>
              <p><strong>{t('skillDrawer.skillDirLabel')}</strong> <span className="break-all">{skill.skill_dir || t('common.unavailable')}</span></p>
              <p><strong>{t('skillDrawer.parentIdsLabel')}</strong> {skill.parent_skill_ids.length ? skill.parent_skill_ids.join(', ') : t('common.none')}</p>
              <p><strong>{t('skillDrawer.changeSummaryLabel')}</strong> {skill.lineage.change_summary || t('common.none')}</p>
              <p><strong>{t('skillDrawer.effectiveScoreLabel')}</strong> {formatPercent(skill.effective_rate)}</p>
            </section>

            <section className="rounded-[var(--radius)] border-2 border-[color:var(--color-border-dark)] bg-surface p-4 space-y-4">
              <div>
                <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('skillDrawer.diff')}</div>
                <h3 className="text-xl font-bold font-serif mt-1">{t('skillDrawer.contentDiff')}</h3>
              </div>
              {isOversizedDiff ? (
                <EmptyState title={t('skillDrawer.diffTooLargeTitle')} description={t('skillDrawer.diffTooLargeDescription')} />
              ) : canShowDiff ? (
                diffFiles.length > 0 ? (
                  <DiffViewer files={diffFiles} />
                ) : (
                  <EmptyState title={t('skillDrawer.diffUnavailableTitle')} description={t('skillDrawer.diffUnavailableDescription')} />
                )
              ) : (
                <EmptyState title={t('skillDrawer.noContentDiffTitle')} description={t('skillDrawer.noContentDiffDescription')} />
              )}
            </section>

            <section className="rounded-[var(--radius)] border-2 border-[color:var(--color-border-dark)] bg-surface p-4 space-y-4">
              <div>
                <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('skillDrawer.source')}</div>
                <h3 className="text-xl font-bold font-serif mt-1">{t('skillDrawer.preview')}</h3>
              </div>
              {sourcePreview ? (
                <div className="space-y-3">
                  <div className="text-xs text-muted break-all">{sourcePreview.path}</div>
                  <pre className="field-surface p-4 text-xs overflow-auto max-h-[320px] whitespace-pre-wrap">{sourcePreview.content}</pre>
                </div>
              ) : (
                <EmptyState title={t('skillDrawer.sourceUnavailableTitle')} description={t('skillDrawer.sourceUnavailableDescription')} />
              )}
            </section>

            <section className="rounded-[var(--radius)] border-2 border-[color:var(--color-border-dark)] bg-surface p-4 space-y-4">
              <div>
                <div className="text-xs uppercase tracking-[0.16em] text-muted">{t('skillDrawer.analyses')}</div>
                <h3 className="text-xl font-bold font-serif mt-1">{t('skillDrawer.recentAnalyses')}</h3>
              </div>
              {skill.recent_analyses.length > 0 ? (
                <div className="space-y-3">
                  {skill.recent_analyses.map((analysis) => (
                    <div key={`${analysis.task_id}-${analysis.timestamp}`} className="panel-subtle p-4 bg-surface space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-bold truncate">{analysis.task_id}</div>
                        <div className="text-xs text-muted">{formatDate(analysis.timestamp)}</div>
                      </div>
                      <div className="text-sm text-muted">{truncate(analysis.execution_note || t('skillDrawer.noExecutionNote'), 220)}</div>
                      <div className="text-xs text-muted">
                        {t('skillDrawer.analysisSummary', {
                          completed: analysis.task_completed ? t('common.yes') : t('common.no'),
                          toolIssues: analysis.tool_issues.length,
                          suggestions: analysis.evolution_suggestions.length,
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title={t('skillDrawer.noAnalysesTitle')} description={t('skillDrawer.noAnalysesDescription')} />
              )}
            </section>
          </main>
        </div>
      </aside>
    </>
  );

  if (typeof document === 'undefined') {
    return drawerContent;
  }

  return createPortal(drawerContent, document.body);
}
