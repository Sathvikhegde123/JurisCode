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
        'rounded-3xl border border-amber-200/70 bg-white p-5 backdrop-blur-xl transition duration-200 hover:border-electric/30',
        className,
      )}
    >
      {title || subtitle ? (
        <div className="mb-4">
          {title ? <h2 className="text-lg font-semibold text-slate-900">{title}</h2> : null}
          {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}
