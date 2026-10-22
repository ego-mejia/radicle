import styled, { type DefaultTheme } from 'styled-components';

// Dark in both themes: ink on the light theme, the raised surface on the dark one.
const ink = (theme: DefaultTheme) =>
  theme.mode === 'dark' ? theme.color.surface2 : theme.color.text;
const onInk = (theme: DefaultTheme) => (theme.mode === 'dark' ? theme.color.text : theme.color.bg);

export const Card = styled.aside`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.lg} ${theme.space.xl}`};
  border-radius: 16px;
  background: ${({ theme }) => ink(theme)};
  color: ${({ theme }) => onInk(theme)};
  box-shadow: 0 10px 28px rgb(17 24 39 / 18%);
`;

export const Face = styled.span`
  display: grid;
  place-items: center;
  flex: none;
  width: 40px;
  height: 40px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.radi};

  ellipse {
    fill: ${({ theme }) => theme.color.radiEye};
  }
`;

export const Say = styled.span`
  display: flex;
  flex: 1 1 280px;
  flex-direction: column;
  gap: 4px;
  font-size: ${({ theme }) => theme.fontSize.md};
  line-height: 1.55;
`;

export const Kicker = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.accentFill};
`;

export const Actions = styled.span`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  a {
    display: inline-flex;
    align-items: center;
    min-height: 36px;
    padding: 0 ${({ theme }) => theme.space.md};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.lg};
    color: inherit;
    font-weight: 600;
    text-decoration: none;
  }

  a:first-child {
    border-color: ${({ theme }) => theme.color.accentFill};
    background: ${({ theme }) => theme.color.accentFill};
    color: ${({ theme }) => theme.color.onAccent};
  }
`;

export const Dismiss = styled.button`
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.border};
  color: inherit;
  cursor: pointer;

  svg {
    width: 14px;
    height: 14px;
  }
`;
