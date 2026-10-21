import styled from 'styled-components';

export const Layout = styled.div`
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  gap: ${({ theme }) => theme.space.xl};
  align-items: start;
  margin-top: ${({ theme }) => theme.space.lg};

  @media (max-width: 860px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Item = styled.button<{ $selected: boolean }>`
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.lg};
  border: 1px solid
    ${({ $selected, theme }) => ($selected ? theme.color.accent : theme.color.border)};
  background: ${({ $selected, theme }) => ($selected ? theme.color.accentSoft : theme.color.surface)};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  text-align: left;
  cursor: pointer;

  strong {
    font-size: ${({ theme }) => theme.fontSize.lg};
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
