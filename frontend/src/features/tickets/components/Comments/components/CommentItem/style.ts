import styled from 'styled-components';

export const Item = styled.article`
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: ${({ theme }) => theme.space.sm};
`;

export const Bubble = styled.div<{ $deleted: boolean }>`
  padding: 8px 12px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $deleted }) => ($deleted ? 'transparent' : theme.color.surface)};
  border-style: ${({ $deleted }) => ($deleted ? 'dashed' : 'solid')};
`;

export const Meta = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};

  strong {
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Spacer = styled.span`
  flex: 1;
`;

export const Deleted = styled.em`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Reactions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
`;

export const Reaction = styled.button<{ $mine: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  padding: 0 8px;
  border: 1px solid ${({ theme, $mine }) => ($mine ? theme.color.accent : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme, $mine }) => ($mine ? theme.color.accentSoft : 'transparent')};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;

  &:disabled {
    cursor: default;
  }
`;

export const EditActions = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  margin-top: ${({ theme }) => theme.space.sm};
`;
