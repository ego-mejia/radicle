import styled from 'styled-components';

export type Category = 'todo' | 'in_progress' | 'done';

export const Chip = styled.span`
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  max-width: 100%;
  padding: 0 6px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.surface2};
  font-size: 0.92em;
  line-height: 1.6;
  vertical-align: baseline;

  a {
    color: inherit;
    text-decoration: none;
  }
`;

export const Key = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-weight: 600;
  white-space: nowrap;
`;

export const Title = styled.span`
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 28ch;
`;

export const State = styled.span<{ $category: Category }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
  white-space: nowrap;

  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${({ theme, $category }) =>
      ({
        todo: theme.color.catTodo,
        in_progress: theme.color.catProgress,
        done: theme.color.catDone,
      })[$category]};
  }
`;

export const Muted = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: nowrap;
`;
