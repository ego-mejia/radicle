import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { useTranslation } from 'react-i18next';
import { Field } from '../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../components/ui/Input';
import type { PluginBlockField } from '../../../../services/api/plugins';
import { usePluginBlocks } from '../../hooks/usePluginBlocks';
import { PluginFrame } from '../PluginFrame';
import * as S from './style';

function Control({
  field,
  value,
  onChange,
  ...aria
}: {
  field: PluginBlockField;
  value: string;
  onChange: (value: string) => void;
  /** Field passes the label's id and the hint's. */
  id?: string;
  'aria-describedby'?: string;
}) {
  if (field.kind === 'textarea')
    return <Textarea {...aria} rows={3} value={value} onChange={(e) => onChange(e.target.value)} />;
  if (field.kind === 'select')
    return (
      <Select {...aria} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="" />
        {field.options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </Select>
    );
  const type = field.kind === 'date' ? 'date' : field.kind === 'number' ? 'number' : 'text';
  return <Input {...aria} type={type} value={value} onChange={(e) => onChange(e.target.value)} />;
}

/** A plugin block in the editor: its fields while it's selected (or a required one is
 * empty), and the block as readers will see it. */
export function PluginBlockEditor({ node, updateAttributes, selected }: NodeViewProps) {
  const { t } = useTranslation();
  const plugin = String(node.attrs.plugin ?? '');
  const block = String(node.attrs.block ?? '');
  const data = (node.attrs.data as Record<string, string> | null) ?? {};
  const def = usePluginBlocks().byId.get(`${plugin}/${block}`);
  const missing = def?.fields.some((f) => f.required && !data[f.key]) ?? false;
  const set = (key: string, value: string) => updateAttributes({ data: { ...data, [key]: value } });

  return (
    <NodeViewWrapper data-folio="plugin" contentEditable={false}>
      {def && (selected || missing) && def.fields.length > 0 && (
        <S.Fields>
          <S.Head>
            {def.icon && <span aria-hidden>{def.icon}</span>}
            {def.name}
          </S.Head>
          {def.fields.map((f) => (
            <Field
              key={f.key}
              label={f.required ? f.label : `${f.label} (${t('common.optional')})`}
            >
              <Control field={f} value={data[f.key] ?? ''} onChange={(v) => set(f.key, v)} />
            </Field>
          ))}
        </S.Fields>
      )}
      <PluginFrame plugin={plugin} block={block} data={data} />
    </NodeViewWrapper>
  );
}
