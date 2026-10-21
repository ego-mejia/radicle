import styled from 'styled-components';

export const List = styled.ul`
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
`;

export const Item = styled.li`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => `${theme.space.md} 0`};
  border-top: 1px solid ${({ theme }) => theme.color.border};

  &:first-child {
    border-top: 0;
  }
`;

export const Question = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.text};
  font-weight: 500;
  overflow-wrap: anywhere;
`;

export const Meta = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Down = styled.span`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  color: ${({ theme }) => theme.color.danger};

  svg {
    width: 12px;
    height: 12px;
  }
`;

export const Note = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-style: italic;
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
