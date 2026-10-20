import type { TFunction } from 'i18next';

/** "All MCP tools" or "12 MCP tools" for an agent's limit. */
export function mcpSummary(t: TFunction, agent: { mcp_tools?: string[] | null }): string {
  return agent.mcp_tools == null
    ? t('admin.mcp.summaryAll')
    : t('admin.mcp.summarySome', { count: agent.mcp_tools.length });
}
