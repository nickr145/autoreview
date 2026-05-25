import os
import tempfile


_SUPPORTED_EXTS = (".py", ".ts", ".tsx", ".js")


def extract_diff_files(pr_diff: str) -> str:
    """
    Parse a unified diff and write the added-line content for each file
    into a fresh temp directory. Only .py / .ts / .tsx / .js files are extracted.
    Returns the path to the temp directory (caller is responsible for cleanup).
    """
    scratch = tempfile.mkdtemp(prefix="autoreview-audit-")
    current_file: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        nonlocal current_file, current_lines
        if current_file and current_lines:
            dest = os.path.join(scratch, current_file)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w") as fh:
                fh.writelines(current_lines)
        current_file = None
        current_lines = []

    for line in pr_diff.splitlines():
        if line.startswith("+++ b/"):
            _flush()
            rel = line[6:]
            current_file = rel if rel.endswith(_SUPPORTED_EXTS) else None
        elif line.startswith("+++"):
            _flush()
        elif line.startswith("+") and not line.startswith("+++") and current_file:
            current_lines.append(line[1:] + "\n")

    _flush()
    return scratch
