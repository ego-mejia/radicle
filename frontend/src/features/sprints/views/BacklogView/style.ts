import styled from 'styled-components';

export const Bar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: 0 ${({ theme }) => theme.space.xl} ${({ theme }) => theme.space.md};

  select {
    width: auto;
  }

  @media (max-width: 640px) {
    padding: 0 ${({ theme }) => theme.space.lg} ${({ theme }) => theme.space.md};
  }
`;

export const Selection = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Spacer = styled.span`
  flex: 1;
`;

export const Lists = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
  padding: 0 ${({ theme }) => theme.space.xl} ${({ theme }) => theme.space.xl};
  max-width: 1100px;

  @media (max-width: 640px) {
    padding: 0 ${({ theme }) => theme.space.lg} ${({ theme }) => theme.space.lg};
  }
`;
