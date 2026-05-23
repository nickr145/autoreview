import shutil
import tempfile

import docker
from docker.errors import ContainerError, ImageNotFound

from core.config import settings

_client: docker.DockerClient | None = None


def _get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def run_in_sandbox(
    cmd: list[str],
    repo_path: str,
    writable: bool = False,
) -> tuple[int, str]:
    """Run cmd inside the sandbox container with repo_path mounted.

    Returns (exit_code, combined_stdout_stderr).
    network_mode=none prevents any outbound network access from the container.
    """
    client = _get_client()
    mode = "rw" if writable else "ro"
    try:
        container = client.containers.run(
            image="autoreview-sandbox:latest",
            command=cmd,
            volumes={repo_path: {"bind": "/sandbox", "mode": mode}},
            detach=True,
            mem_limit=settings.sandbox_mem_limit,
            network_mode="none",
        )
    except ImageNotFound:
        raise RuntimeError(
            "autoreview-sandbox:latest not found — run /sandbox-test to build it first"
        )

    try:
        result = container.wait()
        logs = container.logs(stdout=True, stderr=True).decode(errors="replace")
        return result["StatusCode"], logs
    finally:
        container.remove(force=True)


def clone_to_scratch(repo_path: str) -> str:
    """Copy repo_path into a fresh temp dir for writable patch application."""
    scratch = tempfile.mkdtemp(prefix="autoreview-scratch-")
    shutil.copytree(repo_path, scratch, dirs_exist_ok=True)
    return scratch
