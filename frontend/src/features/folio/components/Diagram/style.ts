import styled from 'styled-components';

export const Figure = styled.figure`
  margin: 0;

  figcaption {
    margin-top: ${({ theme }) => theme.space.xs};
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
    text-align: center;
  }
`;

export const Drawing = styled.div`
  min-height: 80px;
  display: flex;
  justify-content: center;
  overflow-x: auto;

  svg {
    max-width: 100%;
    height: auto;
  }
`;

export const Error = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.danger};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.sm};

  pre {
    margin: 0;
    overflow-x: auto;
    color: ${({ theme }) => theme.color.textMuted};
    font-family: ${({ theme }) => theme.fonts.mono};
  }
`;
