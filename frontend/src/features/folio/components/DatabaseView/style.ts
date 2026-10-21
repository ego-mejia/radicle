import styled from 'styled-components';

export const Wrap = styled.div<{ $embedded: boolean }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  margin: ${({ theme, $embedded }) => ($embedded ? `${theme.space.lg} 0` : 0)};
`;

export const Caption = styled.div`
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;

  span {
    font-weight: 400;
    color: ${({ theme }) => theme.color.textMuted};
  }
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

export const Toolbar = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Error = styled.p`
  color: ${({ theme }) => theme.color.danger};
`;

export const Empty = styled.p`
  padding: ${({ theme }) => theme.space.xl};
  text-align: center;
  color: ${({ theme }) => theme.color.textMuted};
`;
