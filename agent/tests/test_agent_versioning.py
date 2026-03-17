import pytest
from gradient.versioning import AgentVersion, VersionManager


@pytest.mark.unit
def test_register_version_returns_agent_version():
    manager = VersionManager()
    result = manager.register_version("bot", "1.0.0", {"model": "gpt-4"})
    assert isinstance(result, AgentVersion)
    assert result.version == "1.0.0"
    assert result.agent_name == "bot"
    assert result.config_hash != ""
    assert result.is_active is False


@pytest.mark.unit
def test_register_version_config_hash_deterministic():
    manager = VersionManager()
    v1 = manager.register_version("bot", "1.0.0", {"model": "gpt-4"})
    manager2 = VersionManager()
    v2 = manager2.register_version("bot", "1.0.0", {"model": "gpt-4"})
    assert v1.config_hash == v2.config_hash


@pytest.mark.unit
def test_register_duplicate_version_raises():
    manager = VersionManager()
    manager.register_version("bot", "1.0.0", {"model": "gpt-4"})
    with pytest.raises(ValueError, match="already registered"):
        manager.register_version("bot", "1.0.0", {"model": "gpt-5"})


@pytest.mark.unit
def test_activate_version_sets_active_and_deactivates_others():
    manager = VersionManager()
    manager.register_version("bot", "1.0.0", {"x": 1})
    manager.register_version("bot", "2.0.0", {"x": 2})
    result = manager.activate_version("bot", "1.0.0")
    assert result is True
    active = manager.get_active_version("bot")
    assert active is not None
    assert active.version == "1.0.0"
    manager.activate_version("bot", "2.0.0")
    active_v2 = manager.get_active_version("bot")
    assert active_v2 is not None
    assert active_v2.version == "2.0.0"
    versions = manager.list_versions("bot")
    inactive = next(v for v in versions if v.version == "1.0.0")
    assert inactive.is_active is False


@pytest.mark.unit
def test_activate_nonexistent_version_returns_false():
    manager = VersionManager()
    manager.register_version("bot", "1.0.0", {})
    assert manager.activate_version("bot", "9.9.9") is False


@pytest.mark.unit
def test_rollback_activates_previous_version():
    manager = VersionManager()
    manager.register_version("bot", "1.0.0", {"v": 1})
    manager.register_version("bot", "2.0.0", {"v": 2})
    manager.activate_version("bot", "2.0.0")
    previous = manager.rollback("bot")
    assert previous is not None
    assert previous.version == "1.0.0"
    active = manager.get_active_version("bot")
    assert active is not None
    assert active.version == "1.0.0"


@pytest.mark.unit
def test_rollback_returns_none_when_already_at_first():
    manager = VersionManager()
    manager.register_version("bot", "1.0.0", {})
    manager.activate_version("bot", "1.0.0")
    result = manager.rollback("bot")
    assert result is None


@pytest.mark.unit
def test_rollback_returns_none_when_no_active_version():
    manager = VersionManager()
    manager.register_version("bot", "1.0.0", {})
    manager.register_version("bot", "2.0.0", {})
    result = manager.rollback("bot")
    assert result is None


@pytest.mark.unit
def test_list_versions_sorted_descending():
    manager = VersionManager()
    manager.register_version("bot", "1.0.0", {"a": 1})
    manager.register_version("bot", "2.0.0", {"a": 2})
    manager.register_version("bot", "3.0.0", {"a": 3})
    versions = manager.list_versions("bot")
    assert [v.version for v in versions] == ["3.0.0", "2.0.0", "1.0.0"]


@pytest.mark.unit
def test_list_versions_returns_empty_for_unknown_agent():
    manager = VersionManager()
    assert manager.list_versions("unknown") == []


@pytest.mark.unit
def test_get_active_version_returns_none_when_none_active():
    manager = VersionManager()
    manager.register_version("bot", "1.0.0", {})
    assert manager.get_active_version("bot") is None


@pytest.mark.unit
def test_compare_versions_returns_metrics_for_both():
    manager = VersionManager()
    v1 = manager.register_version("bot", "1.0.0", {})
    v2 = manager.register_version("bot", "2.0.0", {})
    v1.metrics = {"correctness": 0.8, "latency": 1.2}
    v2.metrics = {"correctness": 0.9, "latency": 0.8}
    result = manager.compare_versions("bot", "1.0.0", "2.0.0")
    assert result["v1"]["version"] == "1.0.0"
    assert result["v2"]["version"] == "2.0.0"
    assert result["v1"]["metrics"]["correctness"] == 0.8
    assert result["v2"]["metrics"]["correctness"] == 0.9


@pytest.mark.unit
def test_compare_versions_handles_unknown_versions():
    manager = VersionManager()
    result = manager.compare_versions("bot", "1.0.0", "2.0.0")
    assert result["v1"]["metrics"] == {}
    assert result["v2"]["metrics"] == {}
