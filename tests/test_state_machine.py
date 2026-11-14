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
        result = engine.baseline("L1-需求拆解", "test", force=True)
        assert result["status"] == "baselined"
        assert result["version"] == "v001"
        manifest = engine.project.read_manifest()
        assert manifest["layer_states"]["L1-需求拆解"]["status"] == "baselined"


class TestDescend:
    def test_descend_to_next_layer(self, engine):
        engine.baseline("L1-需求拆解", "test", force=True)
        result = engine.descend("L2-参考文献与方案搜证汇总", "test")
        assert result["to_layer"] == "L2-参考文献与方案搜证汇总"
        manifest = engine.project.read_manifest()
        assert manifest["current_layer"] == "L2-参考文献与方案搜证汇总"

    def test_descend_skip_unbaselined_fails(self, engine):
        # L1 not baselined, try to skip to L3
        with pytest.raises(ValueError):
            engine.descend("L3-方案细化")

    def test_descend_upward_fails(self, engine):
        engine.baseline("L1-需求拆解", "test", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        with pytest.raises(ValueError):
            engine.descend("L1-需求拆解")


class TestAscend:
    def test_ascent_creates_new_descent(self, engine):
        engine.baseline("L1-需求拆解", "test", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "test", force=True)
        engine.descend("L3-方案细化")
        result = engine.ascend("L3-方案细化", "L1-需求拆解", "v001", "test ascent")
        assert result["new_descent"] == 2
        assert result["previous_descent"] == 1

    def test_ascent_invalidates_every_layer_below_target(self, engine):
        """Ascending to L1 means L2 must be redone: it must not stay green."""
        engine.baseline("L1-需求拆解", "test", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "test", force=True)
        engine.descend("L3-方案细化")
        engine.baseline("L3-方案细化", "test", force=True)
        engine.ascend("L3-方案细化", "L1-需求拆解", "v001", "test")

        manifest = engine.project.read_manifest()
        states = manifest["layer_states"]
        # target layer becomes the working layer again
        assert states["L1-需求拆解"]["status"] == "in_progress"
        # layers that had work are marked superseded (needs redo) ...
        for layer in ("L2-参考文献与方案搜证汇总", "L3-方案细化"):
            assert states[layer]["status"] == "superseded", layer
            assert states[layer].get("needs_redo") is True
        # ... and nothing below the target may still look done
        for layer in (
            "L2-参考文献与方案搜证汇总",
            "L3-方案细化",
            "L4-编码实现",
            "L5-测试验证",
            "L6-检视清理",
            "L7-终验",
        ):
            assert states[layer]["status"] not in ("baselined", "completed"), layer
        # baselines are kept as reference material
        assert states["L2-参考文献与方案搜证汇总"]["latest_baseline"] == "v001"

    def test_ascent_to_same_or_lower_fails(self, engine):
        engine.baseline("L1-需求拆解", "test", force=True)
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
        engine.baseline("L1-需求拆解", "test", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.require_confirmation("test", "block me")
        ok, msg, _ = engine.can_descend_to_next()
        assert not ok
        assert "unresolved" in msg.lower() or "blocking" in msg.lower()


class TestAscendRepair:
    """State written by older builds left lower layers looking completed."""

    def test_repair_invalidates_layers_below_ascent_target(self, engine):
        engine.baseline("L1-需求拆解", "t", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "t", force=True)
        engine.descend("L3-方案细化")
        engine.ascend("L3-方案细化", "L1-需求拆解", "v001", "t")

        # simulate the old (buggy) behaviour: lower layers left baselined
        manifest = engine.project.read_manifest()
        manifest["layer_states"]["L2-参考文献与方案搜证汇总"]["status"] = "baselined"
        manifest["layer_states"]["L3-方案细化"]["status"] = "baselined"
        manifest["current_layer"] = "L2-参考文献与方案搜证汇总"
        engine.project.write_manifest(manifest)

        result = engine.repair_ascend_state()
        assert "L3-方案细化" in result["repaired"]

        states = engine.project.read_manifest()["layer_states"]
        # the current layer stays in_progress; deeper layers need redo
        assert states["L2-参考文献与方案搜证汇总"]["status"] == "in_progress"
        assert states["L3-方案细化"]["status"] == "superseded"
        assert states["L3-方案细化"].get("needs_redo") is True

    def test_repair_logs_a_changelog_entry(self, engine):
        engine.baseline("L1-需求拆解", "t", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "t", force=True)
        engine.ascend("L2-参考文献与方案搜证汇总", "L1-需求拆解", "v001", "t")

        manifest = engine.project.read_manifest()
        manifest["layer_states"]["L2-参考文献与方案搜证汇总"]["status"] = "baselined"
        manifest["current_layer"] = "L1-需求拆解"
        engine.project.write_manifest(manifest)

        engine.repair_ascend_state()
        changelog = (engine.project.vinw_dir / "changelog.md").read_text(encoding="utf-8")
        assert "修复" in changelog and "失效范围" in changelog

    def test_repair_without_history_is_noop(self, engine):
        result = engine.repair_ascend_state()
        assert result["repaired"] == []


class TestStateSync:
    """manifest is the state machine; README must mirror it, never diverge."""

    def _readme_status(self, engine, layer):
        import frontmatter

        path = engine.project.get_layer_dir(layer) / "README.md"
        return frontmatter.load(path).metadata.get("status")

    def test_baseline_mirrors_status_to_readme(self, engine):
        engine.baseline("L1-需求拆解", "t", force=True)
        assert self._readme_status(engine, "L1-需求拆解") == "baselined"

    def test_descend_mirrors_status_to_readme(self, engine):
        engine.baseline("L1-需求拆解", "t", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        assert self._readme_status(engine, "L2-参考文献与方案搜证汇总") == "in_progress"

    def test_ascend_mirrors_superseded_to_readme(self, engine):
        engine.baseline("L1-需求拆解", "t", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "t", force=True)
        engine.ascend("L2-参考文献与方案搜证汇总", "L1-需求拆解", "v001", "t")

        assert self._readme_status(engine, "L1-需求拆解") == "in_progress"
        assert self._readme_status(engine, "L2-参考文献与方案搜证汇总") == "superseded"

    def test_sync_all_readmes_closes_historical_divergence(self, engine):
        import frontmatter

        engine.baseline("L1-需求拆解", "t", force=True)
        path = engine.project.get_layer_dir("L1-需求拆解") / "README.md"
        post = frontmatter.load(path)
        post.metadata["status"] = "in_progress"  # simulate an old divergence
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

        engine.sync_all_layer_readmes()
        assert self._readme_status(engine, "L1-需求拆解") == "baselined"

    def test_rebaseline_clears_supersede_markers(self, engine):
        engine.baseline("L1-需求拆解", "t", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "t", force=True)
        engine.ascend("L2-参考文献与方案搜证汇总", "L1-需求拆解", "v001", "t")
        engine.descend("L2-参考文献与方案搜证汇总")

        state = engine.project.read_manifest()["layer_states"]["L2-参考文献与方案搜证汇总"]
        assert state["status"] == "in_progress"
        assert "needs_redo" not in state
        assert "superseded_by" not in state

    def test_superseded_layer_todos_are_excluded(self, engine):
        """get_todos used to filter on the README mirror, which lagged."""
        from vinw.store.project import replace_todo_section

        readme = engine.project.read_layer_readme("L2-参考文献与方案搜证汇总")
        engine.project.write_layer_readme(
            "L2-参考文献与方案搜证汇总",
            {**readme, "todo_descent": 1},
            replace_todo_section(readme["content"], "## 当前待办\n\n- [ ] 待重做的任务"),
        )
        engine.baseline("L1-需求拆解", "t", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "t", force=True)
        engine.ascend("L2-参考文献与方案搜证汇总", "L1-需求拆解", "v001", "t")

        texts = [t["text"] for t in engine.project.get_todos()]
        assert "待重做的任务" not in texts
