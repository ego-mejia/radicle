import styled from 'styled-components';

export const Back = styled.a`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  margin-bottom: ${({ theme }) => theme.space.md};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
  text-decoration: none;
`;

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  max-width: 860px;
`;

export const Row = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 120px) minmax(0, 1fr);
  gap: ${({ theme }) => theme.space.lg};

  & + & {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;

export const Body = styled.section`
  padding: ${({ theme }) => theme.space.xl};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
`;

export const Variables = styled.p`
  margin: 0 0 ${({ theme }) => theme.space.lg};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Code = styled.textarea`
  width: 100%;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.md};
  padding: ${({ theme }) => theme.space.md};
  color: ${({ theme }) => theme.color.text};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
`;

export const Actions = styled.div`
  display: flex;
  justify-content: flex-end;
`;
