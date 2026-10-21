import styled from 'styled-components';

export const Section = styled.section`
  margin-top: ${({ theme }) => theme.space.xl};
  border-top: 1px solid ${({ theme }) => theme.color.border};
  padding-top: ${({ theme }) => theme.space.md};
`;

export const Toggle = styled.button`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  min-height: 36px;
  border: 0;
  background: transparent;
  color: ${({ theme }) => theme.color.textMuted};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  cursor: pointer;

  svg {
    width: 15px;
    height: 15px;
  }
`;

export const List = styled.ul`
  list-style: none;
  margin: ${({ theme }) => theme.space.sm} 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: ${({ theme }) => theme.space.sm};
  }

  button svg {
    width: 14px;
    height: 14px;
  }
`;

export const Text = styled.span`
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    font-weight: 500;
    font-size: ${({ theme }) => theme.fontSize.md};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    font-size: ${({ theme }) => theme.fontSize.sm};
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
