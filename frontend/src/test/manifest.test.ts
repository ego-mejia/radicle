import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const publicDir = resolve(__dirname, '../../public');

describe('app manifest', () => {
  it('makes Radicle installable as its own app, with Radi as the icon', () => {
    const manifest = JSON.parse(readFileSync(resolve(publicDir, 'manifest.json'), 'utf8'));
    expect(manifest).toMatchObject({ name: 'Radicle', start_url: '/', display: 'standalone' });
    const sizes = manifest.icons.map((icon: { sizes: string }) => icon.sizes);
    expect(sizes).toEqual(expect.arrayContaining(['192x192', '512x512']));
    for (const icon of manifest.icons)
      expect(existsSync(resolve(publicDir, `.${icon.src}`))).toBe(true);
    const html = readFileSync(resolve(publicDir, '../index.html'), 'utf8');
    expect(html).toContain('<link rel="manifest" href="/manifest.json" />');
  });

  it('has a real favicon.ico, so /favicon.ico is not the HTML page', () => {
    expect(existsSync(resolve(publicDir, 'favicon.ico'))).toBe(true);
  });
});
