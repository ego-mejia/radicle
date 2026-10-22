import styled from 'styled-components';

export const Main = styled.div`
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100vh;
`;

/** The slim bar over the content: same height and ground as Docket's top bar. */
export const Bar = styled.header`
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  min-height: 52px;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.xl}`};
  background: ${({ theme }) => theme.color.bg};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  }
`;

export const MenuButton = styled.div`
  display: none;

  @media (max-width: 860px) {
    display: block;
  }
`;

export const Search = styled.div`
  flex: 1 1 280px;
  max-width: 560px;
  min-width: 0;
`;

export const Actions = styled.div`
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Ask = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  cursor: pointer;

  &:hover,
  &[aria-expanded='true'] {
    background: ${({ theme }) => theme.color.surface2};
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: 2px;
  }

  svg {
    width: 16px;
    height: 16px;
  }

  @media (max-width: 600px) {
    font-size: 0;
    gap: 0;
  }
`;

export const Content = styled.main`
  flex: 1;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  box-sizing: border-box;
  padding: ${({ theme }) => `${theme.space.xl} ${theme.space.xxl}`};

  &:focus {
    outline: none;
  }

  @media (max-width: 600px) {
    padding: ${({ theme }) => theme.space.lg};
  }
`;

export const SkipLink = styled.a`
  position: absolute;
  left: -999px;
  top: 8px;
  z-index: 70;
  padding: 6px 10px;
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
  border-radius: ${({ theme }) => theme.radius.md};

  &:focus {
    left: 8px;
  }
`;
