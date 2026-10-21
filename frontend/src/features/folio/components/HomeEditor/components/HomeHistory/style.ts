import styled from 'styled-components';

export const Wrap = styled.section`
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
`;

export const Row = styled.li`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
  min-height: 44px;
  padding: ${({ theme }) => theme.space.sm} 0;

  & + & {
    border-top: 1px solid ${({ theme }) => theme.color.surface2};
  }
`;

export const Text = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: ${({ theme }) => theme.fontSize.md};

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
