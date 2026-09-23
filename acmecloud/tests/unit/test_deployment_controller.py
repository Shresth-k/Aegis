"""Unit tests for Docker Compose deployment control."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from simulator.scenarios.deployment import (
    DeploymentCommandError,
    DeploymentControllerError,
    DeploymentVersionNotFoundError,
    DockerComposeDeploymentController,
)


def _controller(
    tmp_path: Path,
    runner,
) -> DockerComposeDeploymentController:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}")
    deployments_root = tmp_path / "deployments"
    deployment_dir = deployments_root / "checkout-service"
    deployment_dir.mkdir(parents=True)
    (deployment_dir / "2.4.0.env").write_text(
        "CHECKOUT_VERSION=2.4.0\nSERVICE_VERSION=2.4.0\n"
    )

    return DockerComposeDeploymentController(
        compose_file=compose_file,
        deployments_root=deployments_root,
        project_root=tmp_path,
        runner=runner,
    )


def test_deployment_file_resolves_versioned_file(tmp_path: Path) -> None:
    controller = _controller(tmp_path, _successful_runner)

    result = controller.deployment_file("checkout-service", "2.4.0")

    assert result == (
        tmp_path / "deployments" / "checkout-service" / "2.4.0.env"
    )


def test_deployment_file_rejects_missing_version(tmp_path: Path) -> None:
    controller = _controller(tmp_path, _successful_runner)

    with pytest.raises(DeploymentVersionNotFoundError):
        controller.deployment_file("checkout-service", "9.9.9")


@pytest.mark.parametrize(
    ("service", "version"),
    [("", "2.4.0"), ("checkout-service", "")],
)
def test_deployment_file_rejects_missing_arguments(
    tmp_path: Path,
    service: str,
    version: str,
) -> None:
    controller = _controller(tmp_path, _successful_runner)

    with pytest.raises(DeploymentControllerError):
        controller.deployment_file(service, version)


def test_deploy_sets_checkout_version_without_compose_env_file(
    tmp_path: Path,
) -> None:
    calls: list[tuple[tuple[str, ...], Path, dict[str, str]]] = []

    def runner(command, *, cwd, env):
        calls.append((tuple(command), cwd, dict(env)))
        return subprocess.CompletedProcess(command, 0, "", "")

    controller = _controller(tmp_path, runner)

    result = controller.deploy("checkout-service", "2.4.0")

    assert result.service == "checkout-service"
    assert result.version == "2.4.0"
    assert "--env-file" not in calls[0][0]
    assert calls[0][0] == (
        "docker",
        "compose",
        "-f",
        str(tmp_path / "docker-compose.yml"),
        "up",
        "-d",
        "--force-recreate",
        "checkout-service",
    )
    assert calls[0][1] == tmp_path
    assert calls[0][2]["CHECKOUT_VERSION"] == "2.4.0"


def test_deploy_preserves_existing_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_USER", "acmecloud")
    captured: dict[str, str] = {}

    def runner(command, *, cwd, env):
        captured.update(env)
        return subprocess.CompletedProcess(command, 0, "", "")

    controller = _controller(tmp_path, runner)

    controller.deploy("checkout-service", "2.4.0")

    assert captured["POSTGRES_USER"] == "acmecloud"
    assert captured["CHECKOUT_VERSION"] == "2.4.0"


def test_deploy_raises_when_compose_fails(tmp_path: Path) -> None:
    def runner(command, *, cwd, env):
        return subprocess.CompletedProcess(
            command,
            1,
            "compose stdout",
            "compose stderr",
        )

    controller = _controller(tmp_path, runner)

    with pytest.raises(
        DeploymentCommandError,
        match="Docker Compose deployment failed",
    ):
        controller.deploy("checkout-service", "2.4.0")


def test_deploy_wraps_runner_os_error(tmp_path: Path) -> None:
    def runner(command, *, cwd, env):
        raise OSError("docker not found")

    controller = _controller(tmp_path, runner)

    with pytest.raises(
        DeploymentCommandError,
        match="Unable to execute Docker Compose",
    ):
        controller.deploy("checkout-service", "2.4.0")


def test_deploy_requires_compose_file(tmp_path: Path) -> None:
    deployments_root = tmp_path / "deployments"
    deployment_dir = deployments_root / "checkout-service"
    deployment_dir.mkdir(parents=True)
    (deployment_dir / "2.4.0.env").write_text(
        "CHECKOUT_VERSION=2.4.0\nSERVICE_VERSION=2.4.0\n"
    )

    controller = DockerComposeDeploymentController(
        compose_file=tmp_path / "missing-compose.yml",
        deployments_root=deployments_root,
        project_root=tmp_path,
        runner=_successful_runner,
    )

    with pytest.raises(DeploymentControllerError, match="does not exist"):
        controller.deploy("checkout-service", "2.4.0")


def _successful_runner(command, *, cwd, env):
    return subprocess.CompletedProcess(command, 0, "", "")
