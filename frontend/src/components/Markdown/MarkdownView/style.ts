import styled from 'styled-components';

export const Prose = styled.div`
  img {
    max-width: 100%;
    max-height: 480px;
    border-radius: ${({ theme }) => theme.radius.md};
    border: 1px solid ${({ theme }) => theme.color.border};
  }

  line-height: 1.6;
  overflow-wrap: anywhere;

  > :first-child {
    margin-top: 0;
  }

  > :last-child {
    margin-bottom: 0;
  }

  p,
  ul,
  ol,
  pre,
  blockquote,
  table {
    margin: 0 0 10px;
  }

  h1,
  h2,
  h3,
  h4 {
    margin: 16px 0 8px;
    line-height: 1.3;
  }

  h1 {
    font-size: 18px;
  }

  h2 {
    font-size: 16px;
  }

  h3,
  h4 {
    font-size: 14px;
  }

  ul,
  ol {
    padding-left: 22px;
  }

  code {
    padding: 1px 5px;
    border-radius: ${({ theme }) => theme.radius.sm};
    background: ${({ theme }) => theme.color.surface2};
    font-size: 0.92em;
  }

  pre {
    padding: 10px 12px;
    border-radius: ${({ theme }) => theme.radius.md};
    background: ${({ theme }) => theme.color.surface2};
    overflow-x: auto;

    code {
      padding: 0;
      background: none;
    }
  }

  blockquote {
    padding-left: 12px;
    border-left: 3px solid ${({ theme }) => theme.color.border};
    color: ${({ theme }) => theme.color.textMuted};
  }

  table {
    border-collapse: collapse;
  }

  th,
  td {
    padding: 4px 8px;
    border: 1px solid ${({ theme }) => theme.color.border};
  }

  .mention {
    color: ${({ theme }) => theme.color.accent};
    font-weight: 600;
  }

  li.task-list-item {
    list-style: none;
    margin-left: -22px;
  }
`;

export const TaskItem = styled.li`
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 2px 0;

  input {
    margin-top: 4px;
    accent-color: ${({ theme }) => theme.color.accentFill};
    width: 15px;
    height: 15px;
    cursor: pointer;
  }

  input:disabled {
    cursor: default;
  }
`;

export const TaskText = styled.span<{ $checked: boolean }>`
  flex: 1;
  color: ${({ theme, $checked }) => ($checked ? theme.color.textMuted : theme.color.text)};
  text-decoration: ${({ $checked }) => ($checked ? 'line-through' : 'none')};
`;

export const Unknown = styled.span`
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.warning};
`;
