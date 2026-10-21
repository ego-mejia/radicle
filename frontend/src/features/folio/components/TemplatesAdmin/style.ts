import styled from 'styled-components';

export const Icon = styled.span`
  width: 28px;
  font-size: ${({ theme }) => theme.fontSize.xl};
  text-align: center;
`;

export const Name = styled.span`
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;

  a {
    font-weight: 600;
    color: ${({ theme }) => theme.color.text};
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
