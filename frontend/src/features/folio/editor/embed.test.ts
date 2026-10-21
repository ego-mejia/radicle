import { describe, expect, it } from 'vitest';
import { loneLink } from './embed';

describe('loneLink', () => {
  it('takes a single http(s) link and nothing else', () => {
    expect(loneLink('  https://youtu.be/dQw4w9WgXcQ \n')).toBe('https://youtu.be/dQw4w9WgXcQ');
    expect(loneLink('http://example.com/a?b=c')).toBe('http://example.com/a?b=c');
    expect(loneLink('mira https://example.com')).toBeNull();
    expect(loneLink('javascript:alert(1)')).toBeNull();
    expect(loneLink('ftp://example.com')).toBeNull();
  });
});
