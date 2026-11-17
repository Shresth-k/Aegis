"""Deployment control for the AcmeCloud Scenario Engine.

The deployment controller selects a service version through the
CHECKOUT_VERSION process environment variable. Docker Compose continues to
load project-level variables from the normal project environment, including
the PostgreSQL credentials, while the service-level env_file selects the
requested version.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class DeploymentControllerError(RuntimeError):
    """Base error for deployment controller failures."""


class DeploymentVersionNotFoundError(DeploymentControllerError):
    """Raised when a requested service/version deployment does not exist."""


class DeploymentCommandError(DeploymentControllerError):
    """Raised when Docker Compose fails to apply a deployment."""


class CommandRunner(Protocol):
    """Protocol for executing external commands."""

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
    ) -> subprocess.CompletedProcess[str]:
        """Execute one command and return its completed process."""


@dataclass(frozen=True)
class DeploymentResult:
    """Result of one deployment operation."""

    service: str
    version: str
    deployment_file: Path


class DockerComposeDeploymentController:
    """Apply a versioned service deployment through Docker Compose."""

    def __init__(
        self,
        *,
        compose_file: Path,
        deployments_root: Path,
        project_root: Path,
        runner: CommandRunner | None = None,
    ) -> None:
        """Create a controller for one Docker Compose project."""
        self._compose_file = compose_file
        self._deployments_root = deployments_root
        self._project_root = project_root
        self._runner = runner or _run_command

    def deployment_file(self, service: str, version: str) -> Path:
        """Resolve and validate a versioned deployment environment file."""
        if not service.strip():
            raise DeploymentControllerError("service is required")

        if not version.strip():
            raise DeploymentControllerError("version is required")

        path = self._deployments_root / service / f"{version}.env"

        try:
            path.relative_to(self._deployments_root)
        except ValueError as exc:
            raise DeploymentControllerError(
                "deployment path escapes deployments root"
            ) from exc

        if not path.is_file():
            raise DeploymentVersionNotFoundError(
                f"No deployment definition for {service}:{version}: {path}"
            )

        return path

    def deploy(self, service: str, version: str) -> DeploymentResult:
        """Recreate one Compose service using the requested version."""
        deployment_file = self.deployment_file(service, version)

        if not self._compose_file.is_file():
            raise DeploymentControllerError(
                f"Docker Compose file does not exist: {self._compose_file}"
            )

        command = (
            "docker",
            "compose",
            "-f",
            str(self._compose_file),
            "up",
            "-d",
            "--force-recreate",
            service,
        )

        environment = os.environ.copy()
        environment["CHECKOUT_VERSION"] = version

        try:
            result = self._runner(
                command,
                cwd=self._project_root,
                env=environment,
            )
        except OSError as exc:
            raise DeploymentCommandError(
                f"Unable to execute Docker Compose for {service}:{version}"
            ) from exc

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise DeploymentCommandError(
                f"Docker Compose deployment failed for {service}:{version}: {detail}"
            )

        return DeploymentResult(
            service=service,
            version=version,
            deployment_file=deployment_file,
        )


def _run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run a command with captured text output."""
    return subprocess.run(
        command,
        cwd=cwd,
        env=dict(env),
        check=False,
        capture_output=True,
        text=True,
    )
