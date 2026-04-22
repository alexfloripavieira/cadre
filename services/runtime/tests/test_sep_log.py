from cadre import SEPLogger


def test_write_creates_log_file(tmp_path):
    logger = SEPLogger(tmp_path / "logs")
    logger.write("run-a", {"phase": "execute", "agent_role": "tester", "outcome": "success"})
    assert logger.log_path("run-a").exists()


def test_write_and_read_roundtrip(tmp_path):
    logger = SEPLogger(tmp_path / "logs")
    logger.write("run-b", {"phase": "plan", "agent_role": "orchestrator", "outcome": "success"})
    logger.write("run-b", {"phase": "execute", "agent_role": "tester", "outcome": "success"})

    entries = logger.read("run-b")
    assert len(entries) == 2
    assert entries[0]["phase"] == "plan"
    assert entries[1]["phase"] == "execute"
    assert all(e["run_id"] == "run-b" for e in entries)
    assert all("timestamp" in e for e in entries)


def test_read_missing_run_returns_empty(tmp_path):
    logger = SEPLogger(tmp_path / "logs")
    assert logger.read("missing-run") == []


def test_write_preserves_field_order_in_output(tmp_path):
    logger = SEPLogger(tmp_path / "logs")
    logger.write("run-c", {"phase": "decide", "agent_role": "orchestrator", "outcome": "success"})
    text = logger.log_path("run-c").read_text()
    assert text.startswith("---\n")
    assert "phase: decide" in text
