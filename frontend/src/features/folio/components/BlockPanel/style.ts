import styled from 'styled-components';

export const Panel = styled.aside<{ $wide: boolean }>`
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 40;
  display: flex;
  flex-direction: column;
  width: min(${({ $wide }) => ($wide ? '880px' : '420px')}, 100vw);
  border-left: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.surface};
  box-shadow: -8px 0 24px rgb(0 0 0 / 12%);
`;

export const Header = styled.header`
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
  display: grid;
  align-content: start;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.lg};
  overflow-y: auto;
`;
