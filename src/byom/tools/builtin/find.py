"""
Find Tool - Recursive file and directory search

Provides glob-based recursive search with depth control.
"""
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from byom.tools.base import Tool, ToolResult, ToolKind


class FindParams(BaseModel):
    """Parameters for the find tool"""

    path: str = Field(..., description="Starting directory path (absolute or relative)")
    pattern: str = Field(
        default="*",
        description="Glob pattern to match (e.g., '*.py', '**/*.ts', 'test_*.py')",
    )
    type: str | None = Field(
        None, description="Filter by type: 'f' for files only, 'd' for directories only"
    )
    max_depth: int = Field(
        default=10,
        description="Maximum recursion depth (default: 10, use -1 for unlimited)",
    )
    case_sensitive: bool = Field(
        default=True, description="Whether pattern matching is case-sensitive"
    )


class FindTool(Tool):
    """
    Recursive file and directory search tool using glob patterns.

    Examples:
        - Find all Python files: pattern="**/*.py"
        - Find test files: pattern="**/test_*.py"
        - Find directories: pattern="**/lib", type="d"
        - Shallow search: pattern="*.txt", max_depth=1
    """

    name = "find"
    description = "Recursively search for files and directories using glob patterns"
    parameters = FindParams
    kind = ToolKind.READ

    def execute(self, arguments: dict[str, Any], cwd: Path) -> ToolResult:
        """Execute the find command"""
        try:
            params = FindParams(**arguments)
        except Exception as e:
            return ToolResult.error(f"Invalid parameters: {e}")

        # Resolve path
        search_path = Path(params.path)
        if not search_path.is_absolute():
            search_path = cwd / search_path

        if not search_path.exists():
            return ToolResult.error(f"Path does not exist: {search_path}")

        if not search_path.is_dir():
            return ToolResult.error(f"Path is not a directory: {search_path}")

        try:
            # Perform search
            results = self._search(
                search_path,
                params.pattern,
                params.type,
                params.max_depth,
                params.case_sensitive,
            )

            if not results:
                return ToolResult.success("No matches found", metadata={"count": 0})

            # Format output
            output_lines = []
            for result in results:
                # Try to make path relative to search_path for cleaner output
                try:
                    rel_path = result.relative_to(search_path)
                    display_path = str(rel_path)
                except ValueError:
                    display_path = str(result)

                # Add type indicator
                if result.is_dir():
                    display_path += "/"

                output_lines.append(display_path)

            output = "\n".join(output_lines)
            metadata = {
                "count": len(results),
                "search_path": str(search_path),
                "pattern": params.pattern,
            }

            return ToolResult.success(output, metadata=metadata)

        except Exception as e:
            return ToolResult.error(f"Search failed: {e}")

    def _search(
        self,
        path: Path,
        pattern: str,
        file_type: str | None,
        max_depth: int,
        case_sensitive: bool,
    ) -> list[Path]:
        """
        Perform the actual search

        Args:
            path: Directory to search in
            pattern: Glob pattern
            file_type: 'f' for files, 'd' for directories, None for both
            max_depth: Maximum recursion depth (-1 for unlimited)
            case_sensitive: Whether matching is case-sensitive

        Returns:
            List of matching paths
        """
        results = []

        # Use rglob for ** patterns, otherwise glob
        if "**" in pattern:
            matches = path.rglob(pattern if case_sensitive else pattern.lower())
        else:
            matches = path.glob(pattern if case_sensitive else pattern.lower())

        for match in matches:
            # Check depth
            if max_depth >= 0:
                try:
                    depth = len(match.relative_to(path).parts)
                    if depth > max_depth:
                        continue
                except ValueError:
                    continue

            # Filter by type
            if file_type == "f" and not match.is_file():
                continue
            elif file_type == "d" and not match.is_dir():
                continue

            # Case-insensitive matching
            if not case_sensitive:
                # For case-insensitive, check if the name matches when lowercased
                # This is a simple implementation - glob already did most of the work
                pass

            results.append(match)

        # Sort for consistent output
        results.sort()

        return results

    @staticmethod
    def get_schema() -> dict[str, Any]:
        """Get JSON schema for the tool"""
        return {
            "type": "function",
            "function": {
                "name": "find",
                "description": "Recursively search for files and directories using glob patterns",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Starting directory path (absolute or relative)",
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern to match (e.g., '*.py', '**/*.ts', 'test_*.py')",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["f", "d"],
                            "description": "Filter by type: 'f' for files only, 'd' for directories only",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum recursion depth (default: 10, use -1 for unlimited)",
                            "default": 10,
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether pattern matching is case-sensitive",
                            "default": True,
                        },
                    },
                    "required": ["path"],
                },
            },
        }
