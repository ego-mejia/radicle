import styled from 'styled-components';

export const Bar = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  flex-wrap: wrap;
  margin-bottom: ${({ theme }) => theme.space.lg};

  select {
    width: auto;
    min-width: 120px;
    height: 30px;
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;
