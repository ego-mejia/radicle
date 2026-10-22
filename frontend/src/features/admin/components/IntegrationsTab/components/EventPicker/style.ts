import styled from 'styled-components';

export const Box = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: ${({ theme }) => theme.space.xs} ${({ theme }) => theme.space.md};

  label {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;

export const Hint = styled.small`
  grid-column: 1 / -1;
  color: ${({ theme }) => theme.color.textMuted};
`;
