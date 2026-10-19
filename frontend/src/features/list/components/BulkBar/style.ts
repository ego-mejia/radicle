import styled from 'styled-components';

export const Bar = styled.div`
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin: 0 ${({ theme }) => theme.space.xl} ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.lg};
  border: 1px solid ${({ theme }) => theme.color.accent};
  background: ${({ theme }) => theme.color.accentSoft};

  @media (max-width: 640px) {
    margin: 0 ${({ theme }) => theme.space.lg} ${({ theme }) => theme.space.sm};
  }
`;

export const Spacer = styled.span`
  flex: 1;
`;
