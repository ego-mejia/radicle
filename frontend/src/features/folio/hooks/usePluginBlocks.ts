import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo } from 'react';
import { fetchPluginBlocks, type PluginBlock, pluginKeys } from '../../../services/api/plugins';
import { setPluginBlocks } from '../editor/pluginBlocks';

/** The blocks of the plugins that are on, by `plugin/type`; also feeds the `/` menu. */
export function usePluginBlocks(enabled = true) {
  const query = useQuery({
    queryKey: pluginKeys.blocks,
    queryFn: fetchPluginBlocks,
    staleTime: 60_000,
    enabled,
  });
  useEffect(() => {
    if (query.data) setPluginBlocks(query.data);
  }, [query.data]);
  const byId = useMemo(
    () => new Map<string, PluginBlock>((query.data ?? []).map((b) => [b.id, b])),
    [query.data],
  );
  return { ...query, byId };
}
