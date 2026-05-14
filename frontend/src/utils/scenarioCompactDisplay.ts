import type { CompactViewShape } from '@/utils/scenarioReportMapping';

const GENERIC_SUMMARY = /property-related legal issue|your situation may involve property|appears to involve a property-related/i;

const GENERIC_SYSTEM = /the system could not fully analyze|could not process|could not fully verify|could not complete analysis/i;

const WEAK_STEP = /^(exact location\/state|relevant documents)\.?$/i;

export function isGenericOrWeakSummary(text: string): boolean {
  const t = text.trim();
  if (!t || t.length < 20) {
    return true;
  }
  return GENERIC_SUMMARY.test(t) || GENERIC_SYSTEM.test(t);
}

export function buildSituationOverview(
  compact: CompactViewShape,
  userScenario: string,
  extras?: { scenarioSummary?: string; simplifiedExplanation?: string },
): string {
  const parts: string[] = [];
  const sum = (extras?.scenarioSummary || '').trim();
  const expl = (extras?.simplifiedExplanation || '').trim();
  const short = compact.short_summary.trim();

  const candidates = [short, sum, expl].filter((p) => p && !GENERIC_SYSTEM.test(p) && !GENERIC_SUMMARY.test(p));

  let chosen = candidates[0] || '';
  if (!chosen || isGenericOrWeakSummary(chosen)) {
    const issue = compact.detected_issue || 'this legal issue';
    const snippet = userScenario.trim().replace(/\s+/g, ' ');
    const clip = snippet.length > 360 ? `${snippet.slice(0, 360)}…` : snippet;
    chosen = `This issue may require more details, but based on your input it appears related to ${issue}. You wrote: ${clip || 'your scenario above'}. The next step is to clarify the key facts through follow-up questions rather than assuming outcomes.`;
  }

  if (chosen.split(/\s+/).filter(Boolean).length < 18) {
    chosen += ` This overview is for general legal awareness only and is not legal advice.`;
  }

  parts.push(chosen);
  return parts.join('\n\n').trim();
}

export function polishMainPoints(points: string[], userScenario: string): string[] {
  const out: string[] = [];
  const scenario = userScenario.toLowerCase();
  for (const p of points) {
    const t = p.trim();
    if (!t || GENERIC_SYSTEM.test(t)) {
      continue;
    }
    if (WEAK_STEP.test(t)) {
      const nicer =
        t.toLowerCase().includes('document')
          ? 'Keep copies of relevant documents such as deeds, receipts, notices, and communication records.'
          : 'Clarify location or state only if it changes which law or forum may apply, and note it in your timeline.';
      if (!out.includes(nicer)) {
        out.push(nicer);
      }
      continue;
    }
    if (!out.includes(t)) {
      out.push(t);
    }
  }
  if (out.length === 0 && scenario.length > 15) {
    out.push(`Review how you described the parties, timeline, and what changed—those details drive most next steps.`);
  }
  if (out.length === 0) {
    out.push('Focus on what happened first, who was involved, and what documents or notices you have today.');
  }
  return out.slice(0, 8);
}

export function polishNextSteps(steps: string[]): string[] {
  const out: string[] = [];
  for (const s of steps) {
    const t = s.trim();
    if (!t) {
      continue;
    }
    if (WEAK_STEP.test(t)) {
      const nicer =
        t.toLowerCase().includes('document')
          ? 'Keep copies of relevant documents such as deeds, receipts, notices, and communication records.'
          : 'Note the state or region if it affects which law or forum may apply, and keep a short chronology.';
      if (!out.includes(nicer)) {
        out.push(nicer);
      }
      continue;
    }
    if (!out.includes(t)) {
      out.push(t);
    }
  }
  if (out.length === 0) {
    out.push('Organize your documents and write a short chronology of what happened and when.');
  }
  return out.slice(0, 8);
}

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) {
    return [];
  }
  return v.map((x) => (typeof x === 'string' ? x : String(x))).filter((s) => s.trim());
}

const TRACE_BAD =
  /fallback response generated|gemini\/parse attempts failed|could not be parsed|api call failed|debug_error|structured api output/i;

export function isLimitedFullReport(fr: Record<string, unknown>): boolean {
  const sum = String(fr.scenario_summary || '');
  if (GENERIC_SUMMARY.test(sum)) {
    return true;
  }
  const expl = String(fr.simplified_explanation || '');
  if (GENERIC_SYSTEM.test(expl)) {
    return true;
  }
  const trace = asStringArray(fr.reasoning_trace).join(' ');
  if (TRACE_BAD.test(trace)) {
    return true;
  }
  return false;
}
