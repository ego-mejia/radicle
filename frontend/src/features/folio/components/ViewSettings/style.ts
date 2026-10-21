import styled from 'styled-components';

export const Form = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Row = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

export const Section = styled.section`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.sm};

  h3 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.md};
  }

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Line = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;
  width: 100%;

  select,
  input {
    flex: 1 1 120px;
    width: auto;
  }
`;

export const Checks = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => `${theme.space.sm} ${theme.space.lg}`};

  label {
    display: inline-flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.xs};
  }
`;

export const Danger = styled.span`
  margin-right: auto;
`;
