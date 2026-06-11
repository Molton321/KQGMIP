"""
Manager controller for loading and generating TPMs.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from src.constants.base import (ABC_START, COLON_DELIM, CSV_EXTENSION,
                                PATH_SAMPLES)
from src.models.base.application import application


@dataclass
class Manager:
    """
    Load TPMs from data/samples/ and generate sample networks.
    """

    initial_state: str
    base_path: Path = field(default=PATH_SAMPLES)

    @property
    def page(self) -> str:
        return application.sample_network_page

    @property
    def tpm_filename(self) -> Path:
        return self.base_path / f"N{len(self.initial_state)}{self.page}.{CSV_EXTENSION}"

    def load_network(self) -> np.ndarray:
        """
        Load the TPM file matching the current state and page.

        Deterministic 0/1 TPMs are returned as uint8 (4x less resident
        memory at large n); continuous TPMs keep float32. Consumers doing
        arithmetic must cast to float first (System builds float32 cubes).
        """
        if not self.tpm_filename.exists():
            raise FileNotFoundError(
                f"TPM no encontrada: {self.tpm_filename}\nColoca el archivo en {PATH_SAMPLES}/"
            )

        tpm = np.loadtxt(self.tpm_filename, delimiter=COLON_DELIM, dtype=np.float32)
        if ((tpm == 0) | (tpm == 1)).all():
            return tpm.astype(np.uint8)
        return tpm

    def generate_network(
        self, dimensions: int, deterministic: bool = True, assume_yes: bool = False
    ) -> str:
        """
        Generate a random network (TPM) and store it in data/samples/.
        """
        np.random.seed(application.numpy_seed)

        if dimensions < 1:
            raise ValueError("Las dimensiones deben ser positivas")

        num_states = 1 << dimensions
        bytes_per_value = 1 if deterministic else 8
        total_gb = (num_states * dimensions * bytes_per_value) / (1024**3)
        print(f"Tamaño estimado: {total_gb:.6f} GB")

        if total_gb > 1 and not assume_yes:
            if (
                input("El sistema ocupará más de 1 GB. ¿Continuar? (s/n): ").lower()
                != "s"
            ):
                return ""

        self.base_path.mkdir(parents=True, exist_ok=True)

        suffix = ABC_START
        while (self.base_path / f"N{dimensions}{suffix}.{CSV_EXTENSION}").exists():
            if (
                not assume_yes
                and input(
                    f"Ya existe N{dimensions}{suffix}.{CSV_EXTENSION}. ¿Generar nueva red? (s/n): "
                ).lower()
                != "s"
            ):
                return f"N{dimensions}{suffix}.{CSV_EXTENSION}"
            if suffix == "Z":
                raise RuntimeError(f"No hay sufijos disponibles para N{dimensions}.")
            suffix = chr(ord(suffix) + 1)

        filename = f"N{dimensions}{suffix}.{CSV_EXTENSION}"
        filepath = self.base_path / filename

        states = (
            np.random.randint(2, size=(num_states, dimensions), dtype=np.int8)
            if deterministic
            else np.random.random(size=(num_states, dimensions))
        )

        t0 = time.time()
        np.savetxt(
            filepath,
            states,
            delimiter=COLON_DELIM,
            fmt="%d" if deterministic else "%.6f",
        )
        print(f"Guardado en {filepath} ({time.time() - t0:.2f}s)")

        return filename
