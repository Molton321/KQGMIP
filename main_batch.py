"""
Batch processing of subsystems from an Excel file (GeoMIP mode).

Reads subsystems from sheet 8, column B of the input Excel, runs GeometricSIA
for each one with a 1-hour timeout, and stores the results in an output Excel.

Environment variables:
  IIT_INPUT_XLSX   → path to the input Excel  (default: data/results/Pruebas_Metodo2.xlsx)
  IIT_OUTPUT_XLSX  → path to the output Excel  (default: data/results/resultados.xlsx)
  IIT_ESTADO_INI   → initial state in bits     (auto-detected from data/samples/)
  IIT_SAMPLES_DIR  → samples directory         (default: data/samples/)
"""

import multiprocessing
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA

PROJECT_ROOT = Path(__file__).resolve().parent


def _to_binary(text: str, n_bits: int) -> str:
    """Convert labels like 'AC|abc' to a binary string of length n_bits."""
    positions = "ABCDEFGHIJKLMNOPQRST"[:n_bits]
    result = ["0"] * n_bits
    for letter in text.upper():
        if letter in positions:
            result[positions.index(letter)] = "1"
    return "".join(result)


def _infer_initial_state(samples_dir: Path) -> str:
    """Pick the initial state from the largest available dataset."""
    pattern = re.compile(r"N(\d+)[A-Z]\.csv$")
    sizes = [
        int(m.group(1))
        for f in samples_dir.glob("N*.csv")
        if (m := pattern.match(f.name))
    ]
    if not sizes:
        raise FileNotFoundError(f"No hay archivos TPM en {samples_dir}")
    n = max(sizes)
    return "1" + "0" * (n - 1)


def _worker(condition, purview, mechanism, tpm, initial_state, queue):
    try:
        analyzer = GeometricSIA(tpm, initial_state)
        solution = analyzer.apply_strategy(condition, purview, mechanism)
        queue.put({
            "partition": solution.partition,
            "loss": str(solution.loss).replace(".", ","),
            "time": str(solution.execution_time).replace(".", ","),
        })
    except Exception as e:
        queue.put({"partition": None, "loss": None, "time": None, "error": str(e)})


def run_from_excel(
    input_path: Path,
    output_path: Path,
    start: int = 0,
    count: int = 50,
    initial_state: str | None = None,
    fixed_conditions: str | None = None,
) -> None:
    df = pd.read_excel(input_path, sheet_name=8, usecols="B", skiprows=3, names=["Subsistema"])
    rows = df["Subsistema"].dropna().tolist()[start: start + count]

    manager = Manager(initial_state or "")
    samples_dir = manager.base_path
    initial_state = initial_state or _infer_initial_state(samples_dir)
    fixed_conditions = fixed_conditions or ("1" * len(initial_state))
    n_bits = len(initial_state)

    tpm_path = samples_dir / f"N{n_bits}A.csv"
    if not tpm_path.exists():
        raise FileNotFoundError(f"TPM no encontrada: {tpm_path}")
    tpm = np.genfromtxt(tpm_path, delimiter=",")

    results = []
    for i, row in enumerate(rows, start=start + 1):
        parts = str(row).split("|")
        if len(parts) != 2:
            continue

        purview = _to_binary(parts[0].rstrip(), n_bits)
        mechanism = _to_binary(parts[1].rstrip(), n_bits)
        print(f"Iteración {i} — Alcance: {purview}, Mecanismo: {mechanism}")

        queue: multiprocessing.Queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=_worker,
            args=(fixed_conditions, purview, mechanism, tpm, initial_state, queue),
        )
        process.start()
        process.join(timeout=3600)

        if process.is_alive():
            print(f"  Iteración {i}: timeout alcanzado.")
            process.terminate()
            process.join()
            result = {"partition": None, "loss": None, "time": None}
        else:
            result = queue.get() if not queue.empty() else {"partition": None, "loss": None, "time": None}

        results.append({
            "Iteración": i,
            "Alcance": purview,
            "Mecanismo": mechanism,
            "Partición": result.get("partition"),
            "Pérdida (φ)": result.get("loss"),
            "Tiempo (s)": result.get("time"),
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_excel(output_path, index=False)
    print(f"Resultados guardados en {output_path}")


def run():
    input_path = Path(os.getenv("IIT_INPUT_XLSX", str(PROJECT_ROOT / "data" / "results" / "Pruebas_Metodo2.xlsx")))
    output_path = Path(os.getenv("IIT_OUTPUT_XLSX", str(PROJECT_ROOT / "data" / "results" / "resultados.xlsx")))
    initial_state = os.getenv("IIT_ESTADO_INI")
    run_from_excel(input_path, output_path, initial_state=initial_state)
