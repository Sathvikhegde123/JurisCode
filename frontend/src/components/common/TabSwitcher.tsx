import { classNames } from '@/utils/classNames';

type TabSwitcherProps = {
  tabs: string[];
  active: string;
  onChange: (tab: string) => void;
};

export function TabSwitcher({ tabs, active, onChange }: TabSwitcherProps) {
  return (
    <div className="flex flex-wrap gap-2 rounded-2xl border border-white/10 bg-white/5 p-2">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onChange(tab)}
          className={classNames(
            'rounded-xl px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-electric/50',
            active === tab ? 'bg-electric text-white shadow-glow' : 'text-slate-300 hover:bg-white/5 hover:text-white',
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
