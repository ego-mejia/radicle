import styled from 'styled-components';

export const Back = styled.span`
  a {
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 ${({ theme }) => theme.space.lg};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.lg};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
    font-size: ${({ theme }) => theme.fontSize.md};
    font-weight: 500;
    text-decoration: none;
  }
`;

export const Layout = styled.div`
  display: grid;
  grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
  gap: ${({ theme }) => theme.space.xl};
  align-items: start;

  @media (max-width: 860px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const List = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Item = styled.button<{ $selected: boolean }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  width: 100%;
  padding: ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.lg};
  border: 1px solid
    ${({ $selected, theme }) => ($selected ? theme.color.accent : theme.color.border)};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  text-align: left;
  cursor: pointer;
`;

export const Meta = styled.small`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Panel = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl};
  border-radius: ${({ theme }) => theme.radius.lg};
  border: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.surface};
`;

export const PanelTop = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
  }
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
