import styled from 'styled-components';

export const Block = styled.div<{ $selected: boolean }>`
  position: relative;
  border-radius: ${({ theme }) => theme.radius.md};
  outline: 2px solid ${({ theme, $selected }) => ($selected ? theme.color.accent : 'transparent')};
  outline-offset: 2px;
`;

export const Edit = styled.button`
  position: absolute;
  top: ${({ theme }) => theme.space.xs};
  right: ${({ theme }) => theme.space.xs};
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  padding: 2px ${({ theme }) => theme.space.sm};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.xs};
  cursor: pointer;
`;

export const Missing = styled.p`
  margin: 0;
  padding: ${({ theme }) => theme.space.lg};
  border: 1px dashed ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  text-align: center;
`;
