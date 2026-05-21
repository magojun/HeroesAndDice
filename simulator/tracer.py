"""
Game tracer (G3) — captura una partida turno-a-turno para alimentar
el replay viewer del frontend.

Uso:
    tracer = GameTracer(team_a, team_b, policy_a, policy_b, seed=42,
                        name_a="Alpha", name_b="Beta")
    replay = tracer.run()           # dict serializable a JSON

El tracer NO modifica el engine; envuelve Game y, después de cada
execute_turn, lee los observables agregados al TurnContext en G3
(assignments, defense_dice, defense_blocked, damage_dealt).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

from engine.models import Team
from engine.turn_engine import TurnEngine, PlayerPolicy, TurnContext


@dataclass
class TurnTrace:
    n: int
    attacker: str
    green_dice: list[int]
    red_die: int
    assignments: list[dict]
    damage_total: int
    defense_dice: list[int]
    defense_blocked: int
    damage_dealt: int
    statuses_applied: list[str]
    state_after: dict


@dataclass
class GameReplay:
    game_id: str
    team_a: str
    team_b: str
    seed: int
    turns: list[TurnTrace] = field(default_factory=list)
    winner: Optional[str] = None
    total_turns: int = 0
    is_draw: bool = False

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "team_a": self.team_a,
            "team_b": self.team_b,
            "seed": self.seed,
            "winner": self.winner,
            "total_turns": self.total_turns,
            "is_draw": self.is_draw,
            "turns": [
                {
                    "n": t.n,
                    "attacker": t.attacker,
                    "dice": {"green": t.green_dice, "red": t.red_die},
                    "assignments": t.assignments,
                    "damage_total": t.damage_total,
                    "defense_dice": t.defense_dice,
                    "defense_blocked": t.defense_blocked,
                    "damage_dealt": t.damage_dealt,
                    "statuses_applied": t.statuses_applied,
                    "state_after": t.state_after,
                }
                for t in self.turns
            ],
        }


class GameTracer:
    """Wrapper de Game que registra cada turno como TurnTrace."""

    MAX_TURNS = 200  # mismo límite que engine.game.Game

    def __init__(
        self,
        team_a: Team,
        team_b: Team,
        policy_a: PlayerPolicy,
        policy_b: PlayerPolicy,
        seed: int,
        name_a: str = "Team A",
        name_b: str = "Team B",
        game_id: Optional[str] = None,
    ):
        self.team_a = copy.deepcopy(team_a)
        self.team_b = copy.deepcopy(team_b)
        self.policy_a = policy_a
        self.policy_b = policy_b
        self.seed = seed
        self.name_a = name_a
        self.name_b = name_b
        self.game_id = game_id or f"{name_a}-vs-{name_b}-seed{seed}"

    def run(self) -> GameReplay:
        import random
        random.seed(self.seed)

        engine = TurnEngine()
        replay = GameReplay(
            game_id=self.game_id,
            team_a=self.name_a,
            team_b=self.name_b,
            seed=self.seed,
        )

        for turn in range(1, self.MAX_TURNS + 1):
            # --- turno de team_a ---
            ctx_a = engine.execute_turn(self.team_a, self.team_b, self.policy_a, turn)
            replay.turns.append(self._snapshot(ctx_a, turn, self.name_a))
            if self._check_end(replay, turn):
                return replay

            # --- turno de team_b ---
            ctx_b = engine.execute_turn(self.team_b, self.team_a, self.policy_b, turn)
            replay.turns.append(self._snapshot(ctx_b, turn, self.name_b))
            if self._check_end(replay, turn):
                return replay

        # Tope de turnos: resolver por recursos
        self._resolve_by_resources(replay, self.MAX_TURNS)
        return replay

    # ------------------------------------------------------------------
    # Snapshot de un turno
    # ------------------------------------------------------------------

    def _snapshot(self, ctx: TurnContext, n: int, attacker_name: str) -> TurnTrace:
        # Separar dados en verdes / rojo (única)
        green = [d.get_number() for d in ctx.dice if not d.is_special_type()]
        reds  = [d.get_number() for d in ctx.dice if d.is_special_type()]
        red = reds[0] if reds else 0

        assignments = [
            {"ability": name, "hero": hero_idx, "dice_used":
                [ctx.dice[i].get_number() for i in indices]}
            for (name, hero_idx, indices) in ctx.assignments
        ]
        statuses_applied = [s.effect.value for s in ctx.statuses_applied]

        return TurnTrace(
            n=n,
            attacker=attacker_name,
            green_dice=green,
            red_die=red,
            assignments=assignments,
            damage_total=ctx.total_damage,
            defense_dice=list(ctx.defense_dice),
            defense_blocked=ctx.defense_blocked,
            damage_dealt=ctx.damage_dealt,
            statuses_applied=statuses_applied,
            state_after=self._state_snapshot(),
        )

    def _state_snapshot(self) -> dict:
        return {
            "team_a": self._team_state(self.team_a),
            "team_b": self._team_state(self.team_b),
        }

    def _team_state(self, team: Team) -> dict:
        return {
            "hp": team.hp,
            "diamonds": team.diamonds,
            "shields": team.shields,
            "statuses": [s.effect.value for s in team.active_statuses],
            "items": [it.name for it in team.items_owned],
        }

    # ------------------------------------------------------------------
    # Fin de partida
    # ------------------------------------------------------------------

    def _check_end(self, replay: GameReplay, turn: int) -> bool:
        a_dead = self.team_a.is_defeated()
        b_dead = self.team_b.is_defeated()
        if not (a_dead or b_dead):
            return False

        replay.total_turns = turn
        if a_dead and b_dead:
            # Desempate por diamantes
            if self.team_a.diamonds > self.team_b.diamonds:
                replay.winner = self.name_a
            elif self.team_b.diamonds > self.team_a.diamonds:
                replay.winner = self.name_b
            else:
                replay.is_draw = True
        else:
            replay.winner = self.name_b if a_dead else self.name_a
        return True

    def _resolve_by_resources(self, replay: GameReplay, turn: int):
        replay.total_turns = turn
        if self.team_a.hp != self.team_b.hp:
            replay.winner = (
                self.name_a if self.team_a.hp > self.team_b.hp else self.name_b
            )
        elif self.team_a.diamonds > self.team_b.diamonds:
            replay.winner = self.name_a
        elif self.team_b.diamonds > self.team_a.diamonds:
            replay.winner = self.name_b
        else:
            replay.is_draw = True
