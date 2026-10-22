import { describe, expect, it } from 'vitest';
import { findBlocks } from './blocks';
import { pluginBlockItems, pluginCode, setPluginBlocks } from './pluginBlocks';
import { COUNTDOWN } from '../components/PluginBlockEditor/fixtures';

describe('plugin blocks', () => {
  it('become / menu entries that start with their defaults', () => {
    setPluginBlocks([COUNTDOWN]);
    const [item] = pluginBlockItems();
    expect(item).toMatchObject({
      key: 'plugin:radicle.countdown/countdown',
      label: '⏳ Cuenta regresiva',
    });
    expect(findBlocks(pluginBlockItems(), 'cuenta', (k) => k)).toHaveLength(1);
    let inserted: unknown;
    const chain = { insertContent: (c: unknown) => ((inserted = c), chain) };
    item!.run(chain as never);
    expect(inserted).toEqual({
      type: 'pluginBlock',
      attrs: { plugin: 'radicle.countdown', block: 'countdown', data: { title: 'Lanzamiento' } },
    });
    setPluginBlocks([]);
    expect(pluginBlockItems()).toEqual([]);
  });

  it('hands the values to the HTML without letting them close the script', () => {
    const code = pluginCode('<p>x</p>', { title: '</script><b>' });
    expect(code).toBe(
      '<script>window.radicle={"data":{"title":"\\u003c/script>\\u003cb>"}};</script><p>x</p>',
    );
  });
});
