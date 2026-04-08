import { useTranslation } from 'react-i18next';

// ttyd URL is baked in at build time via VITE_TTYD_URL.
// Default: http://localhost:8681 (the oh-web service exposed port).
const TTYD_URL = (import.meta.env.VITE_TTYD_URL as string | undefined) ?? 'http://localhost:8681';

export default function HarnessAgentPage() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col h-full">

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[color:var(--color-border)] shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-semibold">{t('harnessAgent.title')}</h1>
          <span className="text-xs text-muted">{t('harnessAgent.subtitle')}</span>
        </div>
        <a
          href={TTYD_URL}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-primary border border-[color:var(--color-border)] hover:border-[color:var(--color-border-dark)] rounded-full px-3 py-1 transition-colors"
        >
          {t('harnessAgent.openInTab')} ↗
        </a>
      </div>

      {/* Embedded ttyd terminal — fills remaining height */}
      <iframe
        src={TTYD_URL}
        title={t('harnessAgent.title')}
        className="flex-1 w-full border-none"
        style={{ background: '#1e1e2e' }}
        allow="clipboard-read; clipboard-write"
      />
    </div>
  );
}
