#!/usr/bin/env bash
# run.sh — Lanzar la app GeoMIP con el entorno correcto
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$REPO_DIR/GeoMIP/src/Method2_Dynamic_Programming_Reformulation/.venv"
PYTHON="$VENV/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: No se encontró el venv en $VENV"
    echo "Ejecuta primero: cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation && uv sync"
    exit 1
fi

# Instalar dependencias de la app si no están
echo "Verificando dependencias de la app..."
$PYTHON -c "import streamlit" 2>/dev/null || $PYTHON -m pip install streamlit plotly openpyxl --quiet
$PYTHON -c "import plotly"    2>/dev/null || $PYTHON -m pip install plotly --quiet

echo "Iniciando GeoMIP Streamlit..."
cd "$SCRIPT_DIR"
"$VENV/bin/streamlit" run streamlit_app.py
