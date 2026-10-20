import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { adminKeys, fetchMcpTools, type McpTool } from '../../../../services/api/admin';
import * as S from './style';

type Props = {
  /** Allowed tool names, or null for every tool (including ones added later). */
  value: string[] | null;
  onChange: (value: string[] | null) => void;
};

function byGroup(tools: McpTool[]): [string, McpTool[]][] {
  const groups = new Map<string, McpTool[]>();
  for (const tool of tools) groups.set(tool.group, [...(groups.get(tool.group) ?? []), tool]);
  return [...groups];
}

/** Checkboxes for the MCP tools an agent may call, grouped, with quick presets. */
export function McpToolPicker({ value, onChange }: Props) {
  const { t } = useTranslation();
  const { data: tools } = useQuery({ queryKey: adminKeys.mcpTools, queryFn: fetchMcpTools });
  if (!tools) return <PageSpinner />;
  const all = value === null;
  const chosen = new Set(value ?? tools.map((tool) => tool.name));
  const set = (names: Set<string>) =>
    onChange(tools.filter((tool) => names.has(tool.name)).map((tool) => tool.name));
  const toggle = (names: string[], on: boolean) => {
    const next = new Set(chosen);
    for (const name of names) {
      if (on) next.add(name);
      else next.delete(name);
    }
    set(next);
  };

  return (
    <S.Wrap>
      <S.Presets>
        <S.Check>
          <input
            type="checkbox"
            checked={all}
            onChange={(e) => onChange(e.target.checked ? null : tools.map((tool) => tool.name))}
          />
          <span>
            <b>{t('admin.mcp.all')}</b>
            <small>{t('admin.mcp.allHint')}</small>
          </span>
        </S.Check>
        <Button
          size="sm"
          onClick={() => set(new Set(tools.filter((tool) => tool.read_only).map((x) => x.name)))}
        >
          {t('admin.mcp.readOnly')}
        </Button>
        <Button size="sm" onClick={() => set(new Set())}>
          {t('admin.mcp.none')}
        </Button>
      </S.Presets>
      <S.Count>
        {t('admin.mcp.count', { count: all ? tools.length : chosen.size, total: tools.length })}
      </S.Count>
      <S.Groups $disabled={all}>
        {byGroup(tools).map(([group, members]) => {
          const on = members.filter((tool) => chosen.has(tool.name)).length;
          return (
            <S.Group key={group} aria-label={t(`admin.mcp.groups.${group}`)}>
              <S.Check>
                <input
                  type="checkbox"
                  disabled={all}
                  checked={on === members.length}
                  ref={(el) => {
                    if (el) el.indeterminate = on > 0 && on < members.length;
                  }}
                  onChange={(e) =>
                    toggle(
                      members.map((tool) => tool.name),
                      e.target.checked,
                    )
                  }
                />
                <b>{t(`admin.mcp.groups.${group}`)}</b>
              </S.Check>
              {members.map((tool) => (
                <S.Tool key={tool.name} title={tool.description}>
                  <input
                    type="checkbox"
                    disabled={all}
                    aria-label={tool.name}
                    checked={chosen.has(tool.name)}
                    onChange={(e) => toggle([tool.name], e.target.checked)}
                  />
                  <code>{tool.name}</code>
                  {tool.read_only && <S.Read>{t('admin.mcp.read')}</S.Read>}
                  <small>{tool.description.split('\n')[0]}</small>
                </S.Tool>
              ))}
            </S.Group>
          );
        })}
      </S.Groups>
    </S.Wrap>
  );
}
