import styled from 'styled-components';

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Heading = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }

  p {
    margin: 0;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Sso = styled.a`
  display: flex;
  justify-content: center;
  align-items: center;
  height: 40px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font-weight: 600;
  text-decoration: none;

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Or = styled.p`
  margin: 0;
  text-align: center;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Emergency = styled.button`
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.textMuted};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  text-decoration: underline;
  cursor: pointer;
`;
