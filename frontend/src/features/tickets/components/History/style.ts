import styled from 'styled-components';

export const List = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
`;

export const Event = styled.li`
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  &:last-child {
    border-bottom: 0;
  }
`;

export const Line = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: ${({ theme }) => theme.fontSize.md};

  strong {
    font-weight: 600;
  }

  time {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;

export const Change = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Old = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  text-decoration: line-through;
`;

export const New = styled.span`
  color: ${({ theme }) => theme.color.text};
  font-weight: 600;
`;

export const Diff = styled.pre`
  margin: 6px 0 0;
  padding: 8px;
  max-height: 300px;
  overflow: auto;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface2};
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: pre-wrap;
`;

export const DiffLine = styled.span<{ $kind: 'same' | 'added' | 'removed' }>`
  display: block;
  color: ${({ theme, $kind }) =>
    $kind === 'added'
      ? theme.color.accent
      : $kind === 'removed'
        ? theme.color.danger
        : theme.color.textMuted};

  &::before {
    content: '${({ $kind }) => ($kind === 'added' ? '+ ' : $kind === 'removed' ? '- ' : '  ')}';
  }
`;

export const Toggle = styled.button`
  all: unset;
  color: ${({ theme }) => theme.color.accent};
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;
`;
