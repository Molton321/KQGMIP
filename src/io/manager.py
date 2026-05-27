import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from src.base.application import aplicacion
from src.constants.base import ABC_START, COLON_DELIM, CSV_EXTENSION, RESOLVER_PATH


def _resolver_ruta_samples() -> Path:
    """Busca el directorio de muestras en ubicaciones estándar del proyecto."""
    env = os.getenv("IIT_SAMPLES_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p

    project_root = Path(__file__).resolve().parents[2]
    candidatos = [
        project_root / "data" / "samples",
        project_root / "src" / ".samples",
    ]
    for c in candidatos:
        if c.exists():
            return c

    return project_root / "data" / "samples"


@dataclass
class Manager:
    """
    Carga TPMs desde data/samples/ y gestiona rutas de salida.

    El archivo se resuelve como: data/samples/N{len(estado_inicial)}{pagina}.csv
    donde `pagina` se toma de `aplicacion.pagina_red_muestra`.
    """

    estado_inicial: str
    ruta_base: Path = field(default_factory=_resolver_ruta_samples)

    @property
    def pagina(self) -> str:
        return aplicacion.pagina_red_muestra

    @property
    def tpm_filename(self) -> Path:
        return self.ruta_base / f"N{len(self.estado_inicial)}{self.pagina}.{CSV_EXTENSION}"

    @property
    def output_dir(self) -> Path:
        return Path(f"{RESOLVER_PATH}/N{len(self.estado_inicial)}{self.pagina}/{self.estado_inicial}")

    def preparar_directorio_salida(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def cargar_red(self) -> np.ndarray:
        if not self.tpm_filename.exists():
            raise FileNotFoundError(
                f"TPM no encontrada: {self.tpm_filename}\n"
                f"Coloca el archivo en data/samples/ o define IIT_SAMPLES_DIR."
            )
        return np.genfromtxt(self.tpm_filename, delimiter=COLON_DELIM)

    def generar_red(self, dimensiones: int, determinista: bool = True) -> str:
        """
        Genera una red aleatoria (TPM) y la guarda en data/samples/.

        Args:
            dimensiones: Número de nodos del sistema.
            determinista: True = valores 0/1, False = probabilidades continuas.
        """
        np.random.seed(aplicacion.semilla_numpy)

        if dimensiones < 1:
            raise ValueError("Las dimensiones deben ser positivas")

        num_estados = 1 << dimensiones
        total_gb = (num_estados * dimensiones) / (1024 ** 3)
        print(f"Tamaño estimado: {total_gb:.6f} GB")

        if total_gb > 1:
            if input("El sistema ocupará más de 1 GB. ¿Continuar? (s/n): ").lower() != "s":
                return ""

        self.ruta_base.mkdir(parents=True, exist_ok=True)

        suffix = ABC_START
        while (self.ruta_base / f"N{dimensiones}{suffix}.{CSV_EXTENSION}").exists():
            if input(
                f"Ya existe N{dimensiones}{suffix}.{CSV_EXTENSION}. ¿Generar nueva red? (s/n): "
            ).lower() != "s":
                return f"N{dimensiones}{suffix}.{CSV_EXTENSION}"
            suffix = chr(ord(suffix) + 1)

        filename = f"N{dimensiones}{suffix}.{CSV_EXTENSION}"
        filepath = self.ruta_base / filename

        t0 = time.time()
        states = (
            np.random.randint(2, size=(num_estados, dimensiones), dtype=np.int8)
            if determinista
            else np.random.random(size=(num_estados, dimensiones))
        )
        print(f"Generación en {time.time() - t0:.2f}s")

        t0 = time.time()
        np.savetxt(filepath, states, delimiter=COLON_DELIM, fmt="%d" if determinista else "%.6f")
        print(f"Guardado en {filepath} ({time.time() - t0:.2f}s)")

        return filename
