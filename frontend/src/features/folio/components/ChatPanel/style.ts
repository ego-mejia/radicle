import styled from 'styled-components';

export const Panel = styled.aside`
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  /* Above the Folio bar (30) and the full-screen editor (40). */
  z-index: 45;
  display: flex;
  flex-direction: column;
  width: min(420px, 100vw);
  border-left: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.bg};
  box-shadow: -8px 0 24px rgb(0 0 0 / 12%);

  &[hidden] {
    display: none;
  }
`;

export const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.lg}`};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }
`;

export const Body = styled.div`
  flex: 1;
  min-height: 0;
  padding: ${({ theme }) => theme.space.lg};
`;
