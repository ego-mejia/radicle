import styled, { css } from 'styled-components';
import type { SpecStatus } from '../../../../services/api/folioSections';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  min-width: 0;
`;

export const Bar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Save = styled.button`
  margin-left: auto;
  padding: 0;
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.accent};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  cursor: pointer;
`;

export const Box = styled.div`
  overflow-x: auto;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 16px;
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;

  th {
    padding: 10px 14px;
    text-align: left;
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-weight: 600;
    color: ${({ theme }) => theme.color.textMuted};
    white-space: nowrap;
  }

  td {
    padding: 12px 14px;
    border-top: 1px solid ${({ theme }) => theme.color.surface2};
    font-size: ${({ theme }) => theme.fontSize.md};
    vertical-align: middle;
  }

  td a {
    color: ${({ theme }) => theme.color.text};
    font-weight: 600;
  }

  tbody tr:hover td {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Project = styled.span`
  padding: 2px 6px;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.accentSoft};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
`;

export const Feature = styled.span`
  display: inline-block;
  margin: 2px 4px 2px 0;
  padding: 2px 8px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  white-space: nowrap;
`;

export const Progress = styled.span`
  display: flex;
  width: 90px;
  height: 6px;
  overflow: hidden;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
`;

export const Done = styled.span<{ $pct: number }>`
  width: ${({ $pct }) => $pct}%;
  background: ${({ theme }) => theme.color.catDone};
`;

export const Live = styled.span<{ $pct: number }>`
  width: ${({ $pct }) => $pct}%;
  background: ${({ theme }) => theme.color.catProgress};
`;

const tones = {
  live: css`
    background: ${({ theme }) => theme.color.accentSoft};
  `,
  done: css`
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.accent};
  `,
  outdated: css`
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.warning};
  `,
  planned: css`
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.textMuted};
  `,
};

export const Status = styled.span<{ $status: SpecStatus }>`
  padding: 2px 8px;
  border-radius: ${({ theme }) => theme.radius.md};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  white-space: nowrap;
  ${({ $status }) => tones[$status]}
`;

export const Muted = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  white-space: nowrap;
`;

export const Empty = styled.p`
  margin: 0;
  padding: 28px;
  text-align: center;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const More = styled.button`
  align-self: center;
  padding: 0;
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.accent};
  font: inherit;
  font-weight: 600;
  cursor: pointer;
`;
