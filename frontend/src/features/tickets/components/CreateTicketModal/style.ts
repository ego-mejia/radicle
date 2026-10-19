import styled from 'styled-components';

export const Form = styled.form`
  display: contents;
`;

export const Types = styled.div`
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface2};
  align-self: flex-start;
`;

export const TypeOption = styled.button<{ $active: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme, $active }) => ($active ? theme.color.surface : 'transparent')};
  box-shadow: ${({ $active }) => ($active ? '0 1px 2px rgba(0,0,0,.08)' : 'none')};
  font: inherit;
  font-weight: 600;
  color: ${({ theme, $active }) => ($active ? theme.color.text : theme.color.textMuted)};
  cursor: pointer;
`;

export const Row = styled.div`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: ${({ theme }) => theme.space.md};

  @media (max-width: 520px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const More = styled.details`
  border-top: 1px solid ${({ theme }) => theme.color.border};
  padding-top: ${({ theme }) => theme.space.md};

  summary {
    cursor: pointer;
    font-weight: 600;
    color: ${({ theme }) => theme.color.textMuted};
    margin-bottom: ${({ theme }) => theme.space.md};
  }

  > div {
    display: flex;
    flex-direction: column;
    gap: ${({ theme }) => theme.space.md};
  }
`;

export const Another = styled.label`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: auto;
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;

  input {
    accent-color: ${({ theme }) => theme.color.accentFill};
  }
`;
