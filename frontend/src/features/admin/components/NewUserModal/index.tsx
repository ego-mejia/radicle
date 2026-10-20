import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { McpToolPicker } from '../McpToolPicker';
import * as S from './style';

export type NewPerson = {
  kind: 'human' | 'agent';
  handle: string;
  display_name: string;
  email: string;
  password: string;
  /** Agents: MCP tools it may call; null means all. */
  mcp_tools: string[] | null;
};

type Props = {
  kind: 'human' | 'agent';
  /** Let the admin pick between a person and an agent (LLM or worker). */
  choose?: boolean;
  onClose: () => void;
  onCreate: (person: NewPerson) => Promise<unknown>;
};

/** New human (email and temporary password) or agent (handle, name and MCP tools). */
export function NewUserModal({ kind, choose = false, onClose, onCreate }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [form, setForm] = useState<NewPerson>({
    kind,
    handle: '',
    display_name: '',
    email: '',
    password: '',
    mcp_tools: null,
  });
  const mutation = useMutation({ mutationFn: () => onCreate(form), onSuccess: onClose });
  const human = form.kind === 'human';
  const set = (name: keyof NewPerson) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [name]: name === 'handle' ? e.target.value.toLowerCase() : e.target.value });

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={choose ? t('admin.newUser') : human ? t('admin.newUser') : t('admin.newAgent')}
      width={human ? undefined : 760}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="new-person"
            disabled={mutation.isPending}
            data-tour="user-form.submit"
          >
            {t('common.create')}
          </Button>
        </>
      }
    >
      <S.Form
        id="new-person"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <FormError>{mutation.error ? errorMessage(mutation.error) : null}</FormError>
        {choose && (
          <S.Kinds role="radiogroup" aria-label={t('admin.kind')} data-tour="user-form.kind">
            {(['human', 'agent'] as const).map((k) => (
              <S.Kind key={k} $active={form.kind === k}>
                <input
                  type="radio"
                  name="kind"
                  checked={form.kind === k}
                  onChange={() => setForm({ ...form, kind: k })}
                />
                <span>
                  <b>{t(`admin.kinds.${k}`)}</b>
                  <small>{t(`admin.kinds.${k}Hint`)}</small>
                </span>
              </S.Kind>
            ))}
          </S.Kinds>
        )}
        <Field label={t('auth.displayName')}>
          <Input
            value={form.display_name}
            onChange={set('display_name')}
            required
            autoFocus
            data-tour="user-form.name"
          />
        </Field>
        <Field label={t('auth.handle')} hint={t('auth.handleHint')}>
          <Input
            value={form.handle}
            onChange={set('handle')}
            data-tour="user-form.handle"
            required
            placeholder={human ? 'ana' : 'agent-backend'}
          />
        </Field>
        {human && (
          <>
            <Field label={t('auth.email')}>
              <Input type="email" value={form.email} onChange={set('email')} required />
            </Field>
            <Field label={t('admin.tempPassword')} hint={t('auth.passwordHint')}>
              <Input value={form.password} onChange={set('password')} required minLength={8} />
            </Field>
          </>
        )}
        {!human && (
          <Field label={t('admin.mcp.title')} hint={t('admin.mcp.help')} group>
            <div data-tour="user-form.mcp">
              <McpToolPicker
                value={form.mcp_tools}
                onChange={(mcp_tools) => setForm({ ...form, mcp_tools })}
              />
            </div>
          </Field>
        )}
      </S.Form>
    </Modal>
  );
}
