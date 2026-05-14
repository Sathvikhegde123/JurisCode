import type { ReactNode } from 'react';
import { classNames } from '@/utils/classNames';

type GlassCardProps = {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
};

export function GlassCard({ children, className, title, subtitle }: GlassCardProps) {
  return (
    <section
      className={classNames(
        'rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl transition duration-200 hover:border-electric/30',
        className,
      )}
    >
      {title || subtitle ? (
        <div className="mb-4">
          {title ? <h2 className="text-lg font-semibold text-white">{title}</h2> : null}
          {subtitle ? <p className="mt-1 text-sm text-slate-400">{subtitle}</p> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}
