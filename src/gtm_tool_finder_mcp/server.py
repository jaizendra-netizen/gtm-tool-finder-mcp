"""gtm-tool-finder-mcp: a Model Context Protocol server over the public OneGTMLab tool directory.

Offline: the directory index ships inside the package (data.json), no network calls, no API keys.
Docs and the live directory: https://www.onegtmlab.dev/tool-directory
"""
import json
from importlib import resources

from mcp.server.fastmcp import FastMCP

KINDS = ("Tool", "Category", "Comparison", "Glossary")
DIRECTORY_URL = "https://www.onegtmlab.dev/tool-directory"

mcp = FastMCP("gtm-tool-finder")
_cache = None


def _load():
    global _cache
    if _cache is None:
        raw = json.loads(resources.files(__package__).joinpath("data.json").read_text(encoding="utf-8"))
        _cache = [{"name": r["n"], "kind": r["k"], "url": r["u"], "description": r["d"]} for r in raw]
    return _cache


def _kind_ok(kind):
    return kind is None or kind == "" or kind.lower() in [k.lower() for k in KINDS]


@mcp.tool()
def search_tools(query: str, kind: str = "", limit: int = 10) -> list:
    """Search the OneGTMLab GTM tool directory by keyword.

    Matches entries whose name or description contains every word of the query, for example
    "apollo", "clay enrichment" or "rate limits". Returns name, kind, url and description.

    Args:
        query: words to look for, e.g. "apollo" or "lead enrichment".
        kind: optional filter, one of Tool, Category, Comparison, Glossary (case-insensitive).
        limit: maximum number of results (1 to 50).
    """
    if not _kind_ok(kind):
        return [{"error": f"kind must be one of {', '.join(KINDS)}"}]
    limit = max(1, min(int(limit), 50))
    words = query.lower().split()
    order = {k: i for i, k in enumerate(KINDS)}
    hits = [r for r in _load()
            if (not kind or r["kind"].lower() == kind.lower())
            and all(w in (r["name"] + " " + r["description"]).lower() for w in words)]
    hits.sort(key=lambda r: (0 if words and r["name"].lower().startswith(words[0]) else 1, order[r["kind"]]))
    return hits[:limit]


@mcp.tool()
def get_tool(name: str) -> dict:
    """Get one directory entry by name (case-insensitive; exact match first, then the closest partial match).

    Args:
        name: entry name such as "Apollo", "Apollo vs Clay" or "Account-Based Marketing (ABM)".
    """
    n = name.strip().lower()
    rows = _load()
    for r in rows:
        if r["name"].lower() == n:
            return r
    partial = [r for r in rows if n and n in r["name"].lower()]
    if partial:
        partial.sort(key=lambda r: (len(r["name"]), KINDS.index(r["kind"])))
        return partial[0]
    return {"error": f"No entry named '{name}'. Try search_tools first.", "directory": DIRECTORY_URL}


@mcp.tool()
def list_categories() -> dict:
    """List the kinds of pages in the directory with counts and the full list of Category pages."""
    rows = _load()
    counts = {k: sum(1 for r in rows if r["kind"] == k) for k in KINDS}
    return {
        "directory": DIRECTORY_URL,
        "kinds": counts,
        "categories": [r for r in rows if r["kind"] == "Category"],
    }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
