import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownEditor, type MentionOption } from '../../../../components/Markdown/MarkdownEditor';
import { MarkdownView } from '../../../../components/Markdown/MarkdownView';
import { Button } from '../../../../components/ui/Button';
import type { Ticket } from '../../../../services/api/types';
import type { TicketActions } from '../../hooks/useTicket';
import * as S from './style';

type Props = {
  ticket: Ticket;
  actions: TicketActions;
  canEdit: boolean;
  mentions: MentionOption[];
};

/** Rendered description; click to edit in CodeMirror. Checklist items toggle in place. */
export function Description({ ticket, actions, canEdit, mentions }: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<string | null>(null);
  const done = ticket.checklist.filter((i) => i.checked).length;

  const save = () => {
    if (draft === null) return;
    if (draft === ticket.description_md) {
      setDraft(null);
      return;
    }
    actions.patch.mutate({ description_md: draft }, { onSuccess: () => setDraft(null) });
  };

  return (
    <S.Section>
      <S.Label>
        {t('ticket.fields.description')}
        {ticket.checklist.length > 0 && (
          <S.Progress>
            {t('ticket.checklistProgress', { done, total: ticket.checklist.length })}
          </S.Progress>
        )}
      </S.Label>
      {draft !== null ? (
        <>
          <MarkdownEditor
            value={draft}
            onChange={setDraft}
            mentions={mentions}
            autoFocus
            onSubmit={save}
            ariaLabel={t('ticket.fields.description')}
            placeholder={t('create.descriptionPlaceholder')}
          />
          <S.Actions>
            <Button variant="primary" size="sm" onClick={save} disabled={actions.patch.isPending}>
              {t('common.save')}
            </Button>
            <Button size="sm" onClick={() => setDraft(null)}>
              {t('common.cancel')}
            </Button>
          </S.Actions>
        </>
      ) : (
        <S.View
          $editable={canEdit}
          onClick={(e) => {
            const target = e.target as HTMLElement;
            if (!canEdit || target.closest('input, a, button')) return;
            setDraft(ticket.description_md);
          }}
        >
          {ticket.description_md.trim() ? (
            <MarkdownView
              checklist={ticket.checklist}
              readOnly={!canEdit}
              onToggle={(index, checked) => actions.toggleItem.mutate({ index, checked })}
            >
              {ticket.description_md}
            </MarkdownView>
          ) : (
            <S.Placeholder>{canEdit ? t('ticket.noDescription') : '—'}</S.Placeholder>
          )}
        </S.View>
      )}
    </S.Section>
  );
}
