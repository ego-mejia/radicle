import * as S from './style';

export { S as SectionParts };

type Props = { title: string; action?: React.ReactNode; children: React.ReactNode };

export function Section({ title, action, children }: Props) {
  return (
    <S.Wrap>
      <S.Head>
        <h2>{title}</h2>
        {action}
      </S.Head>
      {children}
    </S.Wrap>
  );
}
