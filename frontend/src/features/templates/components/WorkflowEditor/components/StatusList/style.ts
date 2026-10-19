import styled from 'styled-components';

export const List = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  align-items: flex-start;
`;

export const Row = styled.div<{ $dragging: boolean }>`
  display: grid;
  grid-template-columns: 20px minmax(120px, 1fr) 130px auto minmax(60px, 120px) 32px;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;
  width: 100%;
  padding: 4px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $dragging }) => ($dragging ? theme.color.surface2 : 'transparent')};
  position: relative;
  z-index: ${({ $dragging }) => ($dragging ? 2 : 'auto')};

  @media (max-width: 640px) {
    grid-template-columns: 20px 1fr 110px 32px;
  }
`;

export const Handle = styled.button`
  display: grid;
  place-items: center;
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.textMuted};
  cursor: grab;
  padding: 0;

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Initial = styled.label`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: nowrap;

  @media (max-width: 640px) {
    display: none;
  }
`;

export const Ref = styled.code`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-variant-ligatures: none;
  color: ${({ theme }) => theme.color.textMuted};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  @media (max-width: 640px) {
    display: none;
  }
`;
