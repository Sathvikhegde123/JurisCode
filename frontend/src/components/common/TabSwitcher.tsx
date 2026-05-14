import { classNames } from '@/utils/classNames';

type TabSwitcherProps = {
  tabs: string[];
  active: string;
  onChange: (tab: string) => void;
};

export function TabSwitcher({ tabs, active, onChange }: TabSwitcherProps) {
  return (
    <div className="flex flex-wrap gap-2 rounded-2xl border border-amber-200/70 bg-white/70 p-2">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onChange(tab)}
          className={classNames(
            'rounded-xl px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-electric/50',
            active === tab ? 'bg-electric text-white shadow-glow' : 'text-slate-700 hover:bg-amber-50/70 hover:text-slate-900',
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
