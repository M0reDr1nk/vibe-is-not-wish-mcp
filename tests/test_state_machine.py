"""Tests for vinw.workflow.state_machine."""

import shutil
from pathlib import Path

import pytest

from vinw.store.project import Project, LAYERS
from vinw.workflow.state_machine import WorkflowEngine


@pytest.fixture
def engine(tmp_path):
    root = tmp_path / "test-proj"
    proj = Project.init(root, "test-proj", "Test")
    yield WorkflowEngine(proj)
    shutil.rmtree(root, ignore_errors=True)


class TestBaseline:
    def test_baseline_updates_state(self, engine):
        result = engine.baseline("L1-需求拆解", "test")
        assert result["status"] == "baselined"
        assert result["version"] == "v001"
        manifest = engine.project.read_manifest()
        assert manifest["layer_states"]["L1-需求拆解"]["status"] == "baselined"


class TestDescend:
    def test_descend_to_next_layer(self, engine):
        engine.baseline("L1-需求拆解", "test")
        result = engine.descend("L2-参考文献与方案搜证汇总", "test")
        assert result["to_layer"] == "L2-参考文献与方案搜证汇总"
        manifest = engine.project.read_manifest()
        assert manifest["current_layer"] == "L2-参考文献与方案搜证汇总"

    def test_descend_skip_unbaselined_fails(self, engine):
        # L1 not baselined, try to skip to L3
        with pytest.raises(ValueError):
            engine.descend("L3-方案细化")

    def test_descend_upward_fails(self, engine):
        engine.baseline("L1-需求拆解", "test")
        engine.descend("L2-参考文献与方案搜证汇总")
        with pytest.raises(ValueError):
            engine.descend("L1-需求拆解")


class TestAscend:
    def test_ascent_creates_new_descent(self, engine):
        engine.baseline("L1-需求拆解", "test")
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "test")
        engine.descend("L3-方案细化")
        result = engine.ascend("L3-方案细化", "L1-需求拆解", "v001", "test ascent")
        assert result["new_descent"] == 2
        assert result["previous_descent"] == 1

    def test_ascent_marks_lower_superseded(self, engine):
        engine.baseline("L1-需求拆解", "test")
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "test")
        engine.descend("L3-方案细化")
        engine.ascend("L3-方案细化", "L1-需求拆解", "v001", "test")
        manifest = engine.project.read_manifest()
        # from_layer (L3) and below (L4-L7) should be superseded
        assert manifest["layer_states"]["L3-方案细化"]["status"] == "superseded"
        # L2 is ABOVE L3 (not in the superseded range), remains baselined
        assert manifest["layer_states"]["L2-参考文献与方案搜证汇总"]["status"] == "baselined"

    def test_ascent_to_same_or_lower_fails(self, engine):
        engine.baseline("L1-需求拆解", "test")
        engine.descend("L2-参考文献与方案搜证汇总")
        with pytest.raises(ValueError):
            engine.ascend("L2-参考文献与方案搜证汇总", "L3-方案细化", "v001", "invalid")

    def test_ascent_nonexistent_baseline_fails(self, engine):
        engine.descend("L2-参考文献与方案搜证汇总")
        with pytest.raises(ValueError):
            engine.ascend("L2-参考文献与方案搜证汇总", "L1-需求拆解", "v999", "no baseline")


class TestConfirmations:
    def test_require_confirmation(self, engine):
        cfm_id = engine.require_confirmation("test", "test desc")
        assert cfm_id.startswith("cfm-")
        manifest = engine.project.read_manifest()
        assert len(manifest["pending_confirmations"]) == 1

    def test_resolve_confirmation(self, engine):
        cfm_id = engine.require_confirmation("test", "test desc")
        engine.resolve_confirmation(cfm_id, "approve")
        manifest = engine.project.read_manifest()
        assert manifest["pending_confirmations"][0]["resolution"] == "approve"

    def test_can_descend_with_pending_blocks(self, engine):
        engine.baseline("L1-需求拆解", "test")
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.require_confirmation("test", "block me")
        ok, msg, _ = engine.can_descend_to_next()
        assert not ok
        assert "unresolved" in msg.lower() or "blocking" in msg.lower()
