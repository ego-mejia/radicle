import * as S from './style';

export { S as SettingsParts };

type Props = { title: string; help?: string; children: React.ReactNode };

export function SettingsCard({ title, help, children }: Props) {
  return (
    <S.Card>
      <h2>{title}</h2>
      {help && <p className="help">{help}</p>}
      {children}
    </S.Card>
  );
}
