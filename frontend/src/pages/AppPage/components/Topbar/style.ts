import styled from 'styled-components';

export const Bar = styled.header`
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  height: 52px;
  padding: 0 ${({ theme }) => theme.space.xl};
  background: ${({ theme }) => theme.color.bg};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  @media (max-width: 600px) {
    padding: 0 ${({ theme }) => theme.space.md};
  }
`;

export const MenuButton = styled.div`
  display: none;

  @media (max-width: 860px) {
    display: block;
  }
`;

export const Crumbs = styled.nav`
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
  white-space: nowrap;

  a {
    color: inherit;
    text-decoration: none;
  }

  a:hover {
    color: ${({ theme }) => theme.color.text};
  }

  strong {
    color: ${({ theme }) => theme.color.text};
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  @media (max-width: 600px) {
    display: none;
  }
`;

export const Search = styled.form`
  flex: 1;
  display: flex;
  justify-content: flex-end;
  min-width: 0;

  input {
    max-width: 380px;
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-variant-ligatures: none;
  }
`;

export const Actions = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  @media (max-width: 600px) {
    .label {
      display: none;
    }
  }
`;
