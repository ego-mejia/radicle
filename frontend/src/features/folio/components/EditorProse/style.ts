import styled, { css } from 'styled-components';
import type { Theme } from '../../../../styles/theme';

const block = (theme: Theme) => css`
  border-radius: ${theme.radius.lg};
  padding: ${theme.space.md} ${theme.space.lg};
  margin: ${theme.space.md} 0;
`;

const panelColor = (theme: Theme, kind: string) =>
  ({
    warning: theme.color.warning,
    error: theme.color.danger,
    note: theme.color.textMuted,
  })[kind] ?? theme.color.accent;

const statusColor = (theme: Theme, color: string) =>
  ({
    green: theme.color.accent,
    yellow: theme.color.warning,
    red: theme.color.danger,
    blue: theme.color.info,
    purple: theme.color.violet,
  })[color] ?? theme.color.textMuted;

/** The document's look while editing; the reading view has its own. */
export const Prose = styled.div`
  .ProseMirror {
    outline: none;
    font-size: 17px;
    line-height: 1.75;
    min-height: 40vh;
  }
  .ProseMirror > * + * {
    margin-top: ${({ theme }) => theme.space.md};
  }
  h1,
  h2,
  h3,
  h4 {
    line-height: 1.25;
    letter-spacing: -0.015em;
    margin: ${({ theme }) => theme.space.xl} 0 0;
  }
  h1 {
    font-size: 30px;
  }
  h2 {
    font-size: 24px;
  }
  h3 {
    font-size: 20px;
  }
  h4 {
    font-size: 17px;
  }
  a {
    color: ${({ theme }) => theme.color.accent};
  }
  code {
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: 0.88em;
    background: ${({ theme }) => theme.color.surface2};
    border-radius: ${({ theme }) => theme.radius.sm};
    padding: 1px 5px;
  }
  pre {
    ${({ theme }) => block(theme)};
    background: ${({ theme }) => theme.color.surface2};
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.md};
    overflow-x: auto;
  }
  pre code {
    background: none;
    padding: 0;
  }
  blockquote {
    border-left: 3px solid ${({ theme }) => theme.color.border};
    margin-left: 0;
    padding-left: ${({ theme }) => theme.space.lg};
    color: ${({ theme }) => theme.color.textMuted};
  }
  ul[data-type='taskList'] {
    list-style: none;
    padding-left: ${({ theme }) => theme.space.xs};
  }
  ul[data-type='taskList'] li {
    display: flex;
    gap: ${({ theme }) => theme.space.sm};
  }
  div[data-folio='actionItem'] {
    display: flex;
    align-items: flex-start;
    gap: ${({ theme }) => theme.space.sm};
    padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.md};
    background: ${({ theme }) => theme.color.surface2};

    > input[type='checkbox'] {
      margin-top: 5px;
      accent-color: ${({ theme }) => theme.color.accent};
    }
    .action-text {
      flex: 1;
      min-width: 0;
    }
    .action-meta {
      display: flex;
      gap: ${({ theme }) => theme.space.xs};
    }
    .action-meta input {
      width: 120px;
      padding: 2px ${({ theme }) => theme.space.xs};
      border: 1px solid ${({ theme }) => theme.color.border};
      border-radius: ${({ theme }) => theme.radius.sm};
      background: ${({ theme }) => theme.color.surface};
      color: ${({ theme }) => theme.color.text};
      font: inherit;
      font-size: ${({ theme }) => theme.fontSize.sm};
    }
    &[data-done='true'] .action-text {
      color: ${({ theme }) => theme.color.textMuted};
      text-decoration: line-through;
    }
  }
  table {
    border-collapse: collapse;
    width: 100%;
  }
  td,
  th {
    border: 1px solid ${({ theme }) => theme.color.border};
    padding: ${({ theme }) => theme.space.sm};
    vertical-align: top;
  }
  th {
    background: ${({ theme }) => theme.color.surface2};
    text-align: left;
  }
  hr {
    border: 0;
    border-top: 1px solid ${({ theme }) => theme.color.border};
  }
  [data-folio='panel'] {
    ${({ theme }) => block(theme)};
    background: ${({ theme }) => theme.color.accentSoft};
  }
  ${({ theme }) =>
    ['info', 'tip', 'warning', 'error', 'note'].map(
      (kind) => css`
        [data-folio='panel'][data-kind='${kind}'] {
          border-left: 4px solid ${panelColor(theme, kind)};
        }
      `,
    )}
  [data-folio='expand'] {
    ${({ theme }) => block(theme)};
    border: 1px solid ${({ theme }) => theme.color.border};
  }
  [data-folio='expand']::before {
    content: '▸ ' attr(data-title);
    display: block;
    font-weight: 600;
    margin-bottom: ${({ theme }) => theme.space.sm};
  }
  [data-folio='columns'] {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: ${({ theme }) => theme.space.lg};
  }
  [data-folio='columns'][data-layout='sidebar_left'] {
    grid-template-columns: 1fr 2fr;
  }
  [data-folio='columns'][data-layout='sidebar_right'] {
    grid-template-columns: 2fr 1fr;
  }
  [data-folio='column'] {
    border: 1px dashed ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.md};
    padding: ${({ theme }) => theme.space.sm};
  }
  [data-folio='tableOfContents'],
  [data-folio='childPages'],
  [data-folio='file'],
  [data-folio='video'],
  [data-folio='image'] {
    ${({ theme }) => block(theme)};
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.md};
  }
  [data-folio='image'],
  [data-folio='video'] {
    background: none;
    padding: 0;
    text-align: center;
  }
  [data-folio='image'] img,
  [data-folio='video'] video {
    max-width: 100%;
    border-radius: ${({ theme }) => theme.radius.lg};
  }
  [data-folio='image'][data-size='small'] img {
    max-width: 40%;
  }
  [data-folio='image'][data-size='medium'] img {
    max-width: 65%;
  }
  [data-folio='image'][data-align='left'] {
    text-align: left;
  }
  [data-folio='image'][data-align='right'] {
    text-align: right;
  }
  .caption {
    display: block;
    margin-top: ${({ theme }) => theme.space.xs};
    font-size: ${({ theme }) => theme.fontSize.md};
    color: ${({ theme }) => theme.color.textMuted};
  }
  [data-folio='file'] a {
    color: ${({ theme }) => theme.color.accent};
    font-weight: 500;
  }
  [data-folio='mention'] {
    color: ${({ theme }) => theme.color.accent};
    font-weight: 500;
  }
  [data-folio='status'] {
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.xs};
    font-weight: 600;
    text-transform: uppercase;
    border: 1px solid currentColor;
    border-radius: ${({ theme }) => theme.radius.sm};
    padding: 1px 6px;
  }
  ${({ theme }) =>
    ['grey', 'green', 'yellow', 'red', 'blue', 'purple'].map(
      (color) => css`
        [data-folio='status'][data-color='${color}'] {
          color: ${statusColor(theme, color)};
        }
      `,
    )}
  .ProseMirror-selectednode {
    outline: 2px solid ${({ theme }) => theme.color.accent};
  }
  p.is-editor-empty:first-child::before {
    content: attr(data-placeholder);
    float: left;
    height: 0;
    pointer-events: none;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
