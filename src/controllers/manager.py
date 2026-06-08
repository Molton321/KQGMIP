import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from src.constants.base import ABC_START, COLON_DELIM, CSV_EXTENSION, PATH_SAMPLES
from src.models.base.application import application


def _resolve_samples_path() -> Path:
    """Resolve the samples directory.

    Priority:
    1. ``IIT_SAMPLES_DIR`` if it exists.
    2. ``<project_root>/data/samples``.
    """
    env_value = os.getenv("IIT_SAMPLES_DIR")
    if env_value:
        env_path = Path(env_value).expanduser().resolve()
        if env_path.exists():
            return env_path

    return Path(__file__).resolve().parents[2] / PATH_SAMPLES


@dataclass
class Manager:
    """Load TPMs from data/samples/ and generate sample networks.

    The file is resolved as: data/samples/N{len(initial_state)}{page}.csv
    where *page* comes from ``application.sample_network_page``.
    """

    initial_state: str
    base_path: Path = field(default_factory=_resolve_samples_path)

    @property
    def page(self) -> str:
        return application.sample_network_page

    @property
    def tpm_filename(self) -> Path:
        return self.base_path / f"N{len(self.initial_state)}{self.page}.{CSV_EXTENSION}"

    def load_network(self) -> np.ndarray:
        """Load the TPM file matching the current state and page.

        Loaded directly as ``float32`` (not the NumPy default ``float64``): the
        n-cube tensors are float32 anyway, so this avoids a transient float64
        copy — the peak that caused the N25A out-of-memory (a float64 TPM is
        ~6.7 GB at n=25, vs ~3.35 GB in float32). The 0/1 deterministic values
        are exact in float32 and continuous values deviate < 1e-6.
        """
        if not self.tpm_filename.exists():
            raise FileNotFoundError(
                f"TPM no encontrada: {self.tpm_filename}\n"
                f"Coloca el archivo en {PATH_SAMPLES}/ o define IIT_SAMPLES_DIR."
            )
        return np.genfromtxt(self.tpm_filename, delimiter=COLON_DELIM, dtype=np.float32)

    def generate_network(
        self, dimensions: int, deterministic: bool = True, assume_yes: bool = False
    ) -> str:
        """Generate a random network (TPM) and store it in data/samples/.

        Args:
            dimensions: Number of nodes in the system.
            deterministic: True = 0/1 values, False = continuous probabilities.
            assume_yes: Non-interactive mode (for the CLI/UI). When True, the
                >1 GB confirmation is skipped and a name collision auto-advances
                to the next free suffix instead of prompting.

        Returns:
            The filename written (or an existing one if generation is declined).
        """
        np.random.seed(application.numpy_seed)

        if dimensions < 1:
            raise ValueError("Las dimensiones deben ser positivas")

        num_states = 1 << dimensions
        bytes_per_value = 1 if deterministic else 8
        total_gb = (num_states * dimensions * bytes_per_value) / (1024 ** 3)
        print(f"Tamaño estimado: {total_gb:.6f} GB")

        if total_gb > 1 and not assume_yes:
            if input("El sistema ocupará más de 1 GB. ¿Continuar? (s/n): ").lower() != "s":
                return ""

        self.base_path.mkdir(parents=True, exist_ok=True)

        suffix = ABC_START
        while (self.base_path / f"N{dimensions}{suffix}.{CSV_EXTENSION}").exists():
            if not assume_yes and input(
                f"Ya existe N{dimensions}{suffix}.{CSV_EXTENSION}. ¿Generar nueva red? (s/n): "
            ).lower() != "s":
                return f"N{dimensions}{suffix}.{CSV_EXTENSION}"
            if suffix == "Z":
                raise RuntimeError(
                    f"No hay sufijos disponibles para N{dimensions}."
                )
            suffix = chr(ord(suffix) + 1)

        filename = f"N{dimensions}{suffix}.{CSV_EXTENSION}"
        filepath = self.base_path / filename

        t0 = time.time()
        states = (
            np.random.randint(2, size=(num_states, dimensions), dtype=np.int8)
            if deterministic
            else np.random.random(size=(num_states, dimensions))
        )
        print(f"Generación en {time.time() - t0:.2f}s")

        t0 = time.time()
        np.savetxt(filepath, states, delimiter=COLON_DELIM, fmt="%d" if deterministic else "%.6f")
        print(f"Guardado en {filepath} ({time.time() - t0:.2f}s)")

        return filename
