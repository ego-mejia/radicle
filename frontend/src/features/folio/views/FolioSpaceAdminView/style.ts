import { Link } from '@tanstack/react-router';
import styled from 'styled-components';

const gutter = `
  padding-left: max(24px, env(safe-area-inset-left, 0px));
  padding-right: max(24px, env(safe-area-inset-right, 0px));
`;

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
`;

export const Head = styled.header`
  ${gutter};
  padding-top: ${({ theme }) => theme.space.lg};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.surface};

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xxl};
  }
`;

export const Back = styled(Link)`
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
  text-decoration: none;

  svg {
    width: 15px;
    height: 15px;
  }
  &:hover {
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Body = styled.div`
  ${gutter};
  padding-top: ${({ theme }) => theme.space.xl};
  padding-bottom: 64px;
`;

export const Settings = styled.section`
  max-width: 640px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};

  p {
    margin: 0;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Row = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
`;
