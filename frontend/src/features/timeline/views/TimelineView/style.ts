import styled from 'styled-components';

export const Toolbar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: 0 0 ${({ theme }) => theme.space.md};

  select {
    width: auto;
  }
`;

export const Zoom = styled.div`
  display: inline-flex;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  overflow: hidden;

  button {
    border: 0;
    padding: 6px 12px;
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

export const Warning = styled.span`
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Body = styled.div`
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: ${({ theme }) => theme.space.lg};
  padding: 0 0 ${({ theme }) => theme.space.xl};

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
`;
