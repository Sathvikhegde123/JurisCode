import { Link, NavLink } from 'react-router-dom';
import { classNames } from '@/utils/classNames';

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/practice', label: 'Practice' },
  { to: '/challenge', label: 'Challenge' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/models', label: 'Models' },
  { to: '/learn', label: 'Learn' },
];

type NavbarProps = {
  compact?: boolean;
};

export function Navbar({ compact = false }: NavbarProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[#07111fe6] backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <Link to="/" className="group flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl border border-electric/30 bg-electric/10 text-sm font-bold text-electric shadow-glow transition group-hover:border-electric/50">
            J
          </div>
          <div>
            <p className="text-base font-semibold text-white">JurisCode Bharat</p>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">AI Mock Trial Learning</p>
          </div>
        </Link>

        {!compact ? (
          <nav className="hidden items-center gap-2 xl:flex" aria-label="Primary navigation">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  classNames(
                    'rounded-full px-4 py-2 text-sm transition',
                    isActive ? 'bg-white/10 text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        ) : null}

        <div className="hidden items-center gap-3 md:flex">
          <span className="rounded-full border border-emeraldGlow/20 bg-emeraldGlow/10 px-3 py-1 text-xs font-medium text-emeraldGlow">
            Education-first AI
          </span>
          <span className="max-w-[18rem] rounded-full border border-mutedGold/20 bg-mutedGold/10 px-3 py-1 text-xs text-mutedGold">
            For educational and mock-trial practice purposes only. Not legal advice.
          </span>
        </div>
      </div>
    </header>
  );
}
