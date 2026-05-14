import { GlassCard } from './GlassCard';

type DashboardStatCardProps = {
  title: string;
  value: string;
  caption?: string;
  delta?: string;
  tone?: 'electric' | 'emerald' | 'gold';
};

export function DashboardStatCard({ title, value, caption, delta, tone = 'electric' }: DashboardStatCardProps) {
  const ring =
    tone === 'emerald'
      ? 'from-emeraldGlow/40 to-emeraldGlow/0'
      : tone === 'gold'
        ? 'from-mutedGold/40 to-mutedGold/0'
        : 'from-electric/40 to-electric/0';

  return (
    <GlassCard className="relative overflow-hidden">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${ring}`} />
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate-600">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
          {caption ? <p className="mt-2 text-sm text-slate-600">{caption}</p> : null}
        </div>
        {delta ? <span className="rounded-full border border-amber-200/70 bg-white px-3 py-1 text-xs text-slate-700">{delta}</span> : null}
      </div>
    </GlassCard>
  );
}
