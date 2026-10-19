import styled from 'styled-components';

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: ${({ theme }) => theme.space.lg};

  h3 {
    margin: 0 0 ${({ theme }) => theme.space.sm};
    font-size: ${({ theme }) => theme.fontSize.sm};
    color: ${({ theme }) => theme.color.textMuted};
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  dl {
    margin: 0;
  }
`;

export const Row = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};
  padding: 4px 0;

  dt {
    display: flex;
    gap: 3px;
  }

  dd {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.sm};
  }

  kbd {
    min-width: 20px;
    padding: 1px 6px;
    border: 1px solid ${({ theme }) => theme.color.border};
    border-bottom-width: 2px;
    border-radius: ${({ theme }) => theme.radius.sm};
    background: ${({ theme }) => theme.color.surface2};
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.xs};
    text-align: center;
  }
`;

export const Note = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
