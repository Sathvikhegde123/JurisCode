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
        className="grid place-items-center rounded-full border border-white/10 bg-white/5 shadow-glow"
        style={{ width: size, height: size, background: `conic-gradient(#3b82f6 ${fill}, rgba(255,255,255,0.08) 0)` }}
      >
        <div className="flex h-[calc(100%-16px)] w-[calc(100%-16px)] flex-col items-center justify-center rounded-full border border-white/10 bg-[#08111f]">
          <span className="text-3xl font-semibold text-white">{formatPercent(safeValue)}</span>
          <span className="mt-1 text-xs uppercase tracking-[0.3em] text-slate-400">{label}</span>
        </div>
      </div>
    </div>
  );
}
