const STEPS = [
  'Understanding your issue...',
  'Selecting legal source pack...',
  'Preparing legal awareness response...',
];

type ScenarioLoadingStateProps = {
  stepIndex?: number;
};

export function ScenarioLoadingState({ stepIndex = 0 }: ScenarioLoadingStateProps) {
  const safe = Math.min(Math.max(stepIndex, 0), STEPS.length - 1);
  return (
    <div className="space-y-4 rounded-3xl border border-amber-200/70 bg-white/90 p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 animate-pulse rounded-2xl border border-electric/30 bg-electric/15" />
        <div>
          <p className="text-sm font-semibold text-slate-900">Analyzing scenario</p>
          <p className="text-xs text-slate-600">This may take a moment.</p>
        </div>
      </div>
      <ul className="space-y-2 text-sm text-slate-700">
        {STEPS.map((label, i) => (
          <li
            key={label}
            className={
              i === safe
                ? 'font-medium text-electric'
                : i < safe
                  ? 'text-slate-500 line-through decoration-slate-300'
                  : 'text-slate-400'
            }
          >
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
