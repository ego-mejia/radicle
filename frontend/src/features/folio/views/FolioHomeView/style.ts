import styled from 'styled-components';

export const Wrap = styled.div`
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
`;

export const Top = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
`;

export const Actions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Heading = styled.h1`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.xxl};
  letter-spacing: -0.02em;
`;
