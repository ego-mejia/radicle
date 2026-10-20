import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Presets = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  > label {
    flex: 1;
    min-width: 220px;
  }
`;

export const Check = styled.label`
  display: flex;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;

  span {
    display: flex;
    flex-direction: column;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }

  input {
    margin-top: 3px;
    accent-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Count = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Groups = styled.div<{ $disabled: boolean }>`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: ${({ theme }) => theme.space.md};
  max-height: 420px;
  overflow-y: auto;
  padding: ${({ theme }) => theme.space.sm};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  opacity: ${({ $disabled }) => ($disabled ? 0.55 : 1)};
`;

export const Group = styled.fieldset`
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: 0;
  border: 0;
`;

export const Tool = styled.label`
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  column-gap: 6px;
  padding-left: 20px;
  cursor: pointer;
  font-size: ${({ theme }) => theme.fontSize.sm};

  input {
    accent-color: ${({ theme }) => theme.color.accent};
  }

  code {
    font-family: ${({ theme }) => theme.fonts.mono};
  }

  small {
    grid-column: 2 / -1;
    overflow: hidden;
    color: ${({ theme }) => theme.color.textMuted};
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

export const Read = styled.span`
  justify-self: start;
  padding: 0 6px;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.accent};
  font-size: ${({ theme }) => theme.fontSize.xs};
`;
