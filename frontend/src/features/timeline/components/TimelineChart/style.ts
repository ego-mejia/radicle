import styled from 'styled-components';

export const Wrapper = styled.div`
  display: grid;
  grid-template-columns: 260px 1fr;
  height: calc(100vh - 230px);
  min-height: 360px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  overflow: hidden;

  @media (max-width: 640px) {
    grid-template-columns: 140px 1fr;
  }
`;

export const Labels = styled.div`
  overflow: hidden;
  border-right: 1px solid ${({ theme }) => theme.color.border};
`;

export const LabelsHead = styled.div`
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  padding: 0 ${({ theme }) => theme.space.md};
  background: ${({ theme }) => theme.color.surface};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

const row = `
  position: absolute;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 0;
  font: inherit;
  text-align: left;
  cursor: pointer;
  overflow: hidden;
  white-space: nowrap;
`;

export const GroupLabel = styled.button`
  ${row}
  padding: 0 ${({ theme }) => theme.space.sm};
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  font-weight: 700;

  svg {
    width: 14px;
    height: 14px;
    flex: none;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 400;
  }
`;

export const TicketLabel = styled.button`
  ${row}
  padding: 0 ${({ theme }) => theme.space.md};
  background: none;
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.md};

  b {
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-weight: 500;
    color: ${({ theme }) => theme.color.textMuted};
  }

  span {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &:hover span {
    text-decoration: underline;
  }
`;

export const Chart = styled.div`
  overflow: auto;
  position: relative;

  svg {
    display: block;
  }
`;

export const Sticky = styled.div`
  position: sticky;
  top: 0;
  z-index: 1;
`;
