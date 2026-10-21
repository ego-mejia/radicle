import styled from 'styled-components';

export const Embed = styled.figure`
  margin: ${({ theme }) => theme.space.lg} 0;
`;

export const Head = styled.figcaption`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin-bottom: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};

  a {
    color: inherit;
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Canvas = styled.div`
  height: 420px;
`;

export const NoAccess = styled.div`
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

export const Error = styled.div`
  margin: ${({ theme }) => theme.space.lg} 0;
  color: ${({ theme }) => theme.color.danger};
`;
