import styled from 'styled-components';

export const Divider = styled.hr`
  border: 0;
  border-top: 1px solid ${({ theme }) => theme.color.border};
  margin: ${({ theme }) => theme.space.sm} 0;
`;

export const Picker = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
`;

export const Dot = styled.span`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
`;

export const Check = styled.input`
  width: 16px;
  height: 16px;
  accent-color: ${({ theme }) => theme.color.accent};
`;

export const Open = styled.a`
  color: ${({ theme }) => theme.color.accent};
  text-decoration: none;
`;
