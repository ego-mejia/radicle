import { describe, expect, it } from 'vitest';
import { fromDraft, parseLabels, toDraft, validate, type Metadata } from './validate';

const CATALOGS = { doc_types: ['how-to'], audiences: ['everyone'], languages: ['es'] };
const GOOD: Metadata = {
  description: 'Cómo conectar un agente a Radicle por MCP, paso a paso y con el token.',
  doc_type: 'how-to',
  labels: ['mcp'],
  owner: 'fernando',
  audiences: ['everyone'],
  language: 'es',
  docket_project: '',
  docket_milestones: [],
  docket_areas: [],
};

describe('publishing rules', () => {
  it('accept complete metadata', () => {
    expect(validate('Guía', GOOD, CATALOGS)).toEqual({});
  });

  it('name every field that fails, like the server', () => {
    const bad = { ...GOOD, description: 'Corta.', doc_type: 'x', labels: [], owner: ' ' };
    expect(validate('', { ...bad, audiences: ['nadie'], language: '' }, CATALOGS)).toEqual({
      title: 'rules.title',
      description: 'rules.descriptionLength',
      doc_type: 'rules.docType',
      labels: 'rules.labelsCount',
      owner: 'rules.owner',
      audiences: 'rules.audiences',
      language: 'rules.language',
    });
    const long = 'Una oración larga de verdad. Otra más. Y otra. Y la cuarta sobra.';
    expect(validate('Guía', { ...GOOD, description: long }, CATALOGS).description).toBe(
      'rules.descriptionSentences',
    );
    expect(validate('Guía', { ...GOOD, labels: ['Mal Label'] }, CATALOGS).labels).toBe(
      'rules.labelsFormat',
    );
  });

  it('read labels and the draft the way the server normalizes them', () => {
    expect(parseLabels('#Onboarding, mcp  mcp,')).toEqual(['onboarding', 'mcp']);
    expect(fromDraft({ owner: '@ana', labels: ['x'] }, 'luis')).toMatchObject({
      owner: 'ana',
      labels: ['x'],
      description: '',
    });
    expect(fromDraft({}, 'luis').owner).toBe('luis');
  });

  it('save the Docket links only when a project is set', () => {
    expect(toDraft(GOOD)).not.toHaveProperty('docket_project');
    const linked = { ...GOOD, docket_project: 'PA', docket_milestones: ['V1'] };
    expect(toDraft(linked)).toMatchObject({ docket_project: 'PA', docket_milestones: ['V1'] });
  });
});
