from __future__ import annotations

from dataclasses import dataclass, field

from sim.entities import Entity
from sim.input import InputState
from sim.vec import DIR_VECTORS, Vec


@dataclass(slots=True)
class PlayerSim(Entity):
    index: int = 0
    team: int = 1
    position: int = 2  # 0 GK, 1 DEF, 2 MID, 3 ATT
    stats: dict = field(default_factory=dict)
    home: Vec = field(default_factory=lambda: Vec(0, 0))
    falling_ticks: int = 0
    sliding_ticks: int = 0
    knock_vel: Vec = field(default_factory=lambda: Vec(0, 0))


def speed_of(p: PlayerSim, physics: dict) -> int:
    # REF Player.cs (e.g. sub_E982/sub_EA62_CalcOpcodesTypeAndVelocityC):
    # velocity starts at player_base_speed and gains +1 for each of
    # SpeedMaxForVelocity4/5/6 (140/170/200) the player's spd stat exceeds,
    # topping out at base+3. The velocity table itself (Match.cs
    # GetVelocityXYFromDir) maps each velocity index directly to that many
    # terrain units/tick per axis -- confirmed by extracting the table from
    # the original disk image, not a guess.
    speed = physics["player_base_speed"]
    for threshold in physics["player_speed_tier_thresholds"]:
        if p.stats["spd"] > threshold:
            speed += 1
    return speed


def apply_movement(p: PlayerSim, inp: InputState, physics: dict) -> None:
    if p.falling_ticks > 0:
        p.falling_ticks -= 1
        p.vel = p.knock_vel
        return
    if p.sliding_ticks > 0:
        p.sliding_ticks -= 1
        step = DIR_VECTORS[p.dir]
        s = physics["tackle_knockback_speed_sliding"]
        p.vel = Vec(step.x * s, step.y * s)
        return
    if inp.dir is None:
        p.vel = Vec(0, 0)
        return
    p.dir = inp.dir
    s = speed_of(p, physics)
    step = DIR_VECTORS[inp.dir]
    p.vel = Vec(step.x * s, step.y * s)
