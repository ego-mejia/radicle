import styled from 'styled-components';

export const Head = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
  flex-wrap: wrap;
  margin-bottom: ${({ theme }) => theme.space.xl};

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
    letter-spacing: -0.01em;
  }

  p {
    margin: 4px 0 0;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
