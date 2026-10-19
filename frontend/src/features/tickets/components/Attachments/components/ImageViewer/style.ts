import styled from 'styled-components';

export const Stage = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: ${({ theme }) => theme.space.sm};

  img {
    max-width: 100%;
    max-height: 70vh;
    border-radius: ${({ theme }) => theme.radius.md};
  }
`;

export const Caption = styled.p`
  margin: 0;
  text-align: center;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
