"""Folio's MCP prompts (Folio 4.7): recipes for agents that work with a codebase. Each one
writes a doc with Folio's tools and ends in submit_for_publication, so a Folio admin
approves what the agent wrote. Tool names go in backticks: a test checks they exist."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

SpaceArg = Annotated[str, Field(description="Key of the space to write in, e.g. eng")]

_ENDING = """
## Send it for approval

1. Read the draft back with `get_page` and fix anything that reads wrong.
2. Call `submit_for_publication` with a change note that says where the content came from.
3. Tell the user it waits for a Folio admin's approval, and check `list_my_submissions`
   later for the outcome. Never publish any other way.
"""

_BEFORE = """
## Before writing

1. Call `whoami` and check that you may create in the space "{space}".
2. Call `search_docs` with the topic, so you don't duplicate a doc that already exists:
   if it exists, change its draft with `update_draft` instead of creating another.
3. Call `get_metadata_schema`: publishing needs every required field (description,
   document type, owner, audiences, language).
"""


def weekly_changes(space: str, since: str, until: str, repo: str) -> str:
    return f"""Write the weekly changes post for the repository {repo or "in this workspace"}, \
covering the commits from {since} to {until}, in the Folio space "{space}".
{_BEFORE.format(space=space)}
## Gather the changes

1. Run `git log --no-merges {since}..{until}` in the repository (with `--stat` to see which
   modules each commit touches). Group the commits by area or module, not one by one.
2. Collect every Docket ticket key the commits mention (like PA-4 in a message, a branch
   name or a PR title).

## Write the post

1. Create it with `create_page`, kind "blog_post", a title like "Cambios del {since} al \
{until}" and Markdown with:
   - a two or three sentence summary of what the week brought, for people who don't read code;
   - one section per area with what changed and why, in plain words;
   - each ticket written as `:ticket[KEY]`, so readers see its live status.
2. Add a Mermaid diagram of what changed (the modules touched and how they connect) with
   `insert_diagram`, after the summary heading. Keep it under 15 nodes.
3. Link each ticket to its section with `link_ticket` (use the heading's anchor).
{_ENDING}"""


def document_module(space: str, module: str) -> str:
    return f"""Write the reference page for the module "{module}" of this codebase, in the \
Folio space "{space}".
{_BEFORE.format(space=space)}
## Read the module

1. Read its source: public functions, classes, endpoints or commands, and what calls it.
2. Note what it needs (configuration, other modules) and what can go wrong (errors it raises).

## Write the page

1. Create it with `create_page`, kind "page", document type "reference", with Markdown:
   - what the module is for, in two sentences;
   - its API as a table: name, what it does, arguments, what it returns;
   - a short example of the most common use;
   - errors and limits.
2. Add a Mermaid diagram with `insert_diagram` showing the module and the modules it talks to.
3. If a Docket ticket covers this module, link it with `link_ticket`.
{_ENDING}"""


def build_spec_from_discussion(space: str, title: str, discussion: str) -> str:
    return f"""Turn this discussion into a build spec titled "{title}" in the Folio space \
"{space}".

<discussion>
{discussion}
</discussion>
{_BEFORE.format(space=space)}
## Write the build spec

1. Find the Build spec template with `list_templates` and create the page from it with
   `create_from_template`: it comes with its sections and its metadata.
2. Fill each section from the discussion with `update_draft`: goal and scope, the
   deliverables table (one row per deliverable, with when it is accepted), data model,
   API and MCP, UI, tests, acceptance criteria and what stays out of scope.
3. Write only what the discussion decided. List open questions in their own section
   instead of inventing answers.
4. Check the deliverables with `get_build_spec_items`; once approved, people can turn them
   into Docket tickets.
{_ENDING}"""


def register(server: MCPServer) -> None:
    @server.prompt(
        title="Weekly changes post",
        description="A blog post with a range of commits' changes, a diagram and their tickets",
    )
    def weekly_changes_post(
        space: SpaceArg,
        since: Annotated[str, Field(description="First commit, tag or date, e.g. v1.4")],
        until: Annotated[str, Field(description="Last commit, tag or date")] = "HEAD",
        repo: Annotated[str, Field(description="The repository's name")] = "",
    ) -> str:
        return weekly_changes(space, since, until, repo)

    @server.prompt(
        name="document_module",
        title="Document a module",
        description="A reference page for one module of the codebase, with its API and a diagram",
    )
    def document_module_prompt(
        space: SpaceArg,
        module: Annotated[str, Field(description="Path or name, e.g. backend/radicle/auth")],
    ) -> str:
        return document_module(space, module)

    @server.prompt(
        name="build_spec_from_discussion",
        title="Build spec from a discussion",
        description="Turn a conversation into a build spec with the Build spec template",
    )
    def build_spec_prompt(
        space: SpaceArg,
        title: str,
        discussion: Annotated[str, Field(description="The conversation, as text")],
    ) -> str:
        return build_spec_from_discussion(space, title, discussion)
