import styled from 'styled-components';

export const Form = styled.form`
  display: contents;
`;

export const Kinds = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Kind = styled.label<{ $active: boolean }>`
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: ${({ theme }) => theme.space.sm};
  border: 1px solid ${({ theme, $active }) => ($active ? theme.color.accent : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $active }) => ($active ? theme.color.accentSoft : 'transparent')};
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
