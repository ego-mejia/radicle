import styled from 'styled-components';

export const Layout = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: ${({ theme }) => theme.space.xl};
  align-items: start;

  @media (max-width: 1100px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const Main = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
  min-width: 0;
`;

export const Conflict = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
  flex-wrap: wrap;
  padding: 10px 12px;
  border: 1px solid ${({ theme }) => theme.color.warning};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.warning};
  font-weight: 600;
`;

export const Activity = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Restricted = styled.p`
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 6px ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.warning};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
