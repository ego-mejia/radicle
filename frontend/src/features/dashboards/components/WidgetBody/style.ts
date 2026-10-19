import styled from 'styled-components';

export const Count = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;

  strong {
    font-size: 44px;
    line-height: 1;
  }

  span {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Scroll = styled.div`
  height: 100%;
  overflow: auto;
`;

export const Empty = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
