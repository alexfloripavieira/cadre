import pytest

from cadre.checkpoint import CheckpointStore


@pytest.fixture
def store(tmp_path):
    return CheckpointStore(tmp_path / "checkpoints.db")


def test_latest_on_empty_run_returns_none(store):
    assert store.latest("missing") is None


def test_save_and_retrieve_single_checkpoint(store):
    store.save("run-1", step_id=1, label="plan_complete", data={"agents_selected": ["pm"]})
    latest = store.latest("run-1")
    assert latest is not None
    assert latest["step_id"] == 1
    assert latest["label"] == "plan_complete"
    assert latest["data"] == {"agents_selected": ["pm"]}
    assert "created_at" in latest


def test_latest_returns_highest_step_id(store):
    store.save("run-2", step_id=1, label="plan", data={"k": 1})
    store.save("run-2", step_id=2, label="execute", data={"k": 2})
    store.save("run-2", step_id=3, label="review", data={"k": 3})
    latest = store.latest("run-2")
    assert latest["step_id"] == 3
    assert latest["label"] == "review"


def test_all_returns_checkpoints_in_step_order(store):
    store.save("run-3", step_id=3, label="third", data={})
    store.save("run-3", step_id=1, label="first", data={})
    store.save("run-3", step_id=2, label="second", data={})
    items = store.all("run-3")
    assert [c["step_id"] for c in items] == [1, 2, 3]
    assert [c["label"] for c in items] == ["first", "second", "third"]


def test_save_same_step_id_overwrites(store):
    store.save("run-4", step_id=1, label="first", data={"v": 1})
    store.save("run-4", step_id=1, label="revised", data={"v": 2})
    latest = store.latest("run-4")
    assert latest["label"] == "revised"
    assert latest["data"] == {"v": 2}
    assert len(store.all("run-4")) == 1


def test_clear_removes_all_checkpoints_for_run(store):
    store.save("run-5", step_id=1, label="x", data={})
    store.save("run-5", step_id=2, label="y", data={})
    assert store.clear("run-5") == 2
    assert store.latest("run-5") is None


def test_clear_does_not_affect_other_runs(store):
    store.save("run-a", step_id=1, label="a1", data={})
    store.save("run-b", step_id=1, label="b1", data={})
    store.clear("run-a")
    assert store.latest("run-a") is None
    assert store.latest("run-b")["label"] == "b1"


def test_data_roundtrips_nested_structures(store):
    payload = {
        "plan": {
            "steps": [
                {"step_id": 1, "agent_role": "orchestrator", "inputs": {"k": "v"}},
                {"step_id": 2, "agent_role": "pm"},
            ]
        },
        "budget_used_usd": 0.37,
        "tags": ["alpha", "beta"],
    }
    store.save("run-6", step_id=1, label="plan", data=payload)
    latest = store.latest("run-6")
    assert latest["data"] == payload


def test_store_persists_across_instances(tmp_path):
    db_path = tmp_path / "shared.db"
    store_a = CheckpointStore(db_path)
    store_a.save("run-7", step_id=1, label="persisted", data={"ok": True})

    store_b = CheckpointStore(db_path)
    latest = store_b.latest("run-7")
    assert latest["label"] == "persisted"
    assert latest["data"] == {"ok": True}
