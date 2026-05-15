import type { ReactNode } from 'react';

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) {
    return [];
  }
  return v.map((x) => (typeof x === 'string' ? x : String(x))).map((s) => s.trim()).filter(Boolean);
}

const SYS_WEAK =
  /the system could not fully analyze|could not process|could not fully verify|could not complete analysis/i;

const TRACE_DENY =
  /fallback response generated|gemini\/parse attempts failed|could not be parsed|api call failed|debug_error|structured api output/i;

function scrubParagraph(text: unknown): string {
  const t = String(text ?? '').trim();
  if (!t || t === '—' || SYS_WEAK.test(t)) {
    return '';
  }
  return t;
}

function filterReasoning(items: string[]): string[] {
  return items.filter((line) => line.trim() && !TRACE_DENY.test(line));
}

function ReportSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-amber-200/60 bg-white/90 p-4">
      <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
      <div className="mt-2 text-sm leading-relaxed text-slate-800">{children}</div>
    </section>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1.5 pl-5">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

type OfficialSourceRow = {
  act_name?: string;
  section_reference?: string;
  relevance?: string;
  source_origin?: string;
  source_type?: string;
  verified?: boolean;
};

function SourceRow({ src }: { src: OfficialSourceRow }) {
  return (
    <div className="rounded-xl border border-amber-200/50 bg-amber-50/30 px-3 py-2 text-sm">
      <p className="font-medium text-slate-900">{src.act_name || 'Statute / source'}</p>
      {src.section_reference ? <p className="text-xs text-slate-600">Section: {src.section_reference}</p> : null}
      {src.relevance ? <p className="mt-1 text-slate-800">{src.relevance}</p> : null}
      {src.source_origin ? <p className="mt-1 text-xs text-slate-600">Origin: {src.source_origin}</p> : null}
    </div>
  );
}

type FullReportModalProps = {
  open: boolean;
  loading: boolean;
  fullReport: Record<string, unknown> | null;
  limitedBanner: boolean;
  onClose: () => void;
  onContinueChat?: () => void;
};

export function FullReportModal({
  open,
  loading,
  fullReport,
  limitedBanner,
  onClose,
  onContinueChat,
}: FullReportModalProps) {
  if (!open) {
    return null;
  }

  const fr = fullReport ?? {};
  const scenarioSummary = scrubParagraph(fr.scenario_summary);
  const simplified = scrubParagraph(fr.simplified_explanation);
  const facts = asStringArray(fr.facts_identified);
  const missing = asStringArray(fr.missing_facts);
  const rights = asStringArray(fr.rights_possibly_involved);
  const remedies = asStringArray(fr.possible_remedies);
  const outcomes = asStringArray(fr.possible_outcomes);
  const reasoning = filterReasoning(asStringArray(fr.reasoning_trace));
  const grounding = scrubParagraph(fr.source_grounding_status);
  const refs = Array.isArray(fr.official_sources_referenced) ? (fr.official_sources_referenced as unknown[]) : [];
  const disclaimer = scrubParagraph(fr.disclaimer) || String(fr.disclaimer || '').trim();
  const issueLabel = scrubParagraph(fr.issue_type) || scrubParagraph(fr.detected_domain);
  const confidence = String(fr.confidence || '').trim();

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center px-3 py-6 sm:px-4">
      <button type="button" className="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px]" aria-label="Close modal backdrop" onClick={onClose} />
      <div className="relative z-10 flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-amber-200/70 bg-[#fffaf1] shadow-glow">
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-amber-200/70 px-5 py-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Full legal awareness report</h3>
            <p className="text-xs text-slate-600">Structured view — not legal advice.</p>
            {confidence && confidence !== '—' ? (
              <p className="mt-1 text-[11px] uppercase tracking-wide text-slate-500">Model confidence: {confidence}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-amber-200/70 px-4 py-1.5 text-sm text-slate-700 transition hover:border-amber-300/70 hover:text-slate-900"
          >
            Close
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <p className="text-sm text-slate-600">Loading report…</p>
          ) : (
            <div className="space-y-3">
              {limitedBanner ? (
                <div className="rounded-2xl border border-amber-200/80 bg-amber-50/90 p-4 text-sm leading-relaxed text-slate-800">
                  <p>
                    Detailed report is limited for this scenario. Continue the guided chat to clarify key facts
                    before relying on any single summary.
                  </p>
                  {onContinueChat ? (
                    <button
                      type="button"
                      className="mt-3 rounded-full bg-electric px-5 py-2 text-sm font-semibold text-white hover:brightness-110"
                      onClick={() => {
                        onContinueChat();
                        onClose();
                      }}
                    >
                      Continue chat
                    </button>
                  ) : null}
                </div>
              ) : null}

              {issueLabel ? (
                <ReportSection title="Detected issue">
                  <p>{issueLabel.replace(/_/g, ' ')}</p>
                </ReportSection>
              ) : null}

              {scenarioSummary ? (
                <ReportSection title="Scenario summary">
                  <p>{scenarioSummary}</p>
                </ReportSection>
              ) : null}

              {simplified ? (
                <ReportSection title="Simplified explanation">
                  <p>{simplified}</p>
                </ReportSection>
              ) : null}

              {facts.length > 0 ? (
                <ReportSection title="Facts identified">
                  <Bullets items={facts} />
                </ReportSection>
              ) : null}

              {missing.length > 0 ? (
                <ReportSection title="Missing facts">
                  <Bullets items={missing} />
                </ReportSection>
              ) : null}

              {rights.length > 0 ? (
                <ReportSection title="Possible rights">
                  <Bullets items={rights} />
                </ReportSection>
              ) : null}

              {remedies.length > 0 ? (
                <ReportSection title="Possible remedies">
                  <Bullets items={remedies} />
                </ReportSection>
              ) : null}

              {outcomes.length > 0 ? (
                <ReportSection title="Possible outcomes">
                  <Bullets items={outcomes} />
                </ReportSection>
              ) : null}

              {reasoning.length > 0 ? (
                <ReportSection title="Reasoning trace">
                  <Bullets items={reasoning} />
                </ReportSection>
              ) : null}

              {grounding ? (
                <ReportSection title="Source grounding status">
                  <p>{grounding}</p>
                </ReportSection>
              ) : null}

              {refs.length > 0 ? (
                <ReportSection title="Official sources referenced">
                  <div className="space-y-2">
                    {refs.map((item, i) => (
                      <SourceRow key={i} src={isRecord(item) ? (item as OfficialSourceRow) : { act_name: String(item) }} />
                    ))}
                  </div>
                </ReportSection>
              ) : null}

              {disclaimer ? (
                <ReportSection title="Disclaimer">
                  <p>{disclaimer}</p>
                </ReportSection>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
