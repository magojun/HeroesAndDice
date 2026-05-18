from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class Skill:
    nombre: str
    tipo: str
    costo: Optional[str]
    efecto: Optional[str]
    confirmar: bool = False


@dataclass
class Passive:
    nombre: str
    tipo: str
    efecto: Optional[str]
    confirmar: bool = False


@dataclass
class Hero:
    id: str
    set: str
    nombre: str
    titulo: str
    raza: str
    vida: int
    escudo: int
    lore: str
    destrezas: list[Passive] = field(default_factory=list)
    habilidades: list[Skill] = field(default_factory=list)


@dataclass
class Beast:
    id: str
    set: str
    nombre: str
    costo_caza: Optional[str]
    recompensa: dict[str, Any]
    confirmar: bool = False


@dataclass
class MagicObject:
    id: str
    set: str
    nombre: str
    uso: str
    mazo: Optional[str]
    costo_diamantes: Optional[Any]
    efecto: Optional[str]
    confirmar: bool = False
