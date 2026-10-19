import styled from 'styled-components';
import { classificationToken } from '../../../../lib/inbox';
import type { Classification } from '../../../../services/api/types';

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  font-size: ${({ theme }) => theme.fontSize.md};

  th,
  td {
    padding: 6px ${({ theme }) => theme.space.sm};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    text-align: left;
    white-space: nowrap;
  }

  th {
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 600;
    font-size: ${({ theme }) => theme.fontSize.sm};
  }

  td:nth-child(2) {
    white-space: normal;
    width: 40%;
  }

  select {
    font: inherit;
    padding: 2px 4px;
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.sm};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Title = styled.button`
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  color: ${({ theme }) => theme.color.text};
  text-align: left;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
`;

export const Class = styled.span<{ $kind: Classification }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: ${({ theme }) => theme.fontSize.sm};

  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${({ theme, $kind }) => theme.color[classificationToken($kind)]};
  }
`;
