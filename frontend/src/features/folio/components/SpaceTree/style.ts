import styled, { css } from 'styled-components';

export const Nav = styled.nav`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

const dropRing = css`
  outline: 2px dashed ${({ theme }) => theme.color.accent};
  outline-offset: -2px;
`;

export const Row = styled.div<{
  $depth: number;
  $current: boolean;
  $over: boolean;
  $dragging: boolean;
}>`
  position: relative;
  display: flex;
  align-items: center;
  gap: 2px;
  min-height: 36px;
  padding-left: ${({ $depth }) => `${4 + $depth * 16}px`};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme, $current }) => ($current ? theme.color.accentSoft : 'transparent')};
  opacity: ${({ $dragging }) => ($dragging ? 0.5 : 1)};
  ${({ $over }) => $over && dropRing};

  &:hover {
    background: ${({ theme, $current }) => ($current ? theme.color.accentSoft : theme.color.surface2)};
  }
`;

/** A thin strip over the top of a row: dropping there places the node before it. */
export const Before = styled.div<{ $over: boolean }>`
  position: absolute;
  inset: -3px 0 auto 0;
  height: 8px;
  border-top: 2px solid ${({ theme, $over }) => ($over ? theme.color.accent : 'transparent')};
`;

const square = css`
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Toggle = styled.button`
  ${square};
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.textMuted};
  border-radius: ${({ theme }) => theme.radius.md};
  cursor: pointer;
`;

export const Spacer = styled.span`
  ${square};
`;

const label = css`
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => `${theme.space.xs} 0`};
  font-size: ${({ theme }) => theme.fontSize.lg};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &[aria-current='page'] {
    font-weight: 600;
    color: ${({ theme }) => theme.color.onAccent};
  }

  svg {
    flex: 0 0 15px;
    width: 15px;
    height: 15px;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Label = styled.span`
  ${label};
`;

/** Holds the page's <Link>, styled like a label. */
export const PageLink = styled.span`
  flex: 1;
  min-width: 0;
  display: flex;

  > a {
    ${label};
  }
`;

export const Handle = styled.button`
  ${square};
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.textMuted};
  border-radius: ${({ theme }) => theme.radius.md};
  cursor: grab;
  opacity: 0;

  ${Row}:hover &,
  &:focus-visible {
    opacity: 1;
  }
`;

export const Root = styled.div<{ $over: boolean }>`
  padding: ${({ theme }) => theme.space.sm};
  border: 1px dashed ${({ theme, $over }) => ($over ? theme.color.accent : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.lg};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
  text-align: center;
`;

export const Empty = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;

/** The title, cut with an ellipsis: text inside a flex row needs its own box for it. */
export const Text = styled.span`
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;
