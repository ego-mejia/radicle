import styled from 'styled-components';

export const Card = styled.section`
  max-width: 900px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: 20px 22px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 16px;
  background: ${({ theme }) => theme.color.surface};
`;

export const Intro = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;

  span {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Scroll = styled.div`
  overflow-x: auto;

  table {
    border-collapse: collapse;
    width: 100%;
  }
  th {
    padding: 8px 10px;
    text-align: center;
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-weight: 600;
    color: ${({ theme }) => theme.color.textMuted};
    white-space: nowrap;
  }
  th:first-child,
  td:first-child {
    text-align: left;
  }
  td {
    padding: 8px 10px;
    text-align: center;
    border-top: 1px solid ${({ theme }) => theme.color.surface2};
    white-space: nowrap;
  }
  input {
    width: 16px;
    height: 16px;
    accent-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Remove = styled.button`
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.md};
  background: none;
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;

  svg {
    width: 15px;
    height: 15px;
  }
  &:hover {
    color: ${({ theme }) => theme.color.danger};
  }
`;

export const Add = styled.form`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;

  select {
    min-height: 40px;
    padding: 0 10px;
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.lg};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
    font: inherit;
  }
  > input,
  > div {
    flex: 1 1 200px;
  }
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;
