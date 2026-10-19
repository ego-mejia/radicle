import styled, { keyframes } from 'styled-components';

const spin = keyframes`to { transform: rotate(360deg) }`;

export const Ring = styled.span<{ $size: number }>`
  display: inline-block;
  width: ${({ $size }) => $size}px;
  height: ${({ $size }) => $size}px;
  border: 2px solid ${({ theme }) => theme.color.border};
  border-top-color: ${({ theme }) => theme.color.accent};
  border-radius: 50%;
  animation: ${spin} 0.7s linear infinite;
`;

export const Center = styled.div`
  display: grid;
  place-items: center;
  padding: ${({ theme }) => theme.space.xxl};
`;
