import styled from 'styled-components';

export const List = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  align-items: flex-start;
`;

export const Column = styled.section`
  width: 100%;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: ${({ theme }) => theme.space.md};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Head = styled.div`
  display: grid;
  grid-template-columns: 1fr 110px auto auto auto;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;
`;

export const Options = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px ${({ theme }) => theme.space.md};
  font-size: ${({ theme }) => theme.fontSize.md};

  label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Warning = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.warning};
`;
