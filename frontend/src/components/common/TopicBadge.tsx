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
          : 'border-white/10 bg-white/5 text-slate-300 hover:border-white/20 hover:text-white',
      )}
    >
      {label}
    </span>
  );
}
