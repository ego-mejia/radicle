import styled from 'styled-components';

export const Panel = styled.aside`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.md};
  border-right: 1px solid ${({ theme }) => theme.color.border};
  min-width: 0;

  @media (max-width: 900px) {
    border-right: 0;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
  }
`;

export const Head = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.md};
  }
`;

export const Group = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;

  h3 {
    margin: 0 0 4px;
    font-size: ${({ theme }) => theme.fontSize.xs};
    color: ${({ theme }) => theme.color.textMuted};
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
`;

export const Item = styled.div<{ $active: boolean }>`
  display: flex;
  align-items: center;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme, $active }) => ($active ? theme.color.accentSoft : 'transparent')};

  > button:first-child {
    flex: 1;
    min-width: 0;
    padding: 5px 8px;
    border: 0;
    background: none;
    color: ${({ theme }) => theme.color.text};
    font: inherit;
    font-size: ${({ theme }) => theme.fontSize.md};
    text-align: left;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Remove = styled.button`
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Empty = styled.span`
  padding: 0 8px;
  color: ${({ theme }) => theme.color.textMuted};
`;
