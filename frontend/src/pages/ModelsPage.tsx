import { useEffect, useState } from 'react';
import { DashboardStatCard } from '@/components/common/DashboardStatCard';
import { GlassCard } from '@/components/common/GlassCard';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { getHealth, getModelsStatus } from '@/services/legalApi';
import { getApiError } from '@/services/api';
import { useToast } from '@/contexts/ToastContext';

export function ModelsPage() {
  const { notify } = useToast();
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<Record<string, unknown>>({});
  const [status, setStatus] = useState<Record<string, unknown>>({});

  useEffect(() => {
    Promise.all([getHealth(), getModelsStatus()])
      .then(([healthResponse, statusResponse]) => {
        setHealth(healthResponse as Record<string, unknown>);
        setStatus(statusResponse as Record<string, unknown>);
      })
      .catch((error) => {
        notify({ variant: 'error', title: 'Model status unavailable', message: getApiError(error).message });
      })
      .finally(() => setLoading(false));
  }, [notify]);

  if (loading) {
    return (
      <GlassCard>
        <LoadingSpinner label="Loading model health" />
      </GlassCard>
    );
  }

  const modelLoaded = Boolean(health.models_loaded ?? status.models_loaded);
  const activeAdapter = String(status.active_adapter ?? 'Unknown');
  const backendStatus = String(status.backend_status ?? health.status ?? 'Unknown');

  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <DashboardStatCard title="Health" value={String(health.status ?? 'unknown')} caption="Backend liveness" tone="emerald" />
        <DashboardStatCard title="Device" value={String(health.device ?? status.device ?? 'unknown')} caption="Runtime device" />
        <DashboardStatCard title="Adapters loaded" value={modelLoaded ? 'Yes' : 'No'} caption="Model runtime state" tone="gold" />
        <DashboardStatCard title="Active adapter" value={activeAdapter} caption="Current LoRA adapter" />
        <DashboardStatCard title="Dtype" value={String(status.dtype ?? 'unknown')} caption="Precision mode" tone="emerald" />
        <DashboardStatCard title="Backend" value={backendStatus} caption="API service status" tone="gold" />
      </section>

      <GlassCard title="Futuristic monitoring dashboard" subtitle="Inspect the live backend and model runtime state">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Object.entries({ ...health, ...status }).map(([key, value]) => (
            <div key={key} className="rounded-2xl border border-amber-200/70 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">{key.split('_').join(' ')}</p>
              <p className="mt-2 break-words text-sm text-slate-900">{typeof value === 'string' ? value : JSON.stringify(value)}</p>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
