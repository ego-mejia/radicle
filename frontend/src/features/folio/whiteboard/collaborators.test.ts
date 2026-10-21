import { describe, expect, it } from 'vitest';
import { collaborators } from './collaborators';

const NOW = 1_000_000;

describe('collaborators', () => {
  it('draws each peer with their name and color, and hides idle pointers', () => {
    const shown = collaborators(
      [
        {
          clientId: 1,
          name: 'Ana',
          color: '#2563EB',
          agent: false,
          pointer: { x: 4, y: 5, at: NOW },
        },
        {
          clientId: 2,
          name: 'Beto',
          color: '#DB2777',
          agent: false,
          pointer: { x: 1, y: 1, at: 0 },
        },
        { clientId: 3, name: 'Caro', color: '#059669', agent: false },
      ],
      NOW,
    );
    expect(shown.get('1' as never)).toEqual({
      username: 'Ana',
      color: { background: '#2563EB', stroke: '#2563EB' },
      pointer: { x: 4, y: 5, tool: 'pointer' },
    });
    expect(shown.get('2' as never)?.pointer).toBeUndefined();
    expect(shown.get('3' as never)?.username).toBe('Caro');
  });
});
