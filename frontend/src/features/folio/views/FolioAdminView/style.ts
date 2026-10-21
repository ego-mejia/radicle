import styled from 'styled-components';

export const Kind = styled.span`
  display: inline-flex;
  color: ${({ theme }) => theme.color.textMuted};

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Role = styled.div`
  width: 140px;
`;

export const Section = styled.div`
  margin-top: ${({ theme }) => theme.space.lg};
`;
