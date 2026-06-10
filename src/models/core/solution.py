"""Result container and colored console renderer for a strategy's solution."""

import re

import numpy as np
from colorama import Fore, Style, init

from src.constants.base import FLOAT_ZERO, WHITESPACE
from src.constants.tags import PYPHI_LABEL
from src.models.base.application import application

init()


class Solution:
    """
    Represents and renders the solution found by an IIT strategy.
    Contains the strategy name, the loss value ( φ ), the subsystem and
    partition distributions, the best partition found, and the execution time.
    """

    def __init__(
        self,
        strategy: str,
        loss: float,
        subsystem_distribution: np.ndarray,
        partition_distribution: np.ndarray,
        partition: str,
        total_time: float = FLOAT_ZERO,
    ) -> None:
        self.strategy = strategy
        self.loss = loss
        self.subsystem_distribution = subsystem_distribution
        self.partition_distribution = partition_distribution
        self.partition = partition
        self.execution_time = total_time

    def __str__(self) -> str:
        spacing = 64
        double_line = "═" * spacing
        triple_line = "≡" * spacing

        def fmt_dist(dist: np.ndarray) -> str:
            count = min(dist.size, spacing)
            overflow = dist.size - spacing
            suffix = f" {overflow} valores más.." if overflow > 0 else ""
            values = WHITESPACE.join(
                (
                    f"{Fore.WHITE}{dist[i]:.4f}"
                    if dist[i] > FLOAT_ZERO
                    else f"{Fore.LIGHTBLACK_EX}0.    "
                )
                for i in range(count)
            )
            return f"[ {values}{suffix} {Fore.WHITE}]"

        is_pyphi = self.strategy == PYPHI_LABEL
        dist_type = "tensorial" if is_pyphi else "marginal"

        t_hours = f"{self.execution_time / 3600:.2f}"
        t_min = f"{self.execution_time / 60:.1f}"
        t_sec = f"{self.execution_time:.4f}"

        k_match = re.search(r"k=(\d+)", self.strategy)
        k_str = f"{k_match.group(1)}-" if k_match else "Bi-"

        return (
            f"{Fore.CYAN}{double_line}\n\n"
            f"{Fore.RED}{self.strategy} fue la estrategia de solución.\n\n"
            f"{Fore.BLUE}Distancia métrica: {Fore.WHITE}{application.metric_distance}\n"
            f"{Fore.BLUE}Notación indexado: {Fore.WHITE}{application.indexing_notation}\n\n"
            f"{Fore.YELLOW}Distribución {dist_type} del Subsistema:\n"
            f"{Style.RESET_ALL}{fmt_dist(self.subsystem_distribution)}\n"
            f"{Fore.YELLOW}Distribución {dist_type} de la Partición:\n"
            f"{Style.RESET_ALL}{fmt_dist(self.partition_distribution)}\n\n"
            f"{Fore.YELLOW}Mejor {k_str}Partición:\n"
            f"{Fore.MAGENTA}{self.partition}\n"
            f"{Fore.GREEN}Pérdida mínima ( φ ) = {self.loss:.4f}\n\n"
            f"{Fore.BLUE}Tiempos de ejecución:\n"
            f"{Fore.WHITE}Horas: {t_hours} = Minutos: {t_min} = Segundos: {t_sec}\n\n"
            f"{Fore.CYAN}{triple_line}{Style.RESET_ALL}"
        )

    def __repr__(self) -> str:
        return self.__str__()
