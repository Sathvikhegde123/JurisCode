type LoadingSpinnerProps = {
  label?: string;
  className?: string;
};

export function LoadingSpinner({ label = 'Loading', className }: LoadingSpinnerProps) {
  return (
    <div className={`inline-flex items-center gap-3 text-sm text-slate-700 ${className ?? ''}`}>
      <div className="h-5 w-5 rounded-full border-2 border-electric/30 border-t-electric animate-spin" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
