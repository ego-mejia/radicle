import styled from 'styled-components';

export const Header = styled.header`
  display: grid;
  grid-template-columns: 1fr auto;
  gap: ${({ theme }) => theme.space.xs} ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl} ${({ theme }) => theme.space.xl} 0;

  > a {
    grid-column: 1 / -1;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
    text-decoration: none;
  }

  @media (max-width: 640px) {
    padding: ${({ theme }) => theme.space.lg} ${({ theme }) => theme.space.lg} 0;
    grid-template-columns: 1fr;
  }
`;

export const Title = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xxl};
  }
`;

export const Linked = styled.p`
  grid-column: 1;
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Actions = styled.div`
  grid-column: 2;
  grid-row: 2 / span 2;
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;

  @media (max-width: 640px) {
    grid-column: 1;
    grid-row: auto;
  }
`;

export const Body = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl};

  @media (max-width: 640px) {
    padding: ${({ theme }) => theme.space.lg};
  }
`;

export const Panel = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  min-width: 0;
`;
