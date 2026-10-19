import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.xxl} ${theme.space.lg}`};
`;

export const Title = styled.h3`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.lg};
  font-weight: 700;
`;

export const Text = styled.p`
  margin: 0;
  max-width: 360px;
  color: ${({ theme }) => theme.color.textMuted};
`;
