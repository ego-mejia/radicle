import styled from 'styled-components';

export const Wrap = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Head = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Row = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 6px 8px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};

  a {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    flex: 1;
    color: ${({ theme }) => theme.color.text};
    text-decoration: none;
  }

  a:hover span.title {
    text-decoration: underline;
  }

  span.title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Group = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

export const GroupLabel = styled.div`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Form = styled.form`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  flex-wrap: wrap;

  select {
    width: auto;
  }

  input {
    flex: 1;
    min-width: 120px;
  }
`;

export const Restricted = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: ${({ theme }) => theme.color.textMuted};
  font-style: italic;
`;
