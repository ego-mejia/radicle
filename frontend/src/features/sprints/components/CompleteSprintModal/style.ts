import styled from 'styled-components';

export const Summary = styled.dl`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: ${({ theme }) => theme.space.sm};
  margin: 0 0 ${({ theme }) => theme.space.lg};

  div {
    padding: ${({ theme }) => theme.space.sm};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.md};
  }

  dt {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }

  dd {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
    font-weight: 700;
    display: flex;
    flex-direction: column;
  }

  small {
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-weight: 400;
    color: ${({ theme }) => theme.color.textMuted};
  }

  @media (max-width: 520px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

export const Options = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
`;
