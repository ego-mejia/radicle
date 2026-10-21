import styled from 'styled-components';

export const Box = styled.section`
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  overflow-x: auto;
`;

export const Head = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.sm};
  margin-bottom: ${({ theme }) => theme.space.sm};

  strong {
    font-size: ${({ theme }) => theme.fontSize.md};
  }
`;

export const List = styled.ul`
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Item = styled.li`
  display: grid;
  grid-template-columns: 3.5em minmax(8em, 1fr) auto auto auto 5em;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.xs} 0;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  &:last-child {
    border-bottom: 0;
  }
`;

export const Key = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-family: ${({ theme }) => theme.fonts.mono};
`;

export const Title = styled.span`
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

export const Pending = styled.span`
  grid-column: 3 / -1;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Bar = styled.span<{ $done: number }>`
  padding: 0 ${({ theme }) => theme.space.xs};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: linear-gradient(
    to right,
    ${({ theme }) => theme.color.accentSoft} ${({ $done }) => $done * 100}%,
    ${({ theme }) => theme.color.surface2} ${({ $done }) => $done * 100}%
  );
  text-align: center;
  font-variant-numeric: tabular-nums;
`;

export const Muted = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;
