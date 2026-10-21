import styled from 'styled-components';

export const Name = styled.span`
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;

  strong {
    font-weight: 600;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Key = styled.code`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.accent};
`;

export const Archived = styled.div`
  opacity: 0.6;
`;

export const Edit = styled.form`
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: ${({ theme }) => theme.space.sm};
  flex: 1;
  min-width: 0;

  > * {
    flex: 1 1 180px;
  }

  > button {
    flex: 0 0 auto;
  }
`;
