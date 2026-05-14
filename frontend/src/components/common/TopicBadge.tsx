import { classNames } from '@/utils/classNames';

type TopicBadgeProps = {
  label: string;
  active?: boolean;
};

export function TopicBadge({ label, active = false }: TopicBadgeProps) {
  return (
    <span
      className={classNames(
        'inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition',
        active
          ? 'border-electric/40 bg-electric/15 text-electric'
          : 'border-amber-200/70 bg-white text-slate-700 hover:border-amber-300/70 hover:text-slate-900',
      )}
    >
      {label}
    </span>
  );
}
