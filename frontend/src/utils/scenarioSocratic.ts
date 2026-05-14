export type FirstSocraticInput = {
  issueType: string;
  detectedIssue: string;
  suggestedQuestions: string[];
};

function firstUsefulQuestion(suggested: string[]): string {
  for (const q of suggested) {
    const t = q.trim();
    if (t.length > 12) {
      const trimmed = t.replace(/\?+$/, '').trim();
      return trimmed.endsWith('?') ? trimmed : `${trimmed}?`;
    }
  }
  return '';
}

export function getFirstSocraticQuestion(input: FirstSocraticInput): string {
  const fromBackend = firstUsefulQuestion(input.suggestedQuestions);
  if (fromBackend) {
    return fromBackend;
  }

  const pack = (input.issueType || '').trim();
  const fallbacks: Record<string, string> = {
    partition_ancestral_property:
      'Who originally owned the property, and did that person leave a will?',
    mutation_vs_title: 'Whose name is currently shown in the mutation or revenue records?',
    sale_deed_dispute:
      'Do you have a registered sale deed, and do you have the previous title documents?',
    rera_delay: 'What was the promised possession date in your builder–buyer agreement?',
    tenant_eviction:
      'Do you have a written rental agreement, and has the landlord given written notice to vacate?',
  };

  if (pack && fallbacks[pack]) {
    return fallbacks[pack];
  }

  const d = (input.detectedIssue || '').toLowerCase();
  if (d.includes('mutation') || d.includes('revenue')) {
    return fallbacks.mutation_vs_title;
  }
  if (d.includes('rera') || d.includes('builder') || d.includes('possession')) {
    return fallbacks.rera_delay;
  }
  if (d.includes('tenant') || d.includes('landlord') || d.includes('lease')) {
    return fallbacks.tenant_eviction;
  }
  if (d.includes('sale') || d.includes('title')) {
    return fallbacks.sale_deed_dispute;
  }
  if (d.includes('ancestral') || d.includes('family') || d.includes('partition')) {
    return fallbacks.partition_ancestral_property;
  }

  return 'What documents do you currently have related to this issue?';
}
