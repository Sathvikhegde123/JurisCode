import { NavLink } from 'react-router-dom';
import { classNames } from '@/utils/classNames';

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/practice', label: 'Practice Arena' },
  { to: '/challenge', label: 'Challenge My Argument' },
  { to: '/sessions', label: 'Session History' },
  { to: '/models', label: 'Model Status' },
  { to: '/learn', label: 'Learning Hub' },
];

export function Sidebar() {
  return (
    <aside className="hidden min-h-[calc(100vh-0px)] w-72 flex-col border-r border-amber-200/70 bg-[#fff7ea]/90 px-4 py-6 backdrop-blur-xl xl:flex">
      <div className="flex items-center gap-3 px-2">
        <div className="grid h-11 w-11 place-items-center rounded-2xl border border-electric/30 bg-electric/10 text-lg font-bold text-electric shadow-sm">
          J
        </div>
        <div>
          <p className="text-lg font-semibold text-slate-900">JurisCode Bharat</p>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Courtroom simulator</p>
        </div>
      </div>

      <nav className="mt-8 flex flex-1 flex-col gap-2" aria-label="Sidebar navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              classNames(
                'rounded-2xl border px-4 py-3 text-sm transition',
                isActive
                  ? 'border-electric/30 bg-electric/10 text-slate-900 shadow-[0_0_0_1px_rgba(249,115,22,0.18)]'
                  : 'border-amber-200/70 bg-white text-slate-700 hover:border-amber-300/70 hover:bg-amber-50/80 hover:text-slate-900',
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto rounded-3xl border border-amber-200/70 bg-white p-4 text-sm text-slate-700">
        <p className="font-semibold text-slate-900">Educational disclaimer</p>
        <p className="mt-2 leading-6">For educational and mock-trial practice purposes only. Not legal advice.</p>
      </div>
    </aside>
  );
}
