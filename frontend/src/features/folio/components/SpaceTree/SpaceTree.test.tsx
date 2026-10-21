import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { FolioTreeItem } from '../../../../services/api/folio';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { moveFor } from './moves';
import { SpaceTree } from '.';

const node = (id: string, title: string, kind = 'page', children: FolioTreeItem[] = []) =>
  ({ id, kind, title, slug: title.toLowerCase(), icon: null, children }) as FolioTreeItem;

const TREE = [
  node('f1', 'Guías', 'folder', [
    node('p1', 'Deploy'),
    node('p2', 'Agentes', 'page', [node('p3', 'MCP')]),
  ]),
  node('p4', 'Intro'),
];

describe('moveFor', () => {
  it('places before a sibling, inside a page or at the root', () => {
    expect(moveFor('p4', 'before:p1', TREE)).toEqual({ parent: 'f1', before: 'p1' });
    expect(moveFor('p4', 'into:p2', TREE)).toEqual({ parent: 'p2' });
    expect(moveFor('p3', 'root', TREE)).toEqual({ parent: null });
    expect(moveFor('p4', 'before:f1', TREE)).toEqual({ parent: null, before: 'f1' });
  });

  it('never moves a node into itself or its descendants', () => {
    expect(moveFor('p2', 'into:p2', TREE)).toBeNull();
    expect(moveFor('f1', 'into:p3', TREE)).toBeNull();
    expect(moveFor('p4', 'root', TREE)).toBeNull(); // already at the root
  });
});

describe('SpaceTree', () => {
  it('links pages, shows folders and collapses a branch', async () => {
    mockFetch({});
    renderWithProviders(<SpaceTree space="docs" items={TREE} current="p1" />);
    const deploy = await screen.findByRole('link', { name: 'Deploy' });
    expect(deploy).toHaveAttribute('href', '/folio/p/p1-deploy');
    expect(deploy).toHaveAttribute('aria-current', 'page');
    expect(screen.queryByRole('link', { name: 'Guías' })).toBeNull();
    expect(screen.queryByRole('button', { name: /Move/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Collapse Guías' }));
    expect(screen.queryByRole('link', { name: 'Deploy' })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Expand Guías' }));
    expect(screen.getByRole('link', { name: 'MCP' })).toBeInTheDocument();
  });

  it('offers drag handles and the root drop zone to those who can move', async () => {
    mockFetch({});
    renderWithProviders(<SpaceTree space="docs" items={TREE} canMove />);
    expect(await screen.findByRole('button', { name: 'Move Deploy' })).toBeInTheDocument();
    expect(screen.getByText('Drop here to move to the top level')).toBeInTheDocument();
  });

  it('says when the space is empty', async () => {
    renderWithProviders(<SpaceTree space="docs" items={[]} />);
    expect(await screen.findByText('No pages yet.')).toBeInTheDocument();
  });
});
