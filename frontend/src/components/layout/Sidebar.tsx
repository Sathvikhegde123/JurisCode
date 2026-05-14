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
    <aside className="hidden min-h-[calc(100vh-0px)] w-72 flex-col border-r border-white/10 bg-[#08111fe6] px-4 py-6 backdrop-blur-xl xl:flex">
      <div className="flex items-center gap-3 px-2">
        <div className="grid h-11 w-11 place-items-center rounded-2xl border border-electric/30 bg-electric/10 text-lg font-bold text-electric shadow-glow">
          J
        </div>
        <div>
          <p className="text-lg font-semibold text-white">JurisCode Bharat</p>
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
                  ? 'border-electric/30 bg-electric/10 text-white shadow-[0_0_0_1px_rgba(59,130,246,0.12)]'
                  : 'border-white/10 bg-white/5 text-slate-300 hover:border-white/20 hover:bg-white/8 hover:text-white',
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto rounded-3xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
        <p className="font-semibold text-white">Educational disclaimer</p>
        <p className="mt-2 leading-6">For educational and mock-trial practice purposes only. Not legal advice.</p>
      </div>
    </aside>
  );
}
