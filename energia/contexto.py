"""Contexto global elegido en la barra lateral, compartido por todas las pestañas."""
from dataclasses import dataclass

import pandas as pd


@dataclass
class Contexto:
    edificios_activos: pd.DataFrame
    edificios_todos: pd.DataFrame
    codigo: str | None
    edificio: pd.Series | None
    anio: int
    mes: int
