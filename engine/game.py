"""
Motor de partida completa (B7).

Alterna turnos entre team_a y team_b hasta que uno quede a 0 vidas.
Desempate: más diamantes. Si hay empate exacto, la partida es nula.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine.models import Team
from engine.turn_engine import TurnEngine, PlayerPolicy


@dataclass
class GameResult:
    winner: Optional[Team]          # None si es empate
    loser: Optional[Team]           # None si es empate
    is_draw: bool
    turns: int
    team_a_hp_remaining: int
    team_b_hp_remaining: int
    team_a_diamonds: int
    team_b_diamonds: int


class Game:
    """Orquesta una partida completa entre dos equipos con sus políticas."""

    MAX_TURNS = 200  # límite de seguridad para evitar partidas infinitas

    def __init__(
        self,
        team_a: Team,
        team_b: Team,
        policy_a: PlayerPolicy,
        policy_b: PlayerPolicy,
        seed: Optional[int] = None,
    ):
        self.team_a = team_a
        self.team_b = team_b
        self.policy_a = policy_a
        self.policy_b = policy_b
        if seed is not None:
            import random
            random.seed(seed)
        self._engine = TurnEngine()

    def run(self) -> GameResult:
        for turn in range(1, self.MAX_TURNS + 1):
            # Turno de team_a
            self._engine.execute_turn(self.team_a, self.team_b, self.policy_a, turn)
            result = self._check_end(turn)
            if result:
                return result

            # Turno de team_b
            self._engine.execute_turn(self.team_b, self.team_a, self.policy_b, turn)
            result = self._check_end(turn)
            if result:
                return result

        # Límite de turnos alcanzado: resolver por HP y luego por diamantes
        return self._resolve_by_resources(self.MAX_TURNS)

    # ------------------------------------------------------------------
    # Lógica de condición de fin (B7)
    # ------------------------------------------------------------------

    def _check_end(self, turns: int) -> Optional[GameResult]:
        a_dead = self.team_a.is_defeated()
        b_dead = self.team_b.is_defeated()

        if not a_dead and not b_dead:
            return None

        if a_dead and b_dead:
            return self._tiebreak(turns)

        winner = self.team_b if a_dead else self.team_a
        loser = self.team_a if a_dead else self.team_b
        return self._build_result(winner, loser, turns, draw=False)

    def _tiebreak(self, turns: int) -> GameResult:
        """Ambos equipos llegan a 0 simultáneamente: más diamantes gana."""
        if self.team_a.diamonds > self.team_b.diamonds:
            return self._build_result(self.team_a, self.team_b, turns, draw=False)
        if self.team_b.diamonds > self.team_a.diamonds:
            return self._build_result(self.team_b, self.team_a, turns, draw=False)
        return self._build_result(None, None, turns, draw=True)

    def _resolve_by_resources(self, turns: int) -> GameResult:
        """Tiempo agotado: gana quien tenga más HP, luego más diamantes."""
        if self.team_a.hp != self.team_b.hp:
            winner = self.team_a if self.team_a.hp > self.team_b.hp else self.team_b
            loser = self.team_b if winner is self.team_a else self.team_a
            return self._build_result(winner, loser, turns, draw=False)
        return self._tiebreak(turns)

    def _build_result(
        self,
        winner: Optional[Team],
        loser: Optional[Team],
        turns: int,
        draw: bool,
    ) -> GameResult:
        return GameResult(
            winner=winner,
            loser=loser,
            is_draw=draw,
            turns=turns,
            team_a_hp_remaining=self.team_a.hp,
            team_b_hp_remaining=self.team_b.hp,
            team_a_diamonds=self.team_a.diamonds,
            team_b_diamonds=self.team_b.diamonds,
        )
