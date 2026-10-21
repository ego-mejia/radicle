import styled from 'styled-components';

export const Reactions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Reaction = styled.button<{ $mine: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  min-height: 28px;
  padding: ${({ theme }) => `0 ${theme.space.sm}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme, $mine }) => ($mine ? theme.color.accentSoft : theme.color.surface)};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;
`;
