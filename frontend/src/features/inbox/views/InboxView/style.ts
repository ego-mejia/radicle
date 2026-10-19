import styled from 'styled-components';

export const Bar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin-bottom: ${({ theme }) => theme.space.md};

  select {
    width: auto;
  }
`;

export const Tabs = styled.div`
  display: inline-flex;
  gap: 2px;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  button {
    border: 0;
    border-bottom: 2px solid transparent;
    background: none;
    padding: 6px 10px;
    font: inherit;
    color: ${({ theme }) => theme.color.textMuted};
    cursor: pointer;
  }

  button[aria-selected='true'] {
    color: ${({ theme }) => theme.color.text};
    border-bottom-color: ${({ theme }) => theme.color.accent};
    font-weight: 600;
  }

  small {
    margin-left: 4px;
    padding: 0 6px;
    border-radius: ${({ theme }) => theme.radius.full};
    background: ${({ theme }) => theme.color.surface2};
    font-size: ${({ theme }) => theme.fontSize.xs};
  }
`;

export const Spacer = styled.span`
  flex: 1;
`;

export const Toggle = styled.div`
  display: inline-flex;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  overflow: hidden;

  button {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border: 0;
    padding: 6px 10px;
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
    font: inherit;
    font-size: ${({ theme }) => theme.fontSize.md};
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    background: ${({ theme }) => theme.color.accentSoft};
    font-weight: 600;
  }
`;
