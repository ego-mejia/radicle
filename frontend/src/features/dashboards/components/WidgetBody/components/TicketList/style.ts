import styled from 'styled-components';

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  overflow: auto;
  height: 100%;

  li {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 0;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    font-size: ${({ theme }) => theme.fontSize.md};
  }

  a {
    display: flex;
    gap: 6px;
    min-width: 0;
    flex: 1;
    color: ${({ theme }) => theme.color.text};
    text-decoration: none;
  }

  a span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  a:hover span {
    text-decoration: underline;
  }
`;

export const Status = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: nowrap;
`;

export const Blockers = styled.span`
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: nowrap;
`;

export const More = styled.li`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  border-bottom: 0 !important;
`;

export const Empty = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
