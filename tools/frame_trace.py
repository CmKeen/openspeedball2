from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from sim.ai import compute_ai_inputs
from sim.config import load_config
from sim.input import InputState
from sim.match import Match, player_id
from sim.vec import Vec


CFG = load_config(Path(__file__).resolve().parent.parent / "data")
DEFAULT_REF_EXE = Path("Speedball 2 - WIP 02") / "bin" / "Speedball 2.exe"


@dataclass(frozen=True)
class Scenario:
    name: str
    ticks: int

    def setup(self, match: Match) -> None:
        if self.name == "ai-smoke":
            return
        if self.name == "free-ball-chase":
            match.ball.held_by = None
            match.ball.pos = Vec(300, 700)
            match.ball.vel = Vec(20, 0)
            return
        if self.name == "goalie-lane":
            match.ball.held_by = None
            match.ball.pos = Vec(320, 900)
            match.ball.vel = Vec(20, 60)
            return
        raise ValueError(f"Unknown scenario: {self.name}")


SCENARIOS = {
    "ai-smoke": Scenario("ai-smoke", 300),
    "free-ball-chase": Scenario("free-ball-chase", 120),
    "goalie-lane": Scenario("goalie-lane", 120),
}


def _serialize_input(inp: InputState) -> dict[str, int | bool | None]:
    return {"dir": inp.dir, "action_a": inp.action_a, "action_b": inp.action_b}


def _serialize_frame(match: Match, ai_inputs: dict[int, InputState]) -> dict:
    return {
        "tick": match.tick_count,
        "state_hash": match.state_hash(),
        "score": [match.score.score_team1, match.score.score_team2],
        "clock_ticks": match.clock_ticks,
        "rng": [match.rng.a, match.rng.b],
        "ball": {
            "x": match.ball.pos.x,
            "y": match.ball.pos.y,
            "vx": match.ball.vel.x,
            "vy": match.ball.vel.y,
            "bounce_timer": match.ball.bounce_timer,
            "holder": (player_id(match.ball.held_by.team, match.ball.held_by.index)
                       if match.ball.held_by is not None else None),
        },
        "players": [
            {
                "id": player_id(p.team, p.index),
                "x": p.pos.x,
                "y": p.pos.y,
                "vx": p.vel.x,
                "vy": p.vel.y,
                "dir": p.dir,
            }
            for p in match.all_players()
        ],
        "ai_inputs": {
            str(pid): _serialize_input(inp)
            for pid, inp in sorted(ai_inputs.items())
        },
    }


def generate_trace(scenario_name: str,
                   ticks: int | None = None,
                   seed: tuple[int, int] = (5, 5)) -> list[dict]:
    scenario = SCENARIOS[scenario_name]
    match = Match(CFG, seed=seed)
    scenario.setup(match)
    frames: list[dict] = []
    total_ticks = scenario.ticks if ticks is None else ticks

    for _ in range(total_ticks):
        human_inputs: dict[int, InputState] = {}
        ai_inputs = compute_ai_inputs(match, set())
        frames.append(_serialize_frame(match, ai_inputs))
        match.tick(ai_inputs | human_inputs)

    frames.append(_serialize_frame(match, compute_ai_inputs(match, set())))
    return frames


def write_trace(path: Path,
                scenario_name: str,
                frames: list[dict],
                seed: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "type": "meta",
            "scenario": scenario_name,
            "seed": list(seed),
            "frame_count": len(frames),
        }) + "\n")
        for frame in frames:
            fh.write(json.dumps(frame, sort_keys=True) + "\n")


def load_trace(path: Path) -> tuple[dict, list[dict]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"Trace file is empty: {path}")
    meta = json.loads(lines[0])
    frames = [json.loads(line) for line in lines[1:]]
    return meta, frames


def compare_traces(expected_path: Path, actual_path: Path) -> list[str]:
    expected_meta, expected_frames = load_trace(expected_path)
    actual_meta, actual_frames = load_trace(actual_path)
    diffs: list[str] = []

    if expected_meta.get("scenario") != actual_meta.get("scenario"):
        diffs.append(
            f"scenario mismatch: {expected_meta.get('scenario')} != {actual_meta.get('scenario')}"
        )
    if expected_meta.get("seed") != actual_meta.get("seed"):
        diffs.append(f"seed mismatch: {expected_meta.get('seed')} != {actual_meta.get('seed')}")
    if len(expected_frames) != len(actual_frames):
        diffs.append(f"frame count mismatch: {len(expected_frames)} != {len(actual_frames)}")

    for idx, (expected, actual) in enumerate(zip(expected_frames, actual_frames)):
        if expected != actual:
            diffs.append(
                f"first differing frame: {idx}\nexpected={json.dumps(expected, sort_keys=True)}\n"
                f"actual={json.dumps(actual, sort_keys=True)}"
            )
            break
    return diffs


def prepare_ref_run(output_dir: Path,
                    scenario_name: str,
                    ticks: int | None,
                    seed: tuple[int, int],
                    ref_exe: Path) -> tuple[Path, Path]:
    if not ref_exe.exists():
        raise FileNotFoundError(f"REF executable not found: {ref_exe}")

    frames = generate_trace(scenario_name, ticks=ticks, seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "sim_trace.jsonl"
    scenario_path = output_dir / "scenario.json"
    write_trace(trace_path, scenario_name, frames, seed)
    scenario_path.write_text(json.dumps({
        "scenario": scenario_name,
        "seed": list(seed),
        "ticks": ticks if ticks is not None else SCENARIOS[scenario_name].ticks,
        "ref_exe": str(ref_exe),
        "expected_ref_trace": str(output_dir / "ref_trace.jsonl"),
    }, indent=2), encoding="utf-8")
    return scenario_path, trace_path


def _parse_seed(text: str) -> tuple[int, int]:
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("seed must be 'a,b'")
    return int(parts[0]), int(parts[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic frame trace harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    trace_parser = sub.add_parser("trace-sim", help="write a sim trace JSONL file")
    trace_parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="ai-smoke")
    trace_parser.add_argument("--ticks", type=int)
    trace_parser.add_argument("--seed", type=_parse_seed, default=(5, 5))
    trace_parser.add_argument("--output", type=Path, required=True)

    compare_parser = sub.add_parser("compare", help="compare two trace JSONL files")
    compare_parser.add_argument("expected", type=Path)
    compare_parser.add_argument("actual", type=Path)

    prepare_parser = sub.add_parser("prepare-ref", help="stage a scenario for REF validation")
    prepare_parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="ai-smoke")
    prepare_parser.add_argument("--ticks", type=int)
    prepare_parser.add_argument("--seed", type=_parse_seed, default=(5, 5))
    prepare_parser.add_argument("--output-dir", type=Path, required=True)
    prepare_parser.add_argument("--ref-exe", type=Path, default=DEFAULT_REF_EXE)

    args = parser.parse_args(argv)

    if args.cmd == "trace-sim":
        frames = generate_trace(args.scenario, ticks=args.ticks, seed=args.seed)
        write_trace(args.output, args.scenario, frames, args.seed)
        print(f"wrote {len(frames)} frames to {args.output}")
        return 0

    if args.cmd == "compare":
        diffs = compare_traces(args.expected, args.actual)
        if diffs:
            for diff in diffs:
                print(diff)
            return 1
        print("traces match")
        return 0

    scenario_path, trace_path = prepare_ref_run(
        args.output_dir,
        args.scenario,
        ticks=args.ticks,
        seed=args.seed,
        ref_exe=args.ref_exe,
    )
    print(f"prepared REF validation in {args.output_dir}")
    print(f"scenario metadata: {scenario_path}")
    print(f"sim trace: {trace_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())