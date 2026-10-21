import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Input } from '../../../../../../components/ui/Input';
import * as S from './style';

/** The home's search block: Enter opens the search page with what was typed. */
export function SearchBox({ label }: { label: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [text, setText] = useState('');
  return (
    <S.Form
      role="search"
      aria-label={label}
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim()) void navigate({ to: '/folio/search', search: { q: text.trim() } });
      }}
    >
      <S.Label>{label}</S.Label>
      <Input
        type="search"
        aria-label={label}
        placeholder={t('folio.searchPlaceholder')}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
    </S.Form>
  );
}
