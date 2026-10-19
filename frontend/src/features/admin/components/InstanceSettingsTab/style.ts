import styled from 'styled-components';

export const Check = styled.label`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
`;

export const Note = styled.p<{ $warn: boolean }>`
  margin: 0;
  color: ${({ theme, $warn }) => ($warn ? theme.color.warning : theme.color.textMuted)};
`;
