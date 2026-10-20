import styled from 'styled-components';

export const Bar = styled.form`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;
  margin-top: ${({ theme }) => theme.space.md};

  > select {
    width: auto;
  }
`;

export const Combo = styled.div`
  position: relative;
  flex: 1 1 260px;
`;

export const Search = styled.input`
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;

  &:focus {
    outline: none;
    border-color: ${({ theme }) => theme.color.accent};
    box-shadow: 0 0 0 3px ${({ theme }) => theme.color.accentSoft};
  }
`;

export const List = styled.div`
  position: absolute;
  z-index: 20;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 280px;
  overflow-y: auto;
  padding: 4px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  box-shadow: 0 12px 28px rgba(17, 24, 39, 0.14);
`;

export const Heading = styled.div`
  padding: 6px 8px 2px;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
`;

export const Option = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: 6px 8px;
  border-radius: ${({ theme }) => theme.radius.sm};
  cursor: pointer;

  &[aria-selected='true'] {
    background: ${({ theme }) => theme.color.accentSoft};
  }

  span {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const GroupIcon = styled.span`
  && {
    flex: none;
    display: inline-grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: ${({ theme }) => theme.color.accentSoft};
    color: ${({ theme }) => theme.color.accent};
  }
`;

export const Tag = styled.span`
  && {
    flex: none;
    padding: 0 8px;
    border-radius: 999px;
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.xs};
  }
`;

export const Empty = styled.p`
  margin: 0;
  padding: 8px;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
