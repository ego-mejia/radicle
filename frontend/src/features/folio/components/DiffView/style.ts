import styled, { css } from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
`;

export const Section = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  h3 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }
`;

export const Block = styled.div<{ $op: 'equal' | 'added' | 'removed' }>`
  display: flex;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border-radius: ${({ theme }) => theme.radius.md};
  white-space: pre-wrap;
  line-height: 1.6;
  color: ${({ theme }) => theme.color.text};
  ${({ $op, theme }) =>
    $op === 'added' &&
    css`
      background: ${theme.color.accentSoft};
    `}
  ${({ $op, theme }) =>
    $op === 'removed' &&
    css`
      background: ${theme.color.surface2};
      color: ${theme.color.textMuted};
      text-decoration: line-through;
    `}
`;

export const Sign = styled.span`
  flex: 0 0 auto;
  width: 16px;
  font-family: ${({ theme }) => theme.fonts.mono};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.md};

  th,
  td {
    text-align: left;
    padding: ${({ theme }) => theme.space.sm};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    vertical-align: top;
  }

  th {
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 600;
  }
`;

export const Before = styled.td`
  color: ${({ theme }) => theme.color.textMuted};
  text-decoration: line-through;
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

/** A block as the reader sees it, without the page's outer spacing. */
export const Rendered = styled.div`
  flex: 1;
  min-width: 0;
  > * > *:first-child {
    margin-top: 0;
  }
  > * > *:last-child {
    margin-bottom: 0;
  }
`;
