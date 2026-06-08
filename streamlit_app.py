"""K-QGMIP web UI — generate TPMs, run k-partition strategies, view results.

A single-file Streamlit application that exposes the whole pipeline without the
command line:

1. **Datos** — pick an existing TPM sample or generate a new one (0/1 or
   continuous) straight from the browser.
2. **Análisis** — choose a strategy (KGeoMIP, KQNodes, Clustering, GA/SA/Tabú,
   ExhaustiveK), ``k`` and the subsystem masks, then run it.
3. **Resultados** — the minimal partition, its δ_k loss, the marginal
   distribution table, and both the static (matplotlib) and interactive
   (Plotly) partition figures, plus the benchmark grid when present.

    uv run streamlit run streamlit_app.py

Requires the optional extras: ``uv sync --extra web`` (Streamlit + Plotly).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.controllers.manager import Manager
from src.funcs.runner import (
    STRATEGY_BUILDERS,
    STRATEGY_HELP,
    available_samples,
    load_tpm,
    parse_net_label,
    run_analysis,
)
from src.models.base.application import application
from src.viz import plot_kpartition_interactive, plot_loss_vs_k_interactive

PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"
RESULTS_CSV = PROJECT_ROOT / "data" / "results" / "benchmark_results_FINAL.csv"

st.set_page_config(page_title="K-QGMIP", page_icon="🧠", layout="wide")
application.disable_profiling()


# ---------------------------------------------------------------------------
# Sidebar — data source (existing sample or freshly generated TPM)
# ---------------------------------------------------------------------------

def _sidebar_data() -> tuple[str, str] | None:
    """Render the data-source controls; return ``(state, page)`` or ``None``."""
    st.sidebar.header("1 · Datos (TPM)")
    mode = st.sidebar.radio(
        "Origen de la red", ["Muestra existente", "Generar nueva"], index=0
    )

    if mode == "Generar nueva":
        n = st.sidebar.slider("Nodos (n)", 2, 25, 4)
        continuous = st.sidebar.checkbox("Probabilidades continuas", value=False)
        seed = st.sidebar.number_input("Semilla NumPy", value=application.numpy_seed, step=1)
        if st.sidebar.button("Generar TPM", width="stretch"):
            application.numpy_seed = int(seed)
            with st.spinner(f"Generando N{n}…"):
                filename = Manager("1" * n, base_path=SAMPLES_DIR).generate_network(
                    n, deterministic=not continuous, assume_yes=True
                )
            st.sidebar.success(f"Creada: {filename}")

    samples = available_samples(SAMPLES_DIR)
    if not samples:
        st.sidebar.warning("No hay muestras en data/samples/. Genera una arriba.")
        return None

    label = st.sidebar.selectbox("Red a analizar", samples, index=0)
    n, page, state = parse_net_label(label)
    st.sidebar.caption(f"n = {n} nodos · estado inicial = {state}")
    return state, page


# ---------------------------------------------------------------------------
# Sidebar — strategy / parameters
# ---------------------------------------------------------------------------

def _sidebar_strategy(n: int) -> dict:
    """Render strategy/parameter controls and return them as a dict."""
    st.sidebar.header("2 · Estrategia")
    strategy = st.sidebar.selectbox("Estrategia", list(STRATEGY_BUILDERS))
    st.sidebar.caption(STRATEGY_HELP[strategy])

    max_k = min(5, 2 * n)  # k cannot exceed the number of atoms (2n)
    k = st.sidebar.slider("k (bloques)", 2, max(2, max_k), min(3, max(2, max_k)))
    method = "spectral"
    if strategy == "Clustering":
        method = st.sidebar.selectbox("Método de clustering", ["spectral", "kmeans"])
    if strategy == "ExhaustiveK" and n > 6:
        st.sidebar.warning("ExhaustiveK sólo es práctico para n ≤ 6.")

    with st.sidebar.expander("Subsistema (avanzado)"):
        full = "1" * n
        condition = st.text_input("Condición de fondo", value=full)
        purview = st.text_input("Purview (futuro)", value=full)
        mechanism = st.text_input("Mecanismo (presente)", value=full)

    return {
        "strategy": strategy, "k": k, "method": method,
        "condition": condition, "purview": purview, "mechanism": mechanism,
    }


# ---------------------------------------------------------------------------
# Results panel
# ---------------------------------------------------------------------------

def _distribution_table(result) -> pd.DataFrame:
    """Build a small table of the reconstructed marginal distribution."""
    dist = result.solution.partition_distribution
    return pd.DataFrame(
        {"estado": list(range(len(dist))), "probabilidad": [float(x) for x in dist]}
    )


def _show_results(result) -> None:
    """Render loss, partition text, distribution and figures for a result."""
    col1, col2, col3 = st.columns(3)
    col1.metric("δ_k (pérdida)", f"{result.solution.loss:.6f}")
    col2.metric("Estrategia", result.strategy)
    col3.metric("Tiempo (s)", f"{result.solution.execution_time:.4f}")

    st.subheader("Partición de mínima información")
    st.code(result.solution.partition, language="text")

    left, right = st.columns([3, 2])
    with left:
        if result.partition is not None:
            fig = plot_kpartition_interactive(
                result.partition,
                f"{result.strategy} — k={result.k} (δ_k={result.solution.loss:.4f})",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Esta estrategia no expone un objeto de partición para graficar.")
    with right:
        st.caption("Distribución marginal reconstruida")
        st.dataframe(_distribution_table(result), width="stretch", height=300)


def _benchmark_panel() -> None:
    """Show the interactive δ_k-vs-k grid if a benchmark CSV exists."""
    if not RESULTS_CSV.exists():
        return
    st.divider()
    st.subheader("Rejilla de experimentación (benchmark)")
    df = pd.read_csv(RESULTS_CSV)
    nets = [n for n in df["network"].dropna().unique()
            if not df[(df["network"] == n) & df["loss"].notna()].empty]
    if not nets:
        return
    net = st.selectbox("Red", nets)
    st.plotly_chart(plot_loss_vs_k_interactive(df, str(net)), width="stretch")
    with st.expander("Tabla completa"):
        st.dataframe(df, width="stretch")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("🧠 K-QGMIP — Partición de Mínima Información (IIT)")
    st.caption(
        "Framework de Teoría de la Información Integrada: encuentra la k-partición "
        "que minimiza la pérdida δ_k de un sistema binario descrito por su TPM."
    )

    data = _sidebar_data()
    if data is None:
        st.info("Genera o coloca una TPM en data/samples/ para empezar.")
        return
    state, page = data
    params = _sidebar_strategy(len(state))

    if st.sidebar.button("▶ Ejecutar análisis", type="primary", width="stretch"):
        try:
            tpm = load_tpm(state, page, base_path=SAMPLES_DIR)
        except FileNotFoundError as exc:
            st.error(f"No se pudo cargar la TPM: {exc}")
            return
        with st.spinner(f"Ejecutando {params['strategy']} (k={params['k']})…"):
            try:
                result = run_analysis(
                    tpm, state, params["strategy"], params["k"],
                    method=params["method"], condition=params["condition"],
                    purview=params["purview"], mechanism=params["mechanism"],
                )
            except Exception as exc:  # surface strategy errors in the UI
                st.error(f"Error durante el análisis: {type(exc).__name__}: {exc}")
                return
        st.success("Análisis completado.")
        _show_results(result)

    _benchmark_panel()


if __name__ == "__main__":
    # Bajo `streamlit run` el runtime existe → renderiza la app. Si se invoca como
    # `python streamlit_app.py` (sin runtime), se re-lanza a sí mismo con Streamlit
    # para que ese comando también funcione.
    from streamlit.runtime import exists as _st_runtime_exists

    if _st_runtime_exists():
        main()
    else:
        from streamlit.web import cli as stcli

        sys.argv = ["streamlit", "run", __file__, *sys.argv[1:]]
        sys.exit(stcli.main())
