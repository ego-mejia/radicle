import styled from 'styled-components';

export const Board = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.md};
  overflow-x: auto;
  padding-bottom: ${({ theme }) => theme.space.sm};
`;

export const Group = styled.section<{ $over: boolean }>`
  flex: 0 0 260px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.sm};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface2};
  outline: 2px solid ${({ theme, $over }) => ($over ? theme.color.accent : 'transparent')};
`;

export const Label = styled.h3`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0;
  padding: ${({ theme }) => theme.space.xs};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Cards = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  min-height: 40px;
`;

export const Card = styled.div<{ $dragging: boolean }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  opacity: ${({ $dragging }) => ($dragging ? 0.6 : 1)};
  z-index: ${({ $dragging }) => ($dragging ? 1 : 'auto')};
  cursor: ${({ $dragging }) => ($dragging ? 'grabbing' : 'grab')};
  touch-action: none;
`;
