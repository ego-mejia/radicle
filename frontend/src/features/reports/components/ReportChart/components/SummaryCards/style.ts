import styled from 'styled-components';

export const Grid = styled.dl`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: ${({ theme }) => theme.space.md};
  margin: 0;
`;

export const Card = styled.div<{ $tone?: 'warning' | 'accent' }>`
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid
    ${({ theme, $tone }) => ($tone === 'warning' ? theme.color.warning : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};

  dt {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }

  dd {
    margin: 4px 0 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
    font-weight: 700;
    color: ${({ theme, $tone }) =>
      $tone === 'warning'
        ? theme.color.warning
        : $tone === 'accent'
          ? theme.color.accent
          : theme.color.text};
  }
`;
