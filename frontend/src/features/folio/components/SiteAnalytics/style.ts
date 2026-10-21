import styled from 'styled-components';

export const Wrap = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Columns = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: ${({ theme }) => theme.space.lg};
  align-items: start;
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Ranked = styled.ol`
  margin: 0;
  padding-left: ${({ theme }) => theme.space.xl};
  display: grid;
  gap: ${({ theme }) => theme.space.sm};

  li {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  a {
    color: ${({ theme }) => theme.color.text};
    font-weight: 500;
    overflow-wrap: anywhere;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Query = styled.span`
  color: ${({ theme }) => theme.color.text};
  font-weight: 500;
  overflow-wrap: anywhere;
`;
