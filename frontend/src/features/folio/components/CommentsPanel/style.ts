import styled from 'styled-components';

export const Panel = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Header = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
  }
`;

export const Filters = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.xs};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

export const Filter = styled.button<{ $on: boolean }>`
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border: 0;
  border-bottom: 2px solid ${({ theme, $on }) => ($on ? theme.color.accent : 'transparent')};
  background: transparent;
  color: ${({ theme, $on }) => ($on ? theme.color.text : theme.color.textMuted)};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: ${({ $on }) => ($on ? 600 : 500)};
  cursor: pointer;
`;

export const Count = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Compose = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: ${({ theme }) => theme.space.sm};

  > :first-child {
    align-self: stretch;
  }
`;

export const Empty = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
