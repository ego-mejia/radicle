import styled from 'styled-components';

export const Section = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Label = styled.h2`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const View = styled.div<{ $editable: boolean }>`
  padding: 8px 10px;
  margin: 0 -10px;
  border-radius: ${({ theme }) => theme.radius.md};
  cursor: ${({ $editable }) => ($editable ? 'text' : 'default')};

  &:hover {
    background: ${({ theme, $editable }) => ($editable ? theme.color.surface2 : 'transparent')};
  }
`;

export const Placeholder = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Actions = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Progress = styled.span`
  margin-left: 8px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
