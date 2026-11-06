"""Codex acceptance reuses client authentication without exposing its secret."""

from importlib import import_module

import pytest


def overrides(config, environment):
    module = import_module("scripts.studio_mcp_e2e")
    assert hasattr(module, "codex_provider_overrides"), "client provider acceptance missing"
    return module.codex_provider_overrides(config, environment)


def test_codex_provider_secret_stays_in_child_environment_and_out_of_arguments():
    secret = "synthetic-client-provider-secret"
    environment = {}
    arguments, secrets = overrides(
        {
            "model": "gpt-6-astra",
            "model_provider": "custom",
            "model_providers": {
                "custom": {
                    "name": "User gateway",
                    "base_url": "https://gateway.example/v1",
                    "wire_api": "responses",
                    "requires_openai_auth": False,
                    "experimental_bearer_token": secret,
                }
            },
        },
        environment,
    )
    assert 'model="gpt-6-astra"' in arguments
    assert 'model_provider="custom"' in arguments
    assert "model_providers.custom.requires_openai_auth=false" in arguments
    assert any("model_providers.custom.env_key=" in item for item in arguments)
    assert secret not in " ".join(arguments)
    assert list(environment.values()) == [secret]
    assert secrets == [secret]


def test_codex_acceptance_does_not_inherit_the_host_delegation_key():
    environment = {"CODEX_API_KEY": "synthetic-host-delegation"}
    overrides(
        {
            "model_provider": "custom",
            "model_providers": {
                "custom": {
                    "experimental_bearer_token": "synthetic-user-provider",
                    "requires_openai_auth": False,
                },
            },
        },
        environment,
    )
    assert "CODEX_API_KEY" not in environment
    assert environment["FANTASY_STUDIO_CODEX_PROVIDER_TOKEN"] == "synthetic-user-provider"


def test_codex_acceptance_does_not_replay_authentication_commands():
    with pytest.raises(ValueError, match="认证"):
        overrides(
            {
                "model_provider": "custom",
                "model_providers": {
                    "custom": {"auth": {"command": "synthetic-auth-command"}},
                },
            },
            {},
        )


def test_codex_provider_environment_key_must_exist():
    config = {
        "model_provider": "custom",
        "model_providers": {
            "custom": {"env_key": "CLIENT_KEY", "requires_openai_auth": False},
        },
    }
    with pytest.raises(ValueError, match="环境变量"):
        overrides(config, {})
    _, secrets = overrides(config, {"CLIENT_KEY": "synthetic-env-key"})
    assert secrets == ["synthetic-env-key"]


@pytest.mark.parametrize(
    "url",
    [
        "https://user:synthetic-password@gateway.example/v1",
        "https://gateway.example/v1?api_key=synthetic-key",
        "https://gateway.example/v1?access_token=synthetic-token",
        "https://gateway.example/v1?client_secret=synthetic-secret",
        "https://gateway.example/v1?api_secret=synthetic-secret",
    ],
    ids=["userinfo", "api-key", "access-token", "client-secret", "api-secret"],
)
def test_codex_provider_rejects_credentials_in_urls_before_building_arguments(url):
    with pytest.raises(ValueError, match="地址"):
        overrides(
            {
                "model_provider": "custom",
                "model_providers": {
                    "custom": {"base_url": url, "requires_openai_auth": False},
                },
            },
            {},
        )
