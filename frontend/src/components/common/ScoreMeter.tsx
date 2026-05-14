import { clamp, formatPercent } from '@/utils/format';

type ScoreMeterProps = {
  score: number;
  label?: string;
};

export function ScoreMeter({ score, label = 'Argument strength' }: ScoreMeterProps) {
  const value = clamp(score, 0, 100);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm text-slate-700">
        <span>{label}</span>
        <span className="font-semibold text-slate-900">{formatPercent(value)}</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-amber-100/70">
        <div
          className="h-full rounded-full bg-gradient-to-r from-electric via-emeraldGlow to-mutedGold transition-all duration-300"
          style={{ width: `${value}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
