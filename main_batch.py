"""
Procesamiento en lote de subsistemas desde un archivo Excel (modo GeoMIP).

Lee subsistemas de la hoja 8 columna B del Excel de entrada,
ejecuta GeometricSIA para cada uno con un timeout de 1 hora,
y guarda los resultados en un Excel de salida.

Variables de entorno:
  IIT_INPUT_XLSX   → ruta al Excel de entrada  (default: data/results/Pruebas_Metodo2.xlsx)
  IIT_OUTPUT_XLSX  → ruta al Excel de salida   (default: data/results/resultados.xlsx)
  IIT_ESTADO_INI   → estado inicial en bits     (auto-detectado desde data/samples/)
  IIT_SAMPLES_DIR  → directorio de muestras     (default: data/samples/)
"""

import multiprocessing
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.io.manager import Manager
from src.strategies.geometric import GeometricSIA

PROJECT_ROOT = Path(__file__).resolve().parent


def _convertir_a_binario(texto: str, n_bits: int) -> str:
    """Convierte etiquetas tipo 'AC|abc' a cadena binaria de longitud n_bits."""
    posiciones = "ABCDEFGHIJKLMNOPQRST"[:n_bits]
    resultado = ["0"] * n_bits
    for letra in texto.upper():
        if letra in posiciones:
            resultado[posiciones.index(letra)] = "1"
    return "".join(resultado)


def _inferir_estado_inicial(samples_dir: Path) -> str:
    """Elige el estado inicial tomando el dataset de mayor tamaño disponible."""
    patron = re.compile(r"N(\d+)[A-Z]\.csv$")
    tamaños = [
        int(m.group(1))
        for f in samples_dir.glob("N*.csv")
        if (m := patron.match(f.name))
    ]
    if not tamaños:
        raise FileNotFoundError(f"No hay archivos TPM en {samples_dir}")
    n = max(tamaños)
    return "1" + "0" * (n - 1)


def _worker(condicion, alcance, mecanismo, tpm, estado_ini, queue):
    try:
        analizador = GeometricSIA(tpm, estado_ini)
        sol = analizador.aplicar_estrategia(condicion, alcance, mecanismo)
        queue.put({
            "particion": sol.particion,
            "perdida": str(sol.perdida).replace(".", ","),
            "tiempo": str(sol.tiempo_ejecucion).replace(".", ","),
        })
    except Exception as e:
        queue.put({"particion": None, "perdida": None, "tiempo": None, "error": str(e)})


def ejecutar_desde_excel(
    ruta_entrada: Path,
    ruta_salida: Path,
    inicio: int = 0,
    cantidad: int = 50,
    estado_ini: str | None = None,
    condiciones_fijas: str | None = None,
) -> None:
    df = pd.read_excel(ruta_entrada, sheet_name=8, usecols="B", skiprows=3, names=["Subsistema"])
    filas = df["Subsistema"].dropna().tolist()[inicio: inicio + cantidad]

    gestor = Manager(estado_ini or "")
    samples_dir = gestor.ruta_base
    estado_ini = estado_ini or _inferir_estado_inicial(samples_dir)
    condiciones_fijas = condiciones_fijas or ("1" * len(estado_ini))
    n_bits = len(estado_ini)

    tpm_path = samples_dir / f"N{n_bits}A.csv"
    if not tpm_path.exists():
        raise FileNotFoundError(f"TPM no encontrada: {tpm_path}")
    tpm = np.genfromtxt(tpm_path, delimiter=",")

    resultados = []
    for i, fila in enumerate(filas, start=inicio + 1):
        partes = str(fila).split("|")
        if len(partes) != 2:
            continue

        alcance = _convertir_a_binario(partes[0].rstrip(), n_bits)
        mecanismo = _convertir_a_binario(partes[1].rstrip(), n_bits)
        print(f"Iteración {i} — Alcance: {alcance}, Mecanismo: {mecanismo}")

        queue: multiprocessing.Queue = multiprocessing.Queue()
        proceso = multiprocessing.Process(
            target=_worker,
            args=(condiciones_fijas, alcance, mecanismo, tpm, estado_ini, queue),
        )
        proceso.start()
        proceso.join(timeout=3600)

        if proceso.is_alive():
            print(f"  Iteración {i}: timeout alcanzado.")
            proceso.terminate()
            proceso.join()
            resultado = {"particion": None, "perdida": None, "tiempo": None}
        else:
            resultado = queue.get() if not queue.empty() else {"particion": None, "perdida": None, "tiempo": None}

        resultados.append({
            "Iteración": i,
            "Alcance": alcance,
            "Mecanismo": mecanismo,
            "Partición": resultado.get("particion"),
            "Pérdida (φ)": resultado.get("perdida"),
            "Tiempo (s)": resultado.get("tiempo"),
        })

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(resultados).to_excel(ruta_salida, index=False)
    print(f"Resultados guardados en {ruta_salida}")


def iniciar():
    ruta_entrada = Path(os.getenv("IIT_INPUT_XLSX", str(PROJECT_ROOT / "data" / "results" / "Pruebas_Metodo2.xlsx")))
    ruta_salida = Path(os.getenv("IIT_OUTPUT_XLSX", str(PROJECT_ROOT / "data" / "results" / "resultados.xlsx")))
    estado_ini = os.getenv("IIT_ESTADO_INI")
    ejecutar_desde_excel(ruta_entrada, ruta_salida, estado_ini=estado_ini)
