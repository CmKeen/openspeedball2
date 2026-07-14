from pathlib import Path

from tools.frame_trace import compare_traces, generate_trace, prepare_ref_run, write_trace


def test_generate_trace_is_deterministic():
    trace_a = generate_trace("free-ball-chase", ticks=20, seed=(17, 23))
    trace_b = generate_trace("free-ball-chase", ticks=20, seed=(17, 23))

    assert trace_a == trace_b


def test_compare_traces_accepts_identical_files(tmp_path: Path):
    trace = generate_trace("goalie-lane", ticks=10, seed=(1, 2))
    expected = tmp_path / "expected.jsonl"
    actual = tmp_path / "actual.jsonl"

    write_trace(expected, "goalie-lane", trace, (1, 2))
    write_trace(actual, "goalie-lane", trace, (1, 2))

    assert compare_traces(expected, actual) == []


def test_prepare_ref_run_writes_metadata_and_trace(tmp_path: Path):
    ref_exe = tmp_path / "Speedball 2.exe"
    ref_exe.write_text("placeholder", encoding="utf-8")

    scenario_path, trace_path = prepare_ref_run(
        tmp_path / "out",
        "ai-smoke",
        ticks=12,
        seed=(3, 4),
        ref_exe=ref_exe,
    )

    assert scenario_path.exists()
    assert trace_path.exists()