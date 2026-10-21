import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { FormError } from '../../../../../../components/ui/Field';
import { Input } from '../../../../../../components/ui/Input';
import { relativeTime } from '../../../../../../lib/format';
import { isApiError } from '../../../../../../services/api/client';
import { folioKeys, queryDocs } from '../../../../../../services/api/folio';
import * as S from './style';

type Props = { rql: string; onRun: (rql: string) => void };

/** Query docs with RQL; an error points at the character it is about. */
export function RqlBar({ rql, onRun }: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(rql);
  const result = useQuery({
    queryKey: folioKeys.query(rql),
    queryFn: () => queryDocs(rql, 50),
    enabled: rql.trim().length > 0,
  });
  const position = isApiError(result.error) ? result.error.problem.position : undefined;

  return (
    <S.Section aria-labelledby="rql-heading">
      <S.Heading id="rql-heading">{t('folio.searchPage.rql')}</S.Heading>
      <S.Form
        onSubmit={(event) => {
          event.preventDefault();
          onRun(draft.trim());
        }}
      >
        <Input
          aria-label={t('folio.searchPage.rqlLabel')}
          placeholder="space = docs AND doc_type = how-to ORDER BY published DESC"
          value={draft}
          invalid={result.isError}
          onChange={(e) => setDraft(e.target.value)}
        />
        <Button type="submit">{t('folio.searchPage.run')}</Button>
      </S.Form>
      <FormError>{result.error?.message}</FormError>
      {position !== undefined && (
        <S.Caret aria-hidden>{`${rql}\n${' '.repeat(position)}^`}</S.Caret>
      )}
      {result.data &&
        (result.data.items.length === 0 ? (
          <S.Note>{t('folio.searchPage.rqlNone')}</S.Note>
        ) : (
          <S.Scroll>
            <S.Table>
              <thead>
                <tr>
                  <th>{t('folio.searchPage.docTitle')}</th>
                  <th>{t('folio.searchPage.space')}</th>
                  <th>{t('folio.searchPage.docType')}</th>
                  <th>{t('folio.searchPage.published')}</th>
                </tr>
              </thead>
              <tbody>
                {result.data.items.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <Link to="/folio/p/$page" params={{ page: `${doc.id}-${doc.slug}` }}>
                        {doc.title}
                      </Link>
                    </td>
                    <td>{doc.space}</td>
                    <td>{String(doc.metadata?.doc_type ?? '')}</td>
                    <td>
                      {doc.published_at
                        ? relativeTime(doc.published_at)
                        : t('folio.searchPage.draft')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </S.Table>
          </S.Scroll>
        ))}
    </S.Section>
  );
}
