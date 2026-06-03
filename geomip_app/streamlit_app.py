"""
streamlit_app.py
GeoMIP — Interfaz unificada para análisis de MIP y K-MIP
Ejecutar con: streamlit run streamlit_app.py
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# ── Rutas propias ───────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from core.loader import (
    REDES_PREDEFINIDAS,
    bits_a_string,
    cargar_tpm,
    estado_a_string,
    stirling2,
)
from core.runner import ejecutar_estrategias
from core.comparator import tabla_speedup, validar_resultados
from core.visualizer import graficar_distribucion, graficar_phi, graficar_radar, graficar_tiempo
from core.exporter import exportar_csv, exportar_excel, exportar_json

# ── Constantes UI ────────────────────────────────────────────────────────────
LETRAS = list("ABCDEFGHIJKLMNOPQRST")


# ════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="GeoMIP — Análisis de Particiones Mínimas",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🧠 GeoMIP — Análisis Unificado de Particiones Mínimas")
st.markdown(
    "Comparación de estrategias para la **Mínima Partición de Información (MIP)** "
    "sobre redes definidas por una Matriz de Probabilidad de Transición (TPM)."
)

# ════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════════════

_defaults = {
    "tpm": None,
    "tpm_nombre": None,
    "n_nodos": 0,
    "estado_bits": [],
    "condiciones": [],
    "alcance": [],
    "mecanismo": [],
    "k": 2,
    "estrategias": {
        "Geometric": True,
        "QNodes": False,
        "Phi": False,
        "Geometric_K": False,
    },
    "resultados": None,
    "ts_ejecucion": None,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _letras_nodos(n: int) -> list[str]:
    return LETRAS[:n]


def _validar_configuracion() -> list[str]:
    """Retorna lista de errores de validación (vacía si todo OK)."""
    errores = []
    if st.session_state.tpm is None:
        errores.append("Carga una TPM primero.")
    if not st.session_state.condiciones:
        errores.append("Selecciona al menos un nodo en Condiciones.")
    if not st.session_state.alcance:
        errores.append("Selecciona al menos un nodo en Alcance.")
    if not st.session_state.mecanismo:
        errores.append("Selecciona al menos un nodo en Mecanismo.")
    if len(st.session_state.estado_bits) != st.session_state.n_nodos:
        errores.append("El estado inicial no coincide con el número de nodos.")
    if not any(st.session_state.estrategias.values()):
        errores.append("Selecciona al menos una estrategia.")
    return errores


def _aplicar_ejemplo():
    """Carga configuración de ejemplo si hay TPM."""
    n = st.session_state.n_nodos
    if n == 0:
        return
    letras = _letras_nodos(n)
    st.session_state.estado_bits = [1] + [0] * (n - 1)
    st.session_state.condiciones = letras[:]
    st.session_state.alcance = letras[:]
    st.session_state.mecanismo = letras[:]


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — CARGA DE DATOS
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("📁 Carga de Datos")

    opcion = st.radio(
        "Origen de la TPM",
        ["Red predefinida", "Subir archivo"],
        horizontal=True,
    )

    if opcion == "Red predefinida":
        if REDES_PREDEFINIDAS:
            red = st.selectbox(
                "Red de prueba",
                options=list(REDES_PREDEFINIDAS.keys()),
                key="sel_red",
            )
            ruta = REDES_PREDEFINIDAS[red]
            try:
                tpm, n = cargar_tpm(ruta)
                if st.session_state.tpm_nombre != red:
                    # Reset estado si cambia la red
                    st.session_state.tpm = tpm
                    st.session_state.tpm_nombre = red
                    st.session_state.n_nodos = n
                    letras = _letras_nodos(n)
                    st.session_state.estado_bits = [1] + [0] * (n - 1)
                    st.session_state.condiciones = letras[:]
                    st.session_state.alcance = letras[:]
                    st.session_state.mecanismo = letras[:]
                st.success(f"✅ {red}  —  {n}×{n} nodos")
            except Exception as e:
                st.error(f"❌ {e}")
        else:
            st.warning("No se encontraron redes en `GeoMIP/data/samples/`")
    else:
        up = st.file_uploader("CSV o Excel", type=["csv", "xlsx"])
        if up:
            try:
                tpm, n = cargar_tpm(up)
                st.session_state.tpm = tpm
                st.session_state.tpm_nombre = up.name
                st.session_state.n_nodos = n
                letras = _letras_nodos(n)
                st.session_state.estado_bits = [1] + [0] * (n - 1)
                st.session_state.condiciones = letras[:]
                st.session_state.alcance = letras[:]
                st.session_state.mecanismo = letras[:]
                st.success(f"✅ {up.name}  —  {n}×{n} nodos")
            except Exception as e:
                st.error(f"❌ {e}")

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — CONFIGURACIÓN DEL SISTEMA
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("⚙️ Configuración del Sistema")

    n = st.session_state.n_nodos
    if n > 0:
        letras = _letras_nodos(n)

        # Estado inicial — checkboxes en fila
        st.subheader("Estado inicial")
        cols = st.columns(min(n, 10))
        estado_bits = []
        for i in range(n):
            col_idx = i % 10
            default_val = (
                bool(st.session_state.estado_bits[i])
                if i < len(st.session_state.estado_bits)
                else False
            )
            val = cols[col_idx].checkbox(letras[i], value=default_val, key=f"bit_{i}")
            estado_bits.append(int(val))
        st.session_state.estado_bits = estado_bits
        st.caption(f"Estado: {''.join(str(b) for b in estado_bits)}")

        # Condiciones
        st.subheader("Condiciones (fondo)")
        st.session_state.condiciones = st.multiselect(
            "Nodos activos como condición",
            options=letras,
            default=st.session_state.condiciones or letras,
            key="ms_cond",
        )

        # Alcance
        st.subheader("Alcance (t+1)")
        st.session_state.alcance = st.multiselect(
            "Nodos receptores",
            options=letras,
            default=st.session_state.alcance or letras,
            key="ms_alc",
        )

        # Mecanismo
        st.subheader("Mecanismo (t)")
        st.session_state.mecanismo = st.multiselect(
            "Nodos emisores",
            options=letras,
            default=st.session_state.mecanismo or letras,
            key="ms_mec",
        )
    else:
        st.info("Carga una TPM para configurar el sistema.")

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — ESTRATEGIAS Y K
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("🎛️ Parámetros")

    n = st.session_state.n_nodos
    k_max = max(2, min(5, n)) if n > 0 else 5
    st.session_state.k = st.slider("K — número de particiones", 2, k_max, st.session_state.k)
    k = st.session_state.k

    if n > 0:
        n_alc = st.session_state.alcance.__len__()
        n_mec = st.session_state.mecanismo.__len__()
        if n_alc > 0 and n_mec > 0:
            est_part = stirling2(n_alc, k) * stirling2(n_mec, k)
            st.caption(f"~{est_part:,} particiones estimadas (K={k})")

    st.subheader("Estrategias")
    st.session_state.estrategias["Geometric"] = st.checkbox(
        "Geometric (recomendada)", value=st.session_state.estrategias["Geometric"]
    )
    st.session_state.estrategias["QNodes"] = st.checkbox(
        "QNodes (baseline)", value=st.session_state.estrategias["QNodes"]
    )
    st.session_state.estrategias["Phi"] = st.checkbox(
        "Phi / PyPhi (referencia, lenta)", value=st.session_state.estrategias["Phi"]
    )
    if k >= 3:
        st.session_state.estrategias["Geometric_K"] = st.checkbox(
            f"Geometric K={k} (K-particiones)", value=st.session_state.estrategias.get("Geometric_K", False)
        )

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — CONTROLES
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.divider()
    c1, c2 = st.columns(2)

    ejecutar = c1.button("▶️ Ejecutar", type="primary", use_container_width=True)
    limpiar = c2.button("🗑️ Limpiar", use_container_width=True)
    ejemplo_btn = st.button("📋 Cargar ejemplo", use_container_width=True)

    if ejemplo_btn:
        _aplicar_ejemplo()
        st.rerun()

    if limpiar:
        st.session_state.resultados = None
        st.rerun()

    if ejecutar:
        errores = _validar_configuracion()
        if errores:
            for e in errores:
                st.error(f"⚠️ {e}")
        else:
            letras = _letras_nodos(st.session_state.n_nodos)
            cond_str = bits_a_string(st.session_state.condiciones, letras)
            alc_str = bits_a_string(st.session_state.alcance, letras)
            mec_str = bits_a_string(st.session_state.mecanismo, letras)
            ei_str = estado_a_string(st.session_state.estado_bits)

            with st.spinner("Ejecutando análisis…"):
                st.session_state.resultados = ejecutar_estrategias(
                    tpm=st.session_state.tpm,
                    estado_inicial_str=ei_str,
                    condicion_str=cond_str,
                    alcance_str=alc_str,
                    mecanismo_str=mec_str,
                    k=st.session_state.k,
                    estrategias=st.session_state.estrategias,
                )
                st.session_state.ts_ejecucion = time.time()
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# ÁREA PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

if st.session_state.resultados is None:
    # Estado inicial — descripción del flujo
    st.info("👈 Configura los parámetros en el panel lateral y haz clic en **▶️ Ejecutar**.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            "### 1️⃣ Carga datos\n"
            "Selecciona una red predefinida (N3A–N15A) o sube tu propio CSV."
        )
    with col2:
        st.markdown(
            "### 2️⃣ Configura\n"
            "Define estado inicial, condiciones, alcance y mecanismo por nodo."
        )
    with col3:
        st.markdown(
            "### 3️⃣ Analiza\n"
            "Compara φ, tiempos y particiones entre las tres estrategias."
        )

    if st.session_state.n_nodos > 0:
        st.divider()
        st.subheader(f"Red cargada: {st.session_state.tpm_nombre}")
        tpm_preview = pd.DataFrame(st.session_state.tpm)
        st.dataframe(tpm_preview.style.format("{:.3f}"), use_container_width=True, height=200)

else:
    # ── TABS ─────────────────────────────────────────────────────────────────
    tab_res, tab_graf, tab_anal, tab_exp = st.tabs(
        ["📊 Resultados", "📈 Gráficos", "🔍 Análisis", "💾 Exportar"]
    )

    resultados = st.session_state.resultados

    # ── TAB 1: RESULTADOS ─────────────────────────────────────────────────────
    with tab_res:
        st.subheader("Tabla de Resultados")

        rows = []
        for nombre, v in resultados.items():
            if "error" in v:
                rows.append({"Estrategia": nombre, "φ": "ERROR", "Tiempo (s)": "—",
                              "Evaluaciones": "—", "Partición": v["error"][:80]})
            else:
                rows.append({
                    "Estrategia": nombre,
                    "φ": round(v["phi"], 6),
                    "Tiempo (s)": round(v["tiempo"], 4),
                    "Evaluaciones": v.get("evaluaciones") or "N/A",
                    "Partición": str(v.get("particion", ""))[:80],
                })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        # Resumen rápido
        exitosos = {k: v for k, v in resultados.items() if v.get("phi") is not None}
        if exitosos:
            mejor = min(exitosos, key=lambda k: exitosos[k]["phi"])
            phi_opt = exitosos[mejor]["phi"]
            st.success(f"**φ mínimo:** `{phi_opt:.6f}` — encontrado por **{mejor}**")

            # Partición óptima formateada
            with st.expander("Ver partición óptima completa"):
                st.code(str(exitosos[mejor].get("particion", "N/A")), language=None)

        # Advertencias de consistencia rápidas
        if len(exitosos) >= 2:
            phis = [v["phi"] for v in exitosos.values()]
            diff = max(phis) - min(phis)
            if diff > 0.001:
                st.warning(f"⚠️ φ difiere entre estrategias (Δ={diff:.4f}) — posible bug.")
            else:
                st.success(f"✅ φ consistente entre estrategias (Δ={diff:.6f})")

    # ── TAB 2: GRÁFICOS ───────────────────────────────────────────────────────
    with tab_graf:
        if not exitosos:
            st.warning("No hay resultados exitosos para graficar.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(graficar_phi(resultados), use_container_width=True)
            with c2:
                st.plotly_chart(graficar_tiempo(resultados), use_container_width=True)

            if len(exitosos) >= 2:
                st.plotly_chart(graficar_radar(resultados), use_container_width=True)

    # ── TAB 3: ANÁLISIS ───────────────────────────────────────────────────────
    with tab_anal:
        st.subheader("Validaciones de Consistencia")
        validaciones = validar_resultados(resultados)
        for nombre_v, res_v in validaciones.items():
            if res_v["ok"]:
                st.success(f"✅ **{nombre_v}:** {res_v['msg']}")
            else:
                st.warning(f"⚠️ **{nombre_v}:** {res_v['msg']}")

        st.divider()
        st.subheader("Tabla de Speedup")
        rows_sp = tabla_speedup(resultados)
        if rows_sp:
            st.dataframe(pd.DataFrame(rows_sp), use_container_width=True)

        st.divider()
        st.subheader("Configuración usada")
        letras = _letras_nodos(st.session_state.n_nodos)
        st.json({
            "red": st.session_state.tpm_nombre,
            "n_nodos": st.session_state.n_nodos,
            "estado_inicial": estado_a_string(st.session_state.estado_bits),
            "condiciones": "".join(st.session_state.condiciones),
            "alcance": "".join(st.session_state.alcance),
            "mecanismo": "".join(st.session_state.mecanismo),
            "k": st.session_state.k,
        })

    # ── TAB 4: EXPORTAR ───────────────────────────────────────────────────────
    with tab_exp:
        st.subheader("Descargar Resultados")
        config_export = {
            "tpm_nombre": st.session_state.tpm_nombre,
            "k": st.session_state.k,
            "estado_inicial": estado_a_string(st.session_state.estado_bits),
            "condiciones": "".join(st.session_state.condiciones),
            "alcance": "".join(st.session_state.alcance),
            "mecanismo": "".join(st.session_state.mecanismo),
            "timestamp": st.session_state.ts_ejecucion,
        }

        c1, c2, c3 = st.columns(3)
        with c1:
            try:
                xlsx = exportar_excel(resultados, config_export)
                st.download_button(
                    "📥 Excel (.xlsx)",
                    data=xlsx,
                    file_name="geomip_resultados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Excel: {e}")

        with c2:
            csv_data = exportar_csv(resultados)
            st.download_button(
                "📥 CSV (.csv)",
                data=csv_data,
                file_name="geomip_resultados.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with c3:
            json_data = exportar_json(resultados)
            st.download_button(
                "📥 JSON (.json)",
                data=json_data,
                file_name="geomip_resultados.json",
                mime="application/json",
                use_container_width=True,
            )

# ════════════════════════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown(
    "<small>**GeoMIP** — Teoría Integrada de Información (IIT) · "
    "Estrategias: Phi (PyPhi) · QNodes · Geometric · K-particiones</small>",
    unsafe_allow_html=True,
)
