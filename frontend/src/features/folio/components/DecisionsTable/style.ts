import styled, { css } from 'styled-components';
import type { DecisionStatus } from '../../../../services/api/folioSections';

// Same table frame as Specs, so the sections read as one family.
export { Bar, Box, Empty, More, Muted, Project, Table, Wrap } from '../SpecsTable/style';

export const Number = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
  font-variant-numeric: tabular-nums;
`;

export const Topic = styled.span`
  padding: 2px 8px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  white-space: nowrap;
`;

const tones = {
  accepted: css`
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.accent};
  `,
  proposed: css`
    background: ${({ theme }) => theme.color.accentSoft};
  `,
  replaced: css`
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.textMuted};
  `,
};

export const Status = styled.span<{ $status: DecisionStatus }>`
  padding: 2px 8px;
  border-radius: ${({ theme }) => theme.radius.md};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  white-space: nowrap;
  ${({ $status }) => tones[$status]}
`;

export const Hidden = styled.span`
  margin-left: auto;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
