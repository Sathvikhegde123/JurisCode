import type { ReactNode } from 'react';
import { GlassCard } from './GlassCard';

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <GlassCard>
      <div className="py-8 text-center">
        <p className="text-lg font-semibold text-white">{title}</p>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-400">{description}</p>
        {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
      </div>
    </GlassCard>
  );
}
