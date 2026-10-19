import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../../../components/ui/Avatar';
import type { UserRef } from '../../../../../../services/api/types';
import { InlineSelect } from '../FieldRow';
import * as S from './style';

export type Person = { handle: string; display_name: string; kind: 'human' | 'agent' };

export function PersonChip({ person, onRemove }: { person: UserRef; onRemove?: () => void }) {
  const { t } = useTranslation();
  return (
    <S.Person>
      <Avatar handle={person.handle} name={person.display_name} kind={person.kind} size={20} />
      {person.display_name}
      {onRemove && (
        <button
          type="button"
          aria-label={`${t('common.remove')} @${person.handle}`}
          onClick={onRemove}
        >
          <X />
        </button>
      )}
    </S.Person>
  );
}

type Props = {
  label: string;
  people: Person[];
  value: string;
  onChange: (handle: string) => void;
  disabled?: boolean;
  emptyLabel: string;
};

/** Picks one assignable member; shows their avatar next to the select. */
export function PersonSelect({ label, people, value, onChange, disabled, emptyLabel }: Props) {
  const current = people.find((p) => p.handle === value);
  return (
    <S.Picker>
      {current && (
        <Avatar handle={current.handle} name={current.display_name} kind={current.kind} size={20} />
      )}
      <InlineSelect
        label={label}
        value={value}
        disabled={disabled}
        onChange={onChange}
        options={[
          { value: '', label: emptyLabel },
          ...people.map((p) => ({
            value: p.handle,
            label: `${p.display_name} (@${p.handle})${p.kind === 'agent' ? ' 🤖' : ''}`,
          })),
        ]}
      />
    </S.Picker>
  );
}
