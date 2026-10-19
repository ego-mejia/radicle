import { Link } from '@tanstack/react-router';
import { Plus, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { TicketKey } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Input, Select } from '../../../../components/ui/Input';
import { LINK_TYPES, type Ticket } from '../../../../services/api/types';
import type { TicketActions } from '../../hooks/useTicket';
import { Section, SectionParts as S } from '../Section';

const LABEL_ORDER = [
  'blocks',
  'is blocked by',
  'relates to',
  'duplicates',
  'is duplicated by',
  'clones',
  'is cloned by',
];

type Props = { ticket: Ticket; actions: TicketActions; canEdit: boolean };

/** Links grouped by label as seen from this ticket, plus a quick form to add one. */
export function Links({ ticket, actions, canEdit }: Props) {
  const { t } = useTranslation();
  const [adding, setAdding] = useState(false);
  const [type, setType] = useState<string>('blocks');
  const [target, setTarget] = useState('');
  const groups = LABEL_ORDER.map((label) => ({
    label,
    links: ticket.links.filter((l) => l.label === label),
  })).filter((g) => g.links.length > 0);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!target.trim()) return;
    actions.addLink.mutate(
      { type, target: target.trim().toUpperCase() },
      {
        onSuccess: () => {
          setTarget('');
          setAdding(false);
        },
      },
    );
  };

  return (
    <Section
      title={t('ticket.links')}
      action={
        canEdit &&
        !adding && (
          <Button size="sm" variant="ghost" onClick={() => setAdding(true)}>
            <Plus />
            {t('ticket.addLink')}
          </Button>
        )
      }
    >
      {adding && (
        <S.Form onSubmit={submit}>
          <Select
            value={type}
            onChange={(e) => setType(e.target.value)}
            aria-label={t('ticket.links')}
          >
            {LINK_TYPES.map((value) => (
              <option key={value} value={value}>
                {t(`ticket.linkTypes.${value}`)}
              </option>
            ))}
          </Select>
          <Input
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder={t('ticket.linkTarget')}
            aria-label={t('ticket.linkTarget')}
            autoFocus
          />
          <Button type="submit" variant="primary" disabled={actions.addLink.isPending}>
            {t('common.add')}
          </Button>
          <Button onClick={() => setAdding(false)}>{t('common.cancel')}</Button>
        </S.Form>
      )}
      {groups.length === 0 && !adding && <S.Muted>{t('ticket.noLinks')}</S.Muted>}
      {groups.map((group) => (
        <S.Group key={group.label}>
          <S.GroupLabel>{t(`ticket.linkLabels.${group.label}`)}</S.GroupLabel>
          {group.links.map((link) => (
            <S.Row key={link.id}>
              <Link to="/t/$key" params={{ key: link.ticket.key }}>
                <CategoryIcon
                  category={link.ticket.status.category}
                  title={link.ticket.status.name}
                />
                <TicketKey>{link.ticket.key}</TicketKey>
                <span className="title">{link.ticket.title}</span>
              </Link>
              {canEdit && (
                <IconButton
                  label={`${t('common.remove')} ${link.ticket.key}`}
                  onClick={() => actions.removeLink.mutate(link.id)}
                >
                  <X />
                </IconButton>
              )}
            </S.Row>
          ))}
        </S.Group>
      ))}
    </Section>
  );
}
