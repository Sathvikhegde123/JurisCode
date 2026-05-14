import { clamp, formatPercent } from '@/utils/format';

type ProgressRingProps = {
  value: number;
  label: string;
  size?: number;
};

export function ProgressRing({ value, label, size = 132 }: ProgressRingProps) {
  const safeValue = clamp(value, 0, 100);
  const fill = `${safeValue}%`;

  return (
    <div className="flex flex-col items-center justify-center text-center">
      <div
        className="grid place-items-center rounded-full border border-amber-200/70 bg-white "
        style={{ width: size, height: size, background: `conic-gradient(#f97316 ${fill}, rgba(148,163,184,0.25) 0)` }}
      >
        <div className="flex h-[calc(100%-16px)] w-[calc(100%-16px)] flex-col items-center justify-center rounded-full border border-amber-200/70 bg-white">
          <span className="text-3xl font-semibold text-slate-900">{formatPercent(safeValue)}</span>
          <span className="mt-1 text-xs uppercase tracking-[0.3em] text-slate-600">{label}</span>
        </div>
      </div>
    </div>
  );
}
