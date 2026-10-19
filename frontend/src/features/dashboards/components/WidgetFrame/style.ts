import styled from 'styled-components';

export const Frame = styled.section`
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  overflow: hidden;
`;

export const Head = styled.header`
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px ${({ theme }) => theme.space.sm} 6px ${({ theme }) => theme.space.md};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  h3 {
    flex: 1;
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.md};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  button svg {
    width: 14px;
    height: 14px;
  }
`;

export const Handle = styled.span`
  display: inline-flex;
  cursor: grab;
  color: ${({ theme }) => theme.color.textMuted};

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Body = styled.div`
  flex: 1;
  min-height: 0;
  padding: ${({ theme }) => theme.space.md};
`;
