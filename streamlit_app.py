"""K-QGMIP web UI — generate TPMs, run k-partition strategies, view results.
This Streamlit app provides an interactive interface for the k-partition framework,
allowing users to generate or select TPMs, choose strategies and parameters,
and visualize the results. It also includes a batch runner for the official evaluation
grid and a benchmark viewer for δ_k vs k when a results CSV is present.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from streamlit.runtime import exists as _st_runtime_exists
from streamlit.web import cli as stcli

from src.constants.base import BENCHMARK_CSV, PATH_RESULTS, PATH_SAMPLES, STRATEGY_TIMEOUT
from src.constants.grid import GRID_RESULTS_XLSX
from src.controllers.manager import Manager
from src.funcs.grid import fill_grid, format_results_text, grid_sheet_names, read_grid_results
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


class StreamlitApp:
    """Web front-end for the k-partition framework (Strategy pipeline + viz)."""

    _EXHAUSTIVE_MAX_N = 6
    _GEOMETRIC_SOFT_CEILING = 15
    _CLUSTERING_HARD_CEILING = 25

    _THEME = {
        "accent": "#7C4DFF",
        "accent_dark": "#4A2FB8",
        "card_bg": "rgba(124, 92, 255, 0.10)",
        "card_border": "rgba(124, 92, 255, 0.28)",
    }

    _STRATEGY_FAMILY_COLOR = {
        "KGeoMIP": "#7C4DFF",
        "KQNodes": "#7C4DFF",
        "Clustering": "#1AAE9F",
        "Genetic": "#E8821A",
        "Annealing": "#E8821A",
        "Tabu": "#E8821A",
        "ExhaustiveK": "#2B9E58",
    }

    def __init__(self) -> None:
        st.set_page_config(page_title="K-QGMIP", page_icon="🧠", layout="wide")
        self._init_session_state()
        self._import_core()

    def _init_session_state(self) -> None:
        """Seed the per-session keys the callbacks read and write."""
        st.session_state.setdefault("result", None)
        st.session_state.setdefault("error", None)
        st.session_state.setdefault("tpm_loaded", None)
        st.session_state.setdefault("params", None)

    def _import_core(self) -> None:
        """Wire the headless pipeline onto the instance."""
        self._manager_cls = Manager
        self._strategy_builders = STRATEGY_BUILDERS
        self._strategy_help = STRATEGY_HELP
        self._available_samples = available_samples
        self._load_tpm = load_tpm
        self._parse_net_label = parse_net_label
        self._strategy_runner = run_analysis
        self._application = application
        self._plot_kpartition = plot_kpartition_interactive
        self._plot_loss_k = plot_loss_vs_k_interactive
        self._application.disable_profiling()

    def run(self) -> None:
        """Render the whole page: theme, header, sidebar, results, benchmark."""
        self._inject_theme()
        self._render_header()
        has_tpm = self._render_sidebar()
        if st.sidebar.button("▶ Ejecutar análisis", type="primary", width="stretch"):
            self._execute_strategy()
        if not has_tpm and st.session_state.result is None:
            st.info(
                "Genera o selecciona una TPM en data/samples/ (panel izquierdo) "
                "para empezar el análisis."
            )
        self._render_results()
        self._render_official_grid()
        self._render_benchmark()

    def _inject_theme(self) -> None:
        """Inject the CSS polish layer on top of the config.toml theme.
        Streamlit's official theming covers colors/radius via config.toml; the
        gradient header banner and the accented metric cards need a small CSS
        layer, which is the common community pattern for finer styling.
        """
        t = self._THEME
        st.markdown(
            f"""
            <style>
              .kqgmip-header {{
                  background: linear-gradient(110deg, {t["accent"]} 0%, {t["accent_dark"]} 100%);
                  color: #FFFFFF;
                  padding: 1.1rem 1.4rem;
                  border-radius: 0.8rem;
                  margin-bottom: 0.4rem;
              }}
              .kqgmip-header h1 {{ color: #FFFFFF; margin: 0; font-size: 1.7rem; }}
              .kqgmip-header p {{ color: #EDE7FF; margin: 0.3rem 0 0 0; font-size: 0.95rem; }}
              div[data-testid="stMetric"] {{
                  background: {t["card_bg"]};
                  border: 1px solid {t["card_border"]};
                  border-left: 4px solid {t["accent"]};
                  border-radius: 0.6rem;
                  padding: 0.7rem 0.9rem;
              }}
              .kqgmip-badge {{
                  display: inline-block;
                  padding: 0.18rem 0.7rem;
                  border-radius: 999px;
                  color: #FFFFFF;
                  font-size: 0.82rem;
                  font-weight: 600;
              }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    def _render_header(self) -> None:
        """Render the branded gradient header banner."""
        st.markdown(
            """
            <div class="kqgmip-header">
              <h1>🧠 K-QGMIP — Partición de Mínima Información (IIT)</h1>
              <p>Teoría de la Información Integrada: encuentra la k-partición que
              minimiza la pérdida δ_k de un sistema binario descrito por su TPM.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _render_sidebar(self) -> bool:
        """Render the data + strategy controls; return whether a TPM is ready."""
        st.sidebar.header("1 · Datos (TPM)")
        mode = st.sidebar.radio(
            "Origen de la red", ["Muestra existente", "Generar nueva"], index=0
        )
        self._handle_tpm_generation(mode)
        samples = self._available_samples(PATH_SAMPLES)
        if not samples:
            st.sidebar.warning("No hay muestras en data/samples/. Genera una arriba.")
            st.session_state.tpm_loaded = None
            return False
        label = st.sidebar.selectbox("Red a analizar", samples, index=0)
        n, page, default_state = self._parse_net_label(label)
        state = self._render_initial_state(n, default_state)
        st.sidebar.caption(f"n = {n} nodos · página {page}")
        st.session_state.tpm_loaded = (state, page)
        self._render_strategy_section(n)
        return True

    def _render_initial_state(self, n: int, default_state: str) -> str:
        """Render the initial state input and return the validated value."""
        state = st.sidebar.text_input(
            "Estado inicial",
            value=default_state,
            help="Cadena binaria de n dígitos que condiciona el análisis.",
        )
        if len(state) != n or any(char not in "01" for char in state):
            st.sidebar.error(
                f"El estado debe ser {n} dígitos binarios; usando {default_state}."
            )
            return default_state
        return state

    def _handle_tpm_generation(self, mode: str) -> None:
        """Render the 'generate a new TPM' controls when that mode is selected."""
        if mode != "Generar nueva":
            return
        n = st.sidebar.slider("Nodos (n)", 2, 25, 4)
        continuous = st.sidebar.checkbox("Probabilidades continuas", value=False)
        seed = st.sidebar.number_input(
            "Semilla NumPy", value=self._application.numpy_seed, step=1
        )
        if st.sidebar.button("Generar TPM", width="stretch"):
            self._application.numpy_seed = int(seed)
            with st.spinner(f"Generando N{n}…"):
                filename = self._manager_cls(
                    "1" * n, base_path=PATH_SAMPLES
                ).generate_network(n, deterministic=not continuous, assume_yes=True)
            st.sidebar.success(f"Creada: {filename}")

    def _render_strategy_section(self, n: int) -> None:
        """Render the strategy selection and parameter controls."""
        st.sidebar.header("2 · Estrategia")
        strategy = st.sidebar.selectbox("Estrategia", list(self._strategy_builders))
        st.sidebar.caption(self._strategy_help[strategy])
        max_k = min(5, 2 * n)
        default_k = min(3, max(2, max_k))
        k = st.sidebar.slider("k (bloques)", 2, max(2, max_k), default_k)
        method = "spectral"
        if strategy == "Clustering":
            method = st.sidebar.selectbox("Método", ["spectral", "kmeans"])
        self._render_strategy_warning(strategy, n)
        masks = self._render_advanced_masks(n)
        st.session_state.params = {
            "strategy": strategy,
            "k": k,
            "method": method,
            **masks,
        }

    def _render_strategy_warning(self, strategy: str, n: int) -> None:
        """Warn when the chosen strategy is impractical for the network size."""
        if strategy == "ExhaustiveK" and n > self._EXHAUSTIVE_MAX_N:
            st.sidebar.warning(
                f"ExhaustiveK es impracticable para n > {self._EXHAUSTIVE_MAX_N}."
            )
        elif strategy in ("KGeoMIP", "KQNodes") and n > self._GEOMETRIC_SOFT_CEILING:
            st.sidebar.warning(
                f"KGeoMIP/KQNodes pueden superar los {STRATEGY_TIMEOUT}s para n > "
                f"{self._GEOMETRIC_SOFT_CEILING}. Considere Clustering."
            )
        elif strategy == "Clustering" and n > self._CLUSTERING_HARD_CEILING:
            st.sidebar.warning(
                f"Clustering puede proponer partición pero no puntuar δ_k para "
                f"n > {self._CLUSTERING_HARD_CEILING}."
            )

    def _render_advanced_masks(self, n: int) -> dict[str, str]:
        """Render the subsystem masks and return them, defaulting to all-active.

        The inputs are intentionally keyless: each carries value="1" * n so
        that selecting a different-sized network re-derives the default to the new
        length, instead of persisting a stale mask that would mismatch the state.
        """
        with st.sidebar.expander("Subsistema (avanzado)"):
            full = "1" * n
            return {
                "condition": st.text_input("Condición de fondo", value=full),
                "purview": st.text_input("Purview (futuro)", value=full),
                "mechanism": st.text_input("Mecanismo (presente)", value=full),
            }

    def _execute_strategy(self) -> None:
        """Load the selected TPM and run the chosen strategy, storing the result."""
        data = st.session_state.tpm_loaded
        if data is None:
            st.session_state.error = (
                "No hay TPM cargada. Genera o selecciona una muestra."
            )
            return
        state, page = data
        params = st.session_state.params
        try:
            tpm = self._load_tpm(state, page, base_path=PATH_SAMPLES)
        except FileNotFoundError as exc:
            st.session_state.error = f"No se pudo cargar la TPM: {exc}"
            return
        full = "1" * len(state)
        masks = {
            "condition": params.get("condition") or full,
            "purview": params.get("purview") or full,
            "mechanism": params.get("mechanism") or full,
        }
        with st.spinner(f"Ejecutando {params['strategy']} (k={params['k']})…"):
            try:
                st.session_state.result = self._strategy_runner(
                    tpm,
                    state,
                    params["strategy"],
                    params["k"],
                    method=params["method"],
                    **masks,
                )
                st.session_state.error = None
            except Exception as exc:
                st.session_state.error = f"{type(exc).__name__}: {exc}"
                st.session_state.result = None

    def _render_results(self) -> None:
        """Render the error banner and/or the latest analysis result."""
        if st.session_state.error:
            st.error(st.session_state.error)
        if st.session_state.result is None:
            return
        st.success("Análisis completado.")
        result = st.session_state.result
        self._show_metrics(result)
        self._show_partition(result)
        self._show_distribution(result)

    def _strategy_badge(self, strategy: str) -> str:
        """Build the colored per-family badge HTML for a strategy name."""
        color = self._STRATEGY_FAMILY_COLOR.get(strategy, self._THEME["accent"])
        return (
            f'<span class="kqgmip-badge" style="background:{color}">{strategy}</span>'
        )

    def _show_metrics(self, result: Any) -> None:
        """Render the headline metrics (loss, strategy badge, runtime)."""
        st.markdown(self._strategy_badge(result.strategy), unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("δ_k (pérdida)", f"{result.solution.loss:.6f}")
        col2.metric("Estrategia", result.strategy)
        col3.metric("Tiempo (s)", f"{result.solution.execution_time:.4f}")

    def _show_partition(self, result: Any) -> None:
        """Render the partition text plus its interactive figure + distribution."""
        st.subheader("Partición de mínima información")
        st.code(result.solution.partition, language="text")
        if result.partition is None:
            st.info("Esta estrategia no expone un objeto de partición para graficar.")
            return
        left, right = st.columns([3, 2])
        with left:
            fig = self._plot_kpartition(
                result.partition,
                f"{result.strategy} — k={result.k} (δ_k={result.solution.loss:.4f})",
            )
            st.plotly_chart(fig, width="stretch")
        with right:
            st.caption("Distribución marginal reconstruida")
            st.dataframe(
                self._build_distribution_table(result), width="stretch", height=300
            )

    def _build_distribution_table(self, result: Any) -> pd.DataFrame:
        """Build the reconstructed-marginal table for the partition distribution."""
        dist = result.solution.partition_distribution
        return pd.DataFrame(
            {
                "estado": list(range(len(dist))),
                "probabilidad": [float(x) for x in dist],
            }
        )

    def _show_distribution(self, result: Any) -> None:
        """Render the original subsystem marginal distribution table."""
        dist = result.solution.subsystem_distribution
        st.subheader("Distribución marginal del subsistema")
        st.dataframe(
            pd.DataFrame(
                {
                    "nodo": list(range(len(dist))),
                    "probabilidad": [float(x) for x in dist],
                }
            ),
            width="stretch",
        )

    def _standard_workbooks(self) -> list[Path]:
        """Workbooks in data/results/ whose sheets actually parse as the standard
        format (anchors included), not just by sheet name."""
        from src.funcs.grid import read_grid_sheet

        found = []
        for path in sorted(PATH_RESULTS.glob("*.xlsx")):
            try:
                names = grid_sheet_names(path)
                if names:
                    read_grid_sheet(path, names[0])
                    found.append(path)
            except Exception:
                continue
        return found

    def _render_official_grid(self) -> None:
        """Batch runner + results viewer over any standard workbook (CLI parity)."""
        st.divider()
        st.subheader("Tabla de evaluación (.xlsx)")
        st.caption(
            "Cualquier workbook con hojas *-Elementos (formato estándar). "
            "Equivalentes de consola: uv run exec.py batch · uv run exec.py resultados."
        )

        uploaded = st.file_uploader(
            "Subir un .xlsx con el formato estándar", type="xlsx"
        )
        if uploaded is not None:
            destination = PATH_RESULTS / uploaded.name
            destination.write_bytes(uploaded.getvalue())
            st.success(f"Guardado en {destination}")

        workbooks = self._standard_workbooks()
        if not workbooks:
            st.info(
                "No hay workbooks con el formato estándar en data/results/. "
                "Sube uno arriba para empezar."
            )
            return
        chosen_book: Path = st.selectbox(
            "Workbook", workbooks, format_func=lambda p: p.name
        )

        view_tab, fill_tab = st.tabs(["Ver resultados", "Llenar tabla"])

        with view_tab:
            rows = read_grid_results(chosen_book)
            if not rows:
                st.info(
                    "Este workbook aún no tiene resultados; llénalo en la otra pestaña."
                )
            else:
                st.code(format_results_text(rows, max_rows=16), language=None)
                with st.expander("Tabla completa (filtrable)"):
                    st.dataframe(pd.DataFrame(rows), width="stretch")
                st.download_button(
                    "Descargar .xlsx",
                    chosen_book.read_bytes(),
                    file_name=chosen_book.name,
                )

        with fill_tab:
            output_path = (
                chosen_book
                if chosen_book.name.startswith("resultados")
                else GRID_RESULTS_XLSX
            )
            st.caption(
                f"Salida: {output_path.name} — la entrada nunca se modifica y las "
                "celdas ya llenas se omiten (reanudable)."
            )
            sheets = grid_sheet_names(chosen_book)
            chosen_sheets = st.multiselect("Hojas a llenar", sheets, default=[])
            if st.button("▶ Llenar tabla", disabled=not chosen_sheets):
                log_box = st.empty()
                lines: list[str] = []

                def report(line: str) -> None:
                    """Stream per-row progress lines into the UI log box."""
                    lines.append(line)
                    log_box.code("\n".join(lines[-15:]))

                with st.spinner("Ejecutando KQNodes + KGeoMIP sobre la tabla…"):
                    fill_grid(
                        chosen_book,
                        output_path,
                        sheet_names=chosen_sheets,
                        progress=report,
                    )
                st.success(f"Tabla de resultados guardada en {output_path}")

    def _render_benchmark(self) -> None:
        """Render the δ_k-vs-k benchmark, with a network picker for (re)generation."""
        st.divider()
        st.subheader("Benchmark (δ_k vs k, todas las estrategias)")
        if not BENCHMARK_CSV.exists():
            st.info(
                "Aún no hay benchmark generado. Elige las redes y genéralo aquí, o "
                "ejecuta uv run exec.py benchmark en la terminal."
            )
            self._benchmark_generator()
            return
        df = pd.read_csv(BENCHMARK_CSV)
        valid_nets = [
            n
            for n in df["network"].dropna().unique()
            if not df[(df["network"] == n) & df["loss"].notna()].empty
        ]
        if valid_nets:
            net = st.selectbox("Red", valid_nets)
            st.plotly_chart(self._plot_loss_k(df, str(net)), width="stretch")
            with st.expander("Tabla de resultados"):
                st.dataframe(df, width="stretch")
        else:
            st.warning(
                "El CSV de benchmark existe pero no tiene filas válidas; regenéralo."
            )
        self._benchmark_generator()

    def _benchmark_generator(self) -> None:
        """Pick which sampled networks to benchmark and run them in a subprocess."""
        samples = self._available_samples(PATH_SAMPLES)
        if not samples:
            st.caption("No hay muestras en data/samples/ para generar el benchmark.")
            return
        default = [n for n in ("N10A", "N15A") if n in samples] or samples[:1]
        chosen = st.multiselect(
            "Redes a incluir en el benchmark",
            samples,
            default=default,
            help="Selecciona una o varias redes de data/samples/.",
        )
        if st.button("Generar/Regenerar benchmark") and chosen:
            with st.spinner(
                f"Corriendo todas las estrategias sobre {', '.join(chosen)}…"
            ):
                subprocess.run(
                    [sys.executable, "scripts/run_benchmark.py", "--nets", *chosen],
                    check=False,
                )
            st.rerun()


def main() -> None:
    """Render the app (called once the Streamlit runtime exists)."""
    StreamlitApp().run()


if __name__ == "__main__":
    if _st_runtime_exists():
        main()
    else:
        sys.argv = ["streamlit", "run", __file__, *sys.argv[1:]]
        sys.exit(stcli.main())
