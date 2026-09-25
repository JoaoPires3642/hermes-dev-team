"""Kiro CLI ACP provider profile.

Makes `kiro-cli acp` the "model" behind a Hermes profile: every agent turn runs inside a
Kiro session driven over stdio (ACP / JSON-RPC). Same shape as the in-tree
``plugins/model-providers/copilot-acp`` — the ACP client itself is generic, only the
binary, argv and marker URL change.

Per-bot Kiro agent: set ``HERMES_KIRO_ACP_ARGS="acp --agent hermes-<bot>"`` in the
profile's ``.env`` so each bot runs with its own Kiro agent (prompt + tool permissions
from ``~/.kiro/agents/hermes-<bot>.json``).

Concurrency cap: point ``HERMES_KIRO_ACP_COMMAND`` at the ``kiro-pool`` wrapper, which
holds one of N slots (default 4) for the lifetime of the Kiro process.
"""

from typing import Any

from providers import register_provider
from providers.base import ProviderProfile


class KiroACPProfile(ProviderProfile):
    """Kiro CLI over ACP — external process, the CLI owns auth (company account)."""

    def create_client(self, **client_kwargs: Any) -> Any:
        from agent.copilot_acp_client import CopilotACPClient

        # The client only defaults to Copilot's binary/args when none are passed; the
        # resolved command/args for this profile arrive in client_kwargs.
        client_kwargs.setdefault("api_key", "kiro-acp")
        client_kwargs.setdefault("base_url", "acp://kiro")
        return CopilotACPClient(**client_kwargs)

    def fetch_models(
        self, *, api_key: str | None = None, base_url: str | None = None, timeout: float = 15.0
    ) -> list[str] | None:
        """Models advertised by a short-lived signed-in Kiro ACP session (``session/new``)."""
        from hermes_cli.auth import resolve_external_process_provider_credentials

        try:
            creds = resolve_external_process_provider_credentials(self.name)
            if not str(creds.get("base_url") or "").startswith("acp://"):
                return None
            client = self.create_client(
                api_key=creds.get("api_key"), base_url=creds.get("base_url"),
                command=creds.get("command"), args=creds.get("args"))
            return client.list_models(timeout_seconds=timeout) or None
        except Exception:
            return None


kiro_acp = KiroACPProfile(
    name="kiro-acp", aliases=("kiro", "kiro-cli"),
    display_name="Kiro CLI (ACP)",
    description="Kiro CLI via ACP — cada turno do bot é uma sessão kiro-cli",
    api_mode="chat_completions",
    env_vars=(),  # auth lives in kiro-cli (kiro-cli login)
    base_url="acp://kiro",
    auth_type="external_process",
    process_command="kiro-cli",
    process_args=("acp",),
    process_command_env_vars=("HERMES_KIRO_ACP_COMMAND", "KIRO_CLI_PATH"),
    process_args_env_var="HERMES_KIRO_ACP_ARGS",
    fallback_models=("auto",),
)

register_provider(kiro_acp)
