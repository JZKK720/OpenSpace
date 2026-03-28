interface SpotlightIconProps {
  icon?: string;
  className?: string;
}

export default function SpotlightIcon({ icon = 'grid', className = 'h-6 w-6' }: SpotlightIconProps) {
  switch (icon) {
    case 'radar':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M12 3v9l6.5 3.5" />
          <circle cx="12" cy="12" r="8" />
          <path d="M12 7a5 5 0 0 1 5 5" />
          <path d="M12 10a2 2 0 0 1 2 2" />
        </svg>
      );
    case 'bot':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M12 4v3" />
          <path d="M8 4h8" />
          <rect x="5" y="8" width="14" height="10" rx="3" />
          <path d="M9 13h.01" />
          <path d="M15 13h.01" />
          <path d="M9 18v2" />
          <path d="M15 18v2" />
          <path d="M5 12H3" />
          <path d="M21 12h-2" />
        </svg>
      );
    case 'spark':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3Z" />
          <path d="M19 4v4" />
          <path d="M21 6h-4" />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <rect x="4" y="4" width="6" height="6" rx="1.2" />
          <rect x="14" y="4" width="6" height="6" rx="1.2" />
          <rect x="4" y="14" width="6" height="6" rx="1.2" />
          <rect x="14" y="14" width="6" height="6" rx="1.2" />
        </svg>
      );
  }
}