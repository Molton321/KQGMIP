# GeoMIP — Análisis de Mínima Partición de Información (MIP)

Implementaciones del problema de **Mínima Partición de Información (MIP)** de la Teoría Integrada de Información (IIT). El repositorio contiene tres estrategias comparables:

| Estrategia | Descripción | Velocidad |
|---|---|---|
| **Phi (PyPhi)** | Referencia exacta, fuerza bruta | Lenta |
| **QNodes** | Algoritmo Q-Nodes, baseline optimizado | Media |
| **Geometric** | Programación dinámica geométrica | Rápida |
| **Geometric K** | Extensión a K-particiones (K ≥ 2) | Rápida |

---

## Requisitos del sistema

- **SO:** Linux (probado en Ubuntu) o macOS
- **Python:** 3.9 o superior
- **uv:** gestor de entornos y dependencias

### Instalar uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

O con pip:

```bash
pip install uv
```

> **Nota sobre PyPhi/Phi:** La estrategia Phi requiere compilar la librería `pot` (C++). Si no tienes `g++` instalado, las estrategias Geometric y QNodes seguirán funcionando normalmente. Para habilitar Phi: `sudo apt install build-essential` (Ubuntu) o `xcode-select --install` (macOS).

---

## Estructura del repositorio

```
projecto-analisis-20263/
├── GeoMIP/
│   ├── data/samples/          ← TPMs de prueba (N3A.csv … N15B.csv)
│   ├── results/               ← Excel de entrada/salida para ejecución por lotes
│   └── src/
│       └── Method2_Dynamic_Programming_Reformulation/   ← Geometric + QNodes + Phi
│           ├── exec.py        ← ejecución por lotes desde Excel
│           ├── src/
│           │   ├── controllers/strategies/
│           │   │   ├── geometric.py
│           │   │   ├── geometric_k.py
│           │   │   ├── q_nodes.py
│           │   │   └── phi.py
│           │   └── main_k.py  ← pruebas K-particiones
│           └── pyproject.toml
├── QNodes/                    ← implementación standalone de QNodes/Phi
│   ├── exec.py
│   └── pyproject.toml
└── geomip_app/                ← Interfaz web Streamlit
    ├── streamlit_app.py
    ├── run.sh                 ← script de lanzamiento (recomendado)
    └── core/
```

---

## Opción 1 — Interfaz web (recomendada)

La forma más sencilla de usar el proyecto. Permite cargar TPMs, configurar parámetros visualmente y comparar las tres estrategias con gráficos interactivos.

### Configuración (una sola vez)

```bash
# 1. Clonar o entrar al repositorio
cd projecto-analisis-20263

# 2. Instalar dependencias del proyecto (Method2)
cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv sync --frozen        # instala todo desde el lock file

# 3. Instalar dependencias de la app web (streamlit, plotly)
uv pip install streamlit plotly openpyxl --python .venv/bin/python

# 4. Volver a la raíz
cd ../../..
```

### Ejecutar la app

```bash
bash geomip_app/run.sh
```

Abre el navegador en `http://localhost:8501`.

> El script `run.sh` detecta automáticamente el entorno correcto. No necesitas activar el venv manualmente.

### Uso básico

1. **Carga de datos:** selecciona una red predefinida (N3A–N15B) en el panel lateral
2. **Estado inicial:** marca los bits activos de cada nodo (ej: solo A activo → `[1,0,0,…]`)
3. **Condiciones / Alcance / Mecanismo:** selecciona los nodos participantes
4. **Estrategias:** activa Geometric y/o QNodes (Phi requiere compilación C++)
5. Haz clic en **▶️ Ejecutar**
6. Explora los tabs **Resultados**, **Gráficos**, **Análisis** y **Exportar**

---

## Opción 2 — Ejecución por lotes desde Excel (Method2)

Procesa múltiples subsistemas definidos en un Excel y guarda los resultados.

### Configuración

```bash
cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv sync --frozen
```

### Ajustar parámetros

Edita `src/main.py` o las variables de entorno:

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `GEOMIP_INPUT_XLSX` | Excel con los casos a analizar | `GeoMIP/results/Pruebas_Metodo2.xlsx` |
| `GEOMIP_OUTPUT_XLSX` | Excel de resultados | `GeoMIP/results/resultados_Geometric.xlsx` |
| `GEOMIP_SAMPLES_DIR` | Directorio de TPMs | auto-detectado |

### Ejecutar

```bash
uv run exec.py
```

Los resultados se guardan en `GeoMIP/results/resultados_Geometric.xlsx`.

---

## Opción 3 — Ejecutar QNodes standalone

```bash
cd QNodes
uv sync
uv run exec.py
```

Edita `QNodes/src/main.py` para cambiar `estado_inicial`, `condiciones`, `alcance` y `mecanismo`.

---

## Opción 4 — Pruebas K-particiones por consola

Para comparar K=2, K=3, K=4 sobre una red específica:

```bash
cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation
PYTHONPATH=. .venv/bin/python -m src.main_k
```

Edita el bloque `if __name__ == "__main__":` al final de `src/main_k.py` para cambiar la red y los parámetros.

---

## Datos de prueba disponibles

| Archivo | Nodos | Estados |
|---|---|---|
| `N3A.csv` | 3 | 8 |
| `N4A.csv`, `N4B.csv`, `N4C.csv` | 4 | 16 |
| `N5A.csv`, `N5B.csv` | 5 | 32 |
| `N6A.csv` | 6 | 64 |
| `N8A.csv` | 8 | 256 |
| `N10A.csv` | 10 | 1024 |
| `N15A.csv`, `N15B.csv` | 15 | 32768 |

Todos están en `GeoMIP/data/samples/`.

---

## Solución de problemas frecuentes

### `ModuleNotFoundError: No module named 'ot'`

La librería `pyphi` necesita compilar `pot` (C++). Esto no afecta a Geometric ni QNodes.

```bash
# Ubuntu/Debian
sudo apt install build-essential
cd GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv sync
```

### La app muestra error al ejecutar análisis

Asegúrate de usar el script `run.sh` en lugar de `streamlit run streamlit_app.py` directamente. El script configura el entorno correcto.

### `uv sync` falla por `pot`

Si no tienes compilador C++ y no necesitas Phi:

```bash
uv sync --frozen   # usa el lock existente, omite compilación
```

### El estado inicial no coincide con la TPM

El largo del estado inicial debe ser igual al número de columnas de la TPM. Para `N10A.csv` (10 nodos), el estado inicial debe tener exactamente 10 bits.

### QNodes termina muy rápido

No es error: si φ = 0, hay terminación temprana porque la partición óptima ya fue encontrada.

---

## Configuración avanzada

### Cambiar la estrategia en exec.py

En `GeoMIP/src/Method2_Dynamic_Programming_Reformulation/src/main.py`:

```python
from src.controllers.strategies.geometric import GeometricSIA   # rápida
# from src.controllers.strategies.q_nodes import QNodes          # baseline
# from src.controllers.strategies.phi import Phi                 # referencia exacta

analizador = GeometricSIA(gestor_sistema)
```

### Cambiar la red de prueba

En `GeoMIP/src/Method2_Dynamic_Programming_Reformulation/src/main.py`:

```python
estado_inicial = "1000000000"   # N10A — 10 nodos, primer nodo activo
# estado_inicial = "100"        # N3A — 3 nodos
```

La TPM se selecciona automáticamente según el largo del estado inicial.
