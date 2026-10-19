import styled from 'styled-components';

export const Drop = styled.div<{ $active: boolean }>`
  border-radius: ${({ theme }) => theme.radius.md};
  outline: 2px dashed ${({ theme, $active }) => ($active ? theme.color.accent : 'transparent')};
  outline-offset: 4px;
`;

export const Empty = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

export const Tile = styled.div`
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: 100px auto;
  gap: 4px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 6px;
  background: ${({ theme }) => theme.color.surface};
  min-width: 0;
`;

export const Preview = styled.button`
  grid-column: 1 / -1;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;
  padding: 0;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  svg {
    width: 32px;
    height: 32px;
  }
`;

export const Meta = styled.div`
  display: flex;
  flex-direction: column;
  min-width: 0;
  font-size: ${({ theme }) => theme.fontSize.sm};

  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.xs};
  }
`;
