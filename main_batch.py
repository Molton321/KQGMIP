"""
Batch processing of subsystems from Excel.

Supports ALL strategies (k-partition + legacy k=2).
Reads subsystems from the Excel file, runs the chosen strategy for each,
and stores results in an output Excel.

Environment variables:
  IIT_INPUT_XLSX   → path to the input Excel  (default: data/results/Pruebas_Metodo2.xlsx)
  IIT_OUTPUT_XLSX  → path to the output Excel  (default: data/results/resultados.xlsx)
  IIT_STRATEGY     → strategy name (default: kgeomip)
  IIT_K            → partition count (default: 3)
  IIT_ESTADO_INI   → initial state in bits     (auto-detected from data/samples/)
  IIT_SAMPLES_DIR  → samples directory         (default: data/samples/)

Usage:
    uv run exec.py --batch                          # default: KGeoMIP(k=3) on N10A
    uv run exec.py --batch --strategy kqnodes --k 4
    uv run main_batch.py                            # same, direct
"""

import multiprocessing
import os
import re
from pathlib import Path

import pandas as pd

from src.controllers.manager import Manager
from src.models.base.application import application

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
    sizes = [int(m.group(1)) for f in samples_dir.glob("N*.csv") if (m := pattern.match(f.name))]
    if not sizes:
        raise FileNotFoundError(f"No hay archivos TPM en {samples_dir}")
    n = max(sizes)
    return "1" + "0" * (n - 1)


def _worker(condition, purview, mechanism, tpm, initial_state, strategy_name, k, method, queue):
    """Worker process for batch evaluation of one subsystem.

    The strategy is built through the single registry (``src/funcs/runner.py``)
    and the result (or error) is pushed onto ``queue`` for the parent process.
    """
    from src.funcs.runner import build_strategy

    try:
        analyzer = build_strategy(strategy_name, tpm, initial_state, k, method)
        solution = analyzer.apply_strategy(condition, purview, mechanism)
        queue.put(
            {
                "partition": solution.partition,
                "loss": str(solution.loss).replace(".", ","),
                "time": str(solution.execution_time).replace(".", ","),
                "error": None,
            }
        )
    except Exception as e:
        queue.put(
            {
                "partition": None,
                "loss": None,
                "time": None,
                "error": str(e),
            }
        )


def run_from_excel(
    input_path: Path,
    output_path: Path,
    strategy_name: str = "kgeomip",
    k: int = 3,
    method: str = "spectral",
    start: int = 0,
    count: int = 50,
    initial_state: str | None = None,
    fixed_conditions: str | None = None,
) -> None:
    """Run a strategy over the subsystems listed in an Excel file.

    The TPM is loaded through ``Manager.load_network`` (the single source of
    truth: float32, no duplicate ``genfromtxt``) using page ``"A"``.
    """
    df = pd.read_excel(input_path, sheet_name=8, usecols="B", skiprows=3, names=["Subsistema"])
    rows = df["Subsistema"].dropna().tolist()[start : start + count]

    samples_dir = Manager(initial_state or "").base_path
    initial_state = initial_state or _infer_initial_state(samples_dir)
    fixed_conditions = fixed_conditions or ("1" * len(initial_state))
    n_bits = len(initial_state)

    application.set_sample_network_page("A")
    manager = Manager(initial_state)
    if not manager.tpm_filename.exists():
        raise FileNotFoundError(f"TPM no encontrada: {manager.tpm_filename}")
    tpm = manager.load_network()

    strategy_label = strategy_name
    if strategy_name == "clustering":
        strategy_label = f"Clustering({method})"
    elif k > 2:
        strategy_label = f"{strategy_name}(k={k})"

    results = []
    for i, row in enumerate(rows, start=start + 1):
        parts = str(row).split("|")
        if len(parts) != 2:
            continue

        purview = _to_binary(parts[0].rstrip(), n_bits)
        mechanism = _to_binary(parts[1].rstrip(), n_bits)
        print(f"[{i}] {strategy_label} — Alcance: {purview}, Mecanismo: {mechanism}")

        queue: multiprocessing.Queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=_worker,
            args=(
                fixed_conditions,
                purview,
                mechanism,
                tpm,
                initial_state,
                strategy_name,
                k,
                method,
                queue,
            ),
        )
        process.start()
        process.join(timeout=3600)

        if process.is_alive():
            print("  Timeout alcanzado.")
            process.terminate()
            process.join()
            result = {"partition": None, "loss": None, "time": None, "error": "timeout"}
        else:
            result = (
                queue.get()
                if not queue.empty()
                else {"partition": None, "loss": None, "time": None, "error": "empty queue"}
            )

        results.append(
            {
                "Iteración": i,
                "Alcance": purview,
                "Mecanismo": mechanism,
                "Estrategia": strategy_label,
                "k": k,
                "Partición": result.get("partition"),
                "Pérdida (δ_k)": result.get("loss"),
                "Tiempo (s)": result.get("time"),
                "Error": result.get("error"),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_excel(output_path, index=False)
    print(f"\nResultados guardados en {output_path}")


def run():
    """CLI entry point (reads env vars or uses defaults)."""
    input_path = Path(
        os.getenv(
            "IIT_INPUT_XLSX",
            str(PROJECT_ROOT / "data" / "results" / "Pruebas_Metodo2.xlsx"),
        )
    )
    output_path = Path(
        os.getenv(
            "IIT_OUTPUT_XLSX",
            str(PROJECT_ROOT / "data" / "results" / "resultados.xlsx"),
        )
    )
    strategy_name = os.getenv("IIT_STRATEGY", "kgeomip")
    k = int(os.getenv("IIT_K", "3"))
    method = os.getenv("IIT_METHOD", "spectral")
    initial_state = os.getenv("IIT_ESTADO_INI")

    print(f"Strategy: {strategy_name}  k={k}  method={method}")
    run_from_excel(
        input_path,
        output_path,
        strategy_name=strategy_name,
        k=k,
        method=method,
        initial_state=initial_state,
    )


if __name__ == "__main__":
    run()
