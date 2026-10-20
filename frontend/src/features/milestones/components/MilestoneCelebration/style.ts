import styled from 'styled-components';

export const Hero = styled.div`
  text-align: center;
  margin-bottom: ${({ theme }) => theme.space.lg};
`;

export const Headline = styled.h2`
  margin: ${({ theme }) => theme.space.sm} 0 ${({ theme }) => theme.space.xs};
  font-size: ${({ theme }) => theme.fontSize.xl};
  font-weight: 800;
  color: ${({ theme }) => theme.color.text};
`;

export const Thanks = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
  line-height: 1.5;
  color: ${({ theme }) => theme.color.textMuted};
`;
