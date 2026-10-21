import styled from 'styled-components';

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Providers = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: ${({ theme }) => theme.space.sm};
`;

export const Provider = styled.label<{ $active: boolean }>`
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

export const Result = styled.p<{ $ok: boolean }>`
  margin: 0;
  color: ${({ theme, $ok }) => ($ok ? theme.color.accent : theme.color.danger)};
  font-weight: 600;
`;

export const Actions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
`;
