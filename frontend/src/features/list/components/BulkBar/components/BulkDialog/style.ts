import styled from 'styled-components';

export const Form = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Summary = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  max-height: 320px;
  overflow: auto;

  p {
    margin: 0;
  }
`;

export const Failure = styled.div`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.danger};

  strong {
    font-family: ${({ theme }) => theme.fonts.mono};
    margin-right: 6px;
  }
`;

export const Progress = styled.div`
  height: 8px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  overflow: hidden;

  span {
    display: block;
    height: 100%;
    background: ${({ theme }) => theme.color.accentFill};
    transition: width 0.3s;
  }
`;
