import styled from 'styled-components';

/** Fixed under the term, in viewport coordinates. */
export const Tip = styled.div`
  position: fixed;
  z-index: 60;
  display: grid;
  gap: ${({ theme }) => theme.space.xs};
  width: min(320px, calc(100vw - 32px));
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
`;

export const Term = styled.strong`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  font-size: ${({ theme }) => theme.fontSize.md};

  svg {
    width: 14px;
    height: 14px;
    color: ${({ theme }) => theme.color.accent};
  }
`;

export const Definition = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
  line-height: 1.5;
`;

export const Source = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.sm};

  a {
    color: ${({ theme }) => theme.color.accent};
  }
`;
