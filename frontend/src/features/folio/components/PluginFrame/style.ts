import styled from 'styled-components';

export const Off = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin: ${({ theme }) => theme.space.lg} 0;
  padding: ${({ theme }) => theme.space.lg};
  color: ${({ theme }) => theme.color.textMuted};
  border: 1px dashed ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};

  svg {
    width: 16px;
    height: 16px;
  }
`;
