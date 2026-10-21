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

export const Heading = styled.h1`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.xxl};
  letter-spacing: -0.02em;
`;

/** A bento row: its cards wrap under each other on narrow screens. */
export const Row = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.xl};
`;

export const Column = styled.div<{ $grow: number; $basis: number }>`
  flex: ${({ $grow, $basis }) => `${$grow} 1 ${$basis}px`};
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
`;
