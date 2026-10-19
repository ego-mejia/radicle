import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import * as S from './style';

type Props = { tags: string[]; onChange: (tags: string[]) => void; disabled?: boolean };

export function TagsField({ tags, onChange, disabled }: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState('');
  const add = () => {
    const tag = draft.trim().replace(/^#/, '').toLowerCase();
    setDraft('');
    if (tag && !tags.includes(tag)) onChange([...tags, tag]);
  };
  return (
    <>
      {tags.map((tag) => (
        <S.Tag key={tag}>
          #{tag}
          {!disabled && (
            <button
              type="button"
              aria-label={`${t('common.remove')} #${tag}`}
              onClick={() => onChange(tags.filter((x) => x !== tag))}
            >
              ×
            </button>
          )}
        </S.Tag>
      ))}
      {!disabled && (
        <S.Add
          value={draft}
          placeholder={`+ ${t('ticket.addTag')}`}
          aria-label={t('ticket.addTag')}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={add}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault();
              add();
            }
          }}
        />
      )}
    </>
  );
}
