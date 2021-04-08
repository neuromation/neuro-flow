from dataclasses import dataclass

import aiohttp
import logging
import os
import pathlib
import pytest
import secrets
import shutil
import subprocess
from neuro_sdk import Config, get as api_get, login_with_token
from pathlib import Path
from typing import Any, AsyncIterator, Callable, List, Optional
from yarl import URL


NETWORK_TIMEOUT = 3 * 60.0
CLIENT_TIMEOUT = aiohttp.ClientTimeout(None, None, NETWORK_TIMEOUT, NETWORK_TIMEOUT)

log = logging.getLogger(__name__)


@pytest.fixture
def assets() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "assets"


@pytest.fixture
def project_id() -> str:
    return f"e2e_proj_{secrets.token_hex(10)}"


async def get_config(nmrc_path: Optional[Path]) -> Config:
    __tracebackhide__ = True
    async with api_get(timeout=CLIENT_TIMEOUT, path=nmrc_path) as client:
        return client.config


@pytest.fixture
async def username(api_config: Optional[pathlib.Path]) -> Optional[str]:
    config = await get_config(api_config)
    return config.username


@pytest.fixture
def ws(
    assets: pathlib.Path,
    tmp_path_factory: Any,
    project_id: str,
    username: Optional[str],
) -> pathlib.Path:
    tmp_dir: pathlib.Path = tmp_path_factory.mktemp("proj-dir-parent")
    ws_dir = tmp_dir / project_id
    shutil.copytree(assets / "ws", ws_dir)
    project_data = f"id: {project_id}"
    if username:
        project_data += f"\nowner: {username}"
    print(f"project_data = {project_data!r}")
    (ws_dir / "project.yml").write_text(project_data)
    return ws_dir


@pytest.fixture
async def api_config(tmp_path_factory: Any) -> AsyncIterator[Optional[pathlib.Path]]:
    e2e_test_token = os.environ.get("E2E_USER_TOKEN")
    if e2e_test_token:
        tmp_path = tmp_path_factory.mktemp("config")
        config_path = tmp_path / "conftest"
        await login_with_token(
            e2e_test_token,
            url=URL("https://dev.neu.ro/api/v1"),
            path=config_path,
        )
    else:
        config_path = None
    yield config_path


@dataclass(frozen=True)
class SysCap:
    out: str
    err: str


RunCLI = Callable[[List[str]], SysCap]


@pytest.fixture
def run_cli(loop: None, ws: pathlib.Path, api_config: Optional[pathlib.Path]) -> RunCLI:
    def _run(
        arguments: List[str],
    ) -> SysCap:
        if api_config:
            os.environ["NEUROMATION_CONFIG"] = str(api_config)
        proc = subprocess.run(
            ["neuro-flow"] + arguments,
            timeout=600,
            cwd=ws,
            encoding="utf8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            proc.check_returncode()
        except subprocess.CalledProcessError:
            log.error(f"Last stdout: '{proc.stdout}'")
            log.error(f"Last stderr: '{proc.stderr}'")
            raise
        return SysCap(out=proc.stdout.strip(), err=proc.stderr.strip())

    return _run
