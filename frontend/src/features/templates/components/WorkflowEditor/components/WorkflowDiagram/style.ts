import styled from 'styled-components';

export const Box = styled.div`
  min-height: 160px;
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.textMuted};
  overflow: auto;

  svg {
    max-width: 100%;
    height: auto;
  }
`;
