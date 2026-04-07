import { NavLink, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? 'font-bold text-primary underline decoration-2 underline-offset-4'
    : 'hover:text-primary';

export default function MainLayout() {
  const { t, i18n } = useTranslation();
  const vitePort = import.meta.env.VITE_PORT || '3888';
  const runtimeLabel = import.meta.env.DEV
    ? t('layout.runtimeDev', { apiPort: '7788', vitePort })
    : t('layout.runtimeProd', { port: '7788' });

  return (
    <div className="h-screen min-w-[1180px] relative flex flex-col overflow-x-auto overflow-y-hidden bg-bg-page text-ink">
      <nav className="relative z-10 flex justify-between items-center px-4 py-3 border-b border-[color:var(--color-border)] bg-bg-page">
        <div className="flex items-center gap-8">
          <img src="/logo.png" alt="Cubecloud" className="h-10 w-auto" />
          <div className="flex gap-4 text-sm">
            <NavLink to="/dashboard" className={linkClass}>
              {t('nav.dashboard')}
            </NavLink>
            <NavLink to="/showcase" className={linkClass}>
              {t('layout.spotlight')}
            </NavLink>
            <NavLink to="/skills" className={linkClass}>
              {t('nav.skills')}
            </NavLink>
            <NavLink to="/workflows" className={linkClass}>
              {t('nav.workflows')}
            </NavLink>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted">
          <div>{runtimeLabel}</div>
          <div className="flex items-center gap-2">
            <span>{t('layout.language')}</span>
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => i18n.changeLanguage('en')}
                className={`rounded-full border px-2 py-1 transition-colors ${
                  i18n.language === 'en'
                    ? 'border-[color:var(--color-ink)] bg-surface text-ink'
                    : 'border-[color:var(--color-border)] hover:border-[color:var(--color-border-dark)]'
                }`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => i18n.changeLanguage('zh')}
                className={`rounded-full border px-2 py-1 transition-colors ${
                  i18n.language === 'zh'
                    ? 'border-[color:var(--color-ink)] bg-surface text-ink'
                    : 'border-[color:var(--color-border)] hover:border-[color:var(--color-border-dark)]'
                }`}
              >
                中文
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="app-scroll-region relative z-10 min-h-0 flex-1 overflow-auto">
        <Outlet />
      </main>

      <footer className="relative z-10 border-t border-[color:var(--color-border)] bg-bg-page px-4 py-2 text-[11px] leading-5 text-muted">
        <div className="font-semibold text-ink">{t('layout.legalPrimary')}</div>
        <div>{t('layout.legalSecondary')}</div>
      </footer>
    </div>
  );
}
