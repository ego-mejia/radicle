import styled from 'styled-components';

export const Block = styled.div<{ $selected: boolean }>`
  position: relative;
  border-radius: ${({ theme }) => theme.radius.md};
  outline: 2px solid ${({ theme, $selected }) => ($selected ? theme.color.accent : 'transparent')};
  outline-offset: 2px;
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
