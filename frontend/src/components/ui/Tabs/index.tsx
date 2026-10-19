import * as S from './style';

type Tab<T extends string> = { id: T; label: string; count?: number };

type Props<T extends string> = {
  tabs: Tab<T>[];
  value: T;
  onChange: (id: T) => void;
  label: string;
};

export function Tabs<T extends string>({ tabs, value, onChange, label }: Props<T>) {
  return (
    <S.List role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <S.Tab
          key={tab.id}
          role="tab"
          aria-selected={tab.id === value}
          $active={tab.id === value}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          {tab.count !== undefined && <S.Count>{tab.count}</S.Count>}
        </S.Tab>
      ))}
    </S.List>
  );
}
