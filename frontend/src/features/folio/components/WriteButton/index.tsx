import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import {
  createFromTemplate,
  createNode,
  fetchSpaces,
  folioKeys,
} from '../../../../services/api/folio';
import { TemplatePicker } from '../TemplatePicker';
import * as S from './style';

type Kind = 'page' | 'blog_post';

/** "Write": choose a space, page or blog post and a title, then go to the editor. */
export function WriteButton() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [space, setSpace] = useState('');
  const [kind, setKind] = useState<Kind>('blog_post');
  const [title, setTitle] = useState('');
  const [template, setTemplate] = useState<string | null>(null);
  const { data: spaces = [] } = useQuery({
    queryKey: folioKeys.spaces,
    queryFn: fetchSpaces,
    enabled: open,
  });
  const writable = spaces.filter((s) => s.permissions.includes('create'));
  const chosen = space || writable[0]?.key || '';

  const create = useMutation({
    mutationFn: () =>
      template
        ? createFromTemplate({ template, space: chosen, kind, title: title.trim() })
        : createNode({ space: chosen, kind, title: title.trim() }),
    onSuccess: (node) => {
      // The button lives in the shell's bar, so it stays mounted: close and reset it.
      setOpen(false);
      setTitle('');
      setTemplate(null);
      void navigate({ to: '/folio/p/$page/edit', params: { page: `${node.id}-${node.slug}` } });
    },
  });

  return (
    <>
      <Button variant="primary" onClick={() => setOpen(true)}>
        <Plus aria-hidden />
        {t('folio.home.write')}
      </Button>
      <Modal open={open} onOpenChange={setOpen} title={t('folio.home.writeTitle')} width={760}>
        <S.Form
          onSubmit={(event) => {
            event.preventDefault();
            create.mutate();
          }}
        >
          {writable.length === 0 ? (
            <FormError>{t('folio.home.noWritableSpace')}</FormError>
          ) : (
            <Field label={t('folio.home.space')}>
              <Select value={chosen} onChange={(e) => setSpace(e.target.value)}>
                {writable.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}
          <Field label={t('folio.home.kind')}>
            <Select value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
              <option value="blog_post">{t('folio.home.kinds.blog_post')}</option>
              <option value="page">{t('folio.home.kinds.page')}</option>
            </Select>
          </Field>
          {chosen && <TemplatePicker space={chosen} value={template} onChange={setTemplate} />}
          <Field label={t('folio.home.docTitle')}>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </Field>
          <FormError>{create.error?.message}</FormError>
          <S.Actions>
            <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
            <Button
              type="submit"
              variant="primary"
              disabled={!chosen || !title.trim() || create.isPending}
            >
              {t('folio.home.startWriting')}
            </Button>
          </S.Actions>
        </S.Form>
      </Modal>
    </>
  );
}
