import { describe, expect, it } from 'vitest';
import { fromText } from './fromText';

describe('fromText', () => {
  it('turns paragraphs and bullets into nodes without Markdown marks', () => {
    expect(fromText('Un **resumen**.\n\n- Uno\n* Dos\n\n')).toEqual([
      { type: 'paragraph', content: [{ type: 'text', text: 'Un resumen.' }] },
      {
        type: 'bulletList',
        content: ['Uno', 'Dos'].map((text) => ({
          type: 'listItem',
          content: [{ type: 'paragraph', content: [{ type: 'text', text }] }],
        })),
      },
    ]);
    expect(fromText('  \n\n')).toEqual([]);
  });
});
