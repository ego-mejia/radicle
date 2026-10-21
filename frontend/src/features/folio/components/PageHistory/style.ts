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
  grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
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

export const Item = styled.li<{ $selected: boolean }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.lg};
  border: 1px solid
    ${({ $selected, theme }) => ($selected ? theme.color.accent : theme.color.border)};
  background: ${({ theme }) => theme.color.surface};
`;

export const Top = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  strong {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

export const Number = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  color: ${({ theme }) => theme.color.accent};
`;

export const Meta = styled.small`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Note = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Picks = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};
  font-size: ${({ theme }) => theme.fontSize.md};

  label {
    display: inline-flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.xs};
  }
`;

export const Panel = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl};
  border-radius: ${({ theme }) => theme.radius.lg};
  border: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.surface};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
  }
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
