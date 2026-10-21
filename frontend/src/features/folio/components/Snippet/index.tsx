import * as S from './style';

/** A search snippet: the words between ** are the ones that matched, shown highlighted. */
export function Snippet({ text }: { text: string }) {
  const parts = text.split('**');
  return (
    <S.Text>{parts.map((part, i) => (i % 2 === 1 ? <mark key={i}>{part}</mark> : part))}</S.Text>
  );
}
