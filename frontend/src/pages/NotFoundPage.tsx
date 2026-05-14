import { Link } from 'react-router-dom';
import { GlassCard } from '@/components/common/GlassCard';

export function NotFoundPage() {
  return (
    <div className="grid min-h-screen place-items-center px-4">
      <GlassCard className="max-w-2xl text-center">
        <p className="section-kicker">404</p>
        <h1 className="mt-3 text-3xl font-semibold text-white">Page not found</h1>
        <p className="mt-4 text-sm leading-7 text-slate-300">The courtroom route you requested does not exist.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link to="/dashboard" className="rounded-full bg-electric px-5 py-2.5 font-semibold text-white transition hover:brightness-110">Go to Dashboard</Link>
          <Link to="/" className="rounded-full border border-white/15 bg-white/5 px-5 py-2.5 font-semibold text-white transition hover:border-electric/40">Return Home</Link>
        </div>
      </GlassCard>
    </div>
  );
}
