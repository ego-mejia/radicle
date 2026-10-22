import styled from 'styled-components';

/** The suite's left sidebar (Docket and Folio): same width, padding and switch position. */
export const SIDEBAR_WIDTH = '232px';

/** The page grid: the sidebar column, then the content. Drawer under 860px. */
export const AppShell = styled.div`
  display: grid;
  grid-template-columns: ${SIDEBAR_WIDTH} minmax(0, 1fr);
  min-height: 100%;

  @media (max-width: 860px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const Aside = styled.aside<{ $open: boolean }>`
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => `${theme.space.lg} ${theme.space.md}`};
  background: ${({ theme }) => theme.color.surface};
  border-right: 1px solid ${({ theme }) => theme.color.border};
  overflow-y: auto;

  @media (max-width: 860px) {
    position: fixed;
    inset: 0 auto 0 0;
    width: 260px;
    z-index: 45;
    transform: translateX(${({ $open }) => ($open ? '0' : '-100%')});
    transition: transform 0.18s ease-out;
    box-shadow: ${({ $open }) => ($open ? '12px 0 40px rgba(0,0,0,.2)' : 'none')};
  }
`;

export const Scrim = styled.div<{ $open: boolean }>`
  display: none;

  @media (max-width: 860px) {
    display: ${({ $open }) => ($open ? 'block' : 'none')};
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.35);
    z-index: 44;
  }
`;

/** The suite switch fills the column, so it is the same size in every app. */
export const Brand = styled.div`
  display: flex;

  > * {
    flex: 1;
    min-width: 0;
  }
`;

export const Section = styled.nav`
  display: flex;
  flex-direction: column;
  gap: 1px;
`;

export const SectionTitle = styled.div`
  padding: 4px 8px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const NavLink = styled.a`
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 6px 8px;
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }

  &[data-status='active'] {
    background: ${({ theme }) => theme.color.accentSoft};
    color: ${({ theme }) => (theme.mode === 'dark' ? theme.color.accent : theme.color.onAccent)};
    font-weight: 600;
  }

  svg {
    width: 16px;
    height: 16px;
    flex: none;
    color: ${({ theme }) => theme.color.textMuted};
  }

  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

export const ProjectKey = styled.code`
  flex: none;
  min-width: 34px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.accent};
`;

export const Spacer = styled.div`
  flex: 1;
`;

export const Profile = styled.button`
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: none;
  font: inherit;
  color: ${({ theme }) => theme.color.text};
  text-align: left;
  cursor: pointer;

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }

  small {
    display: block;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.xs};
  }
`;
