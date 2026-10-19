import styled from 'styled-components';

export const List = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 220px;
`;

export const Option = styled.button<{ $selected: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 9px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme, $selected }) => ($selected ? theme.color.surface2 : 'transparent')};
  font: inherit;
  color: ${({ theme }) => theme.color.text};
  text-align: left;
  cursor: pointer;

  &:hover:not(:disabled),
  &:focus-visible {
    background: ${({ theme }) => theme.color.surface2};
  }

  &:disabled {
    cursor: not-allowed;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Label = styled.span`
  display: flex;
  flex-direction: column;
`;

export const Reason = styled.small`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.xs};
`;

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 9px 4px;
  border-top: 1px solid ${({ theme }) => theme.color.border};
  margin-top: 4px;
  max-width: 300px;

  strong {
    font-size: ${({ theme }) => theme.fontSize.sm};
  }

  button[type='submit'] {
    align-self: flex-end;
  }
`;

export const Via = styled.span`
  margin-left: auto;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Resolutions = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 9px 4px;
  border-top: 1px solid ${({ theme }) => theme.color.border};
  margin-top: 4px;

  strong {
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;

export const Chips = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
`;

export const Empty = styled.div`
  padding: 8px;
  color: ${({ theme }) => theme.color.textMuted};
`;
