import styled from 'styled-components';

export const Panel = styled.aside`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  min-width: 0;

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 400;
  }
`;

export const Help = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: calc(100vh - 300px);
  overflow: auto;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};

  li {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px ${({ theme }) => theme.space.sm};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    cursor: grab;
    font-size: ${({ theme }) => theme.fontSize.md};
  }

  li:last-child {
    border-bottom: 0;
  }

  button {
    border: 0;
    background: none;
    padding: 0;
    font: inherit;
    color: ${({ theme }) => theme.color.text};
    text-align: left;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;
