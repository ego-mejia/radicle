import * as S from './style';

/** The look of a Folio document while it is edited: every block, styled by its data attributes. */
export function EditorProse({ children }: { children: React.ReactNode }) {
  return <S.Prose>{children}</S.Prose>;
}
