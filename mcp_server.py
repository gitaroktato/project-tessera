"""Tessera MCP server — exposes document search tools to Claude Desktop."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path so `src` package resolves
_project_root = str(Path(__file__).parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp.server.fastmcp import FastMCP

from src.config import workspace
from src.search import invalidate_search_cache

# Configure logging: file + stderr
_log_dir = Path(_project_root) / "data" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
_file_handler = logging.handlers.RotatingFileHandler(
    _log_dir / "tessera.log",
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)
_file_handler.setLevel(logging.DEBUG)

_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setLevel(logging.WARNING)
_stderr_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

logging.basicConfig(level=logging.DEBUG, handlers=[_file_handler, _stderr_handler])

logger = logging.getLogger(__name__)

from src.search import search  # noqa: E402  — kept so tests can patch mcp_server.search

from src import core  # noqa: E402


mcp = FastMCP(
    name="tessera",
    instructions=(
        "Tessera provides semantic search across the user's local workspace documents "
        "and cross-session memory.\n\n"
        "## Auto-use rules\n"
        "When the user asks about topics that may be in their workspace, "
        "**call unified_search first** (searches documents AND memories together):\n"
        "- Project-related content (PRDs, specs, requirements)\n"
        "- Past decisions, meeting notes, session logs\n"
        "- Previously remembered facts or preferences\n\n"
    ),
)


# --- Tools (thin wrappers delegating to core) ---


@mcp.tool(
    description=(
        "Hybrid (semantic + keyword) search across indexed workspace documents "
        "(PRDs, decision logs, session logs, etc.). "
        "Call this tool first when the user asks about project-related content.\n\n"
        "Filter by project ID or doc_type (prd, session_log, decision_log, document)."
    )
)
def search_documents(
    query: str,
    top_k: int = 5,
    project: str | None = None,
    doc_type: str | None = None,
) -> str:
    """Search indexed documents with hybrid vector+keyword search."""
    # Sync the module-level `search` reference so tests patching
    # ``mcp_server.search`` propagate into core.
    core.search = search
    return core.search_documents(query, top_k=top_k, project=project, doc_type=doc_type)


@mcp.tool(
    description=(
        "Return full contents of a file as a structured view. "
        "CSV → markdown table, XLSX → tables per sheet, MD → raw text, DOCX → paragraphs. "
        "Use when the user wants to see the complete file, not just search results."
    )
)
def view_file_full(file_path: str) -> str:
    """Return full contents of any supported file as structured text."""
    return core.view_file_full(file_path)


@mcp.tool(description="List all indexed source files.")
def list_sources() -> str:
    """List all indexed source files."""
    return core.list_sources()


@mcp.tool(description="Read file contents by absolute path.")
def read_file(file_path: str) -> str:
    """Read file contents by path."""
    return core.read_file(file_path)


# TODO: Remove?
# @mcp.tool(
#     description=(
#         "Get project status including HANDOFF.md, recent changes, and file statistics. "
#         "Call automatically when asked about project status."
#     )
# )
def project_status(project_id: str | None = None) -> str:
    """Get project status. If no project_id, returns all projects summary."""
    return core.project_status(project_id)


# TODO: Remove?
# @mcp.tool(
#     description=(
#         "Audit a PRD file for quality and completeness against a 13-section structure. "
#         "Checks section coverage, Mermaid syntax, wireframes, versioning, and changelog.\n\n"
#         "check_sprawl=True: Detect multiple versions of the same PRD (suggest archiving old ones)\n"
#         "check_consistency=True: Check cross-PRD consistency for period selectors and tiers"
#     )
# )
def audit_prd(
    file_path: str,
    check_sprawl: bool = False,
    check_consistency: bool = False,
) -> str:
    """Audit a PRD file for quality and completeness."""
    return core.audit_prd(file_path, check_sprawl=check_sprawl, check_consistency=check_consistency)


# --- Memory Tools ---


# --- Knowledge Graph Tools ---


# TODO: Remove?
# @mcp.tool(
#     description=(
#         "Build a knowledge graph from indexed documents showing relationships "
#         "between concepts, decisions, and entities. "
#         "Returns a Mermaid diagram of the document relationships.\n\n"
#         "scope: 'project' (single project) or 'all' (entire workspace)\n"
#         "max_nodes: limit the number of nodes in the graph (default 30)"
#     )
# )
# def knowledge_graph(
#     query: str | None = None,
#     project: str | None = None,
#     scope: str = "all",
#     max_nodes: int = 30,
# ) -> str:
#     """Build and return a knowledge graph as Mermaid diagram."""
#     return core.knowledge_graph(query=query, project=project, scope=scope, max_nodes=max_nodes)
#
#
# @mcp.tool(
#     description=(
#         "Show connections for a specific document or concept in the knowledge graph. "
#         "Returns related documents, shared topics, and a focused Mermaid subgraph."
#     )
# )
# def explore_connections(query: str, top_k: int = 10) -> str:
#     """Explore connections around a specific topic or document."""
#     return core.explore_connections(query, top_k=top_k)


# --- Unified Search ---


# --- Indexing Tools ---


# --- Operations Tools ---


# --- Freshness Tools ---


# --- Analytics Tools ---

# --- Batch Memory Tools ---


# --- Similarity Tools ---


# --- Tag Tools ---


# --- MCP Resources ---


# TODO: Remove?
# @mcp.resource("docs://index")
# def document_index() -> str:
#     """Provide a browsable index of all indexed documents."""
#     return core.document_index()
#
#
# @mcp.resource("workspace://status")
# def workspace_status() -> str:
#     """Provide current workspace status across all projects."""
#     return core.workspace_status()


# --- Auto-Learn Tools ---


# --- Interaction Log Tools ---


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run(
        transport="streamable-http",
    )


if __name__ == "__main__":
    main()
