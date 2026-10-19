import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { Button } from '../../../../components/ui/Button';
import { Input, Textarea } from '../../../../components/ui/Input';
import { parseDuration } from '../../../../lib/duration';
import { type Values, toBody } from '../../../../lib/schemaForm';
import { fetchSchema, screenKeys } from '../../../../services/api/screens';
import type { Resolution, TicketType, TransitionOption } from '../../../../services/api/types';
import { SchemaFields } from '../SchemaFields';
import * as S from './style';

export type Pick = {
  option: TransitionOption;
  resolution: Resolution | null;
  comment?: string | null;
  fields?: Record<string, unknown> | null;
  logMinutes?: number | null;
};

type Props = {
  options: TransitionOption[];
  onPick: (pick: Pick) => void;
  /** Preselect a transition, e.g. after a drop, so only what is missing is asked. */
  initial?: TransitionOption | null;
  /** Where the ticket lives, to load the fields of transition screens. */
  projectKey?: string;
  ticketType?: TicketType;
};

function needsForm(option: TransitionOption): boolean {
  const resolutions = option.allowed_resolutions ?? [];
  return (
    option.requires_comment ||
    option.has_screen ||
    (option.category === 'done' && resolutions.length > 1)
  );
}

/**
 * Lists transitions. Unavailable ones show why. When a transition needs a resolution
 * choice or a comment, a small form asks for it; otherwise one click moves the ticket.
 */
export function TransitionPicker({
  options,
  onPick,
  initial = null,
  projectKey = '',
  ticketType = 'task',
}: Props) {
  const { t } = useTranslation();
  const [pending, setPending] = useState<TransitionOption | null>(
    initial && needsForm(initial) ? initial : null,
  );
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const [comment, setComment] = useState('');
  const [logTime, setLogTime] = useState('');
  const logMinutes = parseDuration(logTime);
  const [values, setValues] = useState<Values>({});
  const { data: screen } = useQuery({
    queryKey: screenKeys.schema(projectKey, ticketType, 'transition', pending?.name),
    queryFn: () => fetchSchema(projectKey, ticketType, 'transition', pending!.name),
    enabled: Boolean(pending?.has_screen && projectKey),
  });

  if (options.length === 0) return <S.Empty>{t('ticket.noTransitions')}</S.Empty>;

  const choose = (option: TransitionOption) => {
    if (!needsForm(option)) {
      onPick({ option, resolution: option.allowed_resolutions?.[0] ?? null });
      return;
    }
    setPending(option);
    setResolution(option.allowed_resolutions?.length === 1 ? option.allowed_resolutions[0]! : null);
  };

  const resolutions = pending?.allowed_resolutions ?? [];
  const missingResolution = pending?.category === 'done' && resolutions.length > 1 && !resolution;
  const missingComment = pending?.requires_comment && !comment.trim();

  return (
    <S.List role="menu">
      {options.map((option) => (
        <S.Option
          key={`${option.name}-${option.to_status}`}
          role="menuitem"
          $selected={pending === option}
          disabled={!option.available}
          aria-disabled={!option.available}
          title={option.reasons.map((r) => r.message).join(' ') || undefined}
          onClick={() => option.available && choose(option)}
        >
          <CategoryIcon category={option.category} />
          <S.Label>
            {option.to_status}
            {!option.available && <S.Reason>{option.reasons[0]?.message}</S.Reason>}
          </S.Label>
          <S.Via>{option.name}</S.Via>
          {option.available && !needsForm(option) && (
            <S.More
              role="button"
              tabIndex={0}
              aria-label={t('ticket.moreOptions', { status: option.to_status })}
              title={t('ticket.moreOptions', { status: option.to_status })}
              onClick={(e) => {
                e.stopPropagation();
                setPending(option);
              }}
              onKeyDown={(e) => {
                if (e.key !== 'Enter') return;
                e.stopPropagation();
                e.preventDefault();
                setPending(option);
              }}
            >
              ⋯
            </S.More>
          )}
        </S.Option>
      ))}
      {pending && (
        <S.Form
          onSubmit={(e) => {
            e.preventDefault();
            if (missingResolution || missingComment) return;
            const { body, custom } = toBody(values);
            const fields = {
              ...body,
              ...Object.fromEntries(Object.entries(custom).map(([k, v]) => [`cf.${k}`, v])),
            };
            onPick({
              option: pending,
              resolution,
              comment: comment.trim() || null,
              fields: Object.keys(fields).length ? fields : null,
              ...(logMinutes ? { logMinutes } : {}),
            });
          }}
        >
          {pending.category === 'done' && resolutions.length > 1 && (
            <>
              <strong>{t('ticket.pickResolution', { status: pending.to_status })}</strong>
              <S.Chips role="radiogroup" aria-label={t('ticket.fields.resolution')}>
                {resolutions.map((r) => (
                  <Button
                    key={r}
                    size="sm"
                    role="radio"
                    aria-checked={resolution === r}
                    variant={resolution === r ? 'primary' : 'secondary'}
                    onClick={() => setResolution(r)}
                  >
                    {t(`ticket.resolutions.${r}`)}
                  </Button>
                ))}
              </S.Chips>
            </>
          )}
          {screen && (
            <SchemaFields
              fields={screen.fields}
              values={values}
              onChange={(name, value) => setValues((v) => ({ ...v, [name]: value }))}
            />
          )}
          <Textarea
            aria-label={t('ticket.moveComment')}
            placeholder={
              pending.requires_comment ? t('ticket.moveCommentRequired') : t('ticket.moveComment')
            }
            rows={2}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <Input
            aria-label={t('time.logInMove')}
            placeholder={t('time.logInMove')}
            value={logTime}
            onChange={(e) => setLogTime(e.target.value)}
          />
          <Button
            type="submit"
            size="sm"
            variant="primary"
            disabled={Boolean(missingResolution || missingComment || (logTime && !logMinutes))}
          >
            {t('ticket.moveTo', { status: pending.to_status })}
          </Button>
        </S.Form>
      )}
    </S.List>
  );
}
