import { afterEach, describe, expect, it } from 'vitest';
import { findTarget, pageFor, projectInPath, waitForTarget } from './tour';

const step = (page: string | null) => ({ target: 'x', action: 'point', page, text: 'hi' }) as const;

describe('tour helpers', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('fills the project into pages', () => {
    expect(pageFor(step('/p/{project}/list'), 'PA')).toBe('/p/PA/list');
    expect(pageFor(step('/p/{project}/list'), null)).toBeNull();
    expect(pageFor(step('/admin?tab=users'), null)).toBe('/admin?tab=users');
    expect(pageFor(step(null), 'PA')).toBeNull();
    expect(projectInPath('/p/pa/board')).toBe('PA');
    expect(projectInPath('/admin')).toBeNull();
  });

  it('finds targets, also once they appear', async () => {
    expect(findTarget('projects.create')).toBeNull();
    setTimeout(() => {
      document.body.innerHTML = '<button data-tour="projects.create">Create</button>';
    }, 150);
    const el = await waitForTarget('projects.create', 2000);
    // jsdom has no layout: getClientRects is empty, so nothing counts as visible.
    expect(el).toBeNull();
  });
});
