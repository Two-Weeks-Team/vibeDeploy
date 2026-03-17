"""Agent versioning utilities for Gradient G10."""

import hashlib
import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AgentVersion(BaseModel):
    """Represents a single versioned snapshot of an agent configuration."""

    version: str
    agent_name: str
    created_at: str
    config_hash: str
    metrics: dict = Field(default_factory=dict)
    is_active: bool = False


class VersionManager:
    """In-memory manager for agent version lifecycle."""

    def __init__(self) -> None:
        self._store: dict[str, list[AgentVersion]] = {}

    def register_version(self, agent_name: str, version: str, config: dict) -> AgentVersion:
        """Create and store a new agent version.

        Raises ValueError if the version string already exists for this agent.
        """
        versions = self._store.setdefault(agent_name, [])
        if any(v.version == version for v in versions):
            raise ValueError(f"Version '{version}' already registered for agent '{agent_name}'")

        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        agent_version = AgentVersion(
            version=version,
            agent_name=agent_name,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            config_hash=config_hash,
        )
        versions.append(agent_version)
        return agent_version

    def get_active_version(self, agent_name: str) -> AgentVersion | None:
        """Return the currently active version, or None if none is active."""
        for v in self._store.get(agent_name, []):
            if v.is_active:
                return v
        return None

    def list_versions(self, agent_name: str) -> list[AgentVersion]:
        """Return all versions for an agent sorted by created_at descending."""
        return sorted(
            self._store.get(agent_name, []),
            key=lambda v: v.created_at,
            reverse=True,
        )

    def activate_version(self, agent_name: str, version: str) -> bool:
        """Set the given version as active, deactivating all others.

        Returns True if the version was found and activated, False otherwise.
        """
        versions = self._store.get(agent_name, [])
        target = next((v for v in versions if v.version == version), None)
        if target is None:
            return False
        for v in versions:
            v.is_active = v.version == version
        return True

    def rollback(self, agent_name: str) -> AgentVersion | None:
        """Activate the version that was registered immediately before the current active one.

        Returns the newly activated version, or None if rollback is not possible.
        """
        versions = self._store.get(agent_name, [])
        sorted_versions = sorted(versions, key=lambda v: v.created_at)
        active_index = next((i for i, v in enumerate(sorted_versions) if v.is_active), None)
        if active_index is None or active_index == 0:
            return None
        previous = sorted_versions[active_index - 1]
        self.activate_version(agent_name, previous.version)
        return previous

    def compare_versions(self, agent_name: str, v1: str, v2: str) -> dict:
        """Return a dict comparing the metrics of two versions side-by-side."""
        versions = {v.version: v for v in self._store.get(agent_name, [])}
        version1 = versions.get(v1)
        version2 = versions.get(v2)
        return {
            "v1": {"version": v1, "metrics": version1.metrics if version1 else {}},
            "v2": {"version": v2, "metrics": version2.metrics if version2 else {}},
        }
