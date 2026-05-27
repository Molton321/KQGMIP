# Framework IIT — Mínima Partición de Información (MIP)

Framework de investigación para analizar la **Integrated Information Theory (IIT)** y encontrar la **Minimal Information Partition (MIP)** de sistemas binarios. Compara cuatro estrategias algorítmicas sobre la misma base de código unificada.

---

## Estructura del proyecto

```
projecto-analisis-20261/
│
├── exec.py              ← Punto de entrada principal
├── main.py              ← Configuración para análisis individual
├── main_batch.py        ← Procesamiento en lote desde Excel
├── pyproject.toml       ← Dependencias Python (uv)
├── pyphi_config.yml     ← Configuración de la librería pyphi
│
├── src/
│   ├── base/
│   │   ├── application.py   ← Singleton de configuración global
│   │   └── sia.py           ← Clase abstracta base para todas las estrategias
│   │
│   ├── constants/
│   │   ├── base.py          ← Constantes numéricas, rutas y símbolos
│   │   ├── errors.py        ← Mensajes de error
│   │   └── tags.py          ← Etiquetas de estrategias y valores dummy
│   │
│   ├── models/
│   │   ├── enums/
│   │   │   ├── distance.py      ← MetricDistance (Hamming, Manhattan, Euclidiana)
│   │   │   ├── notation.py      ← Notation (LIL_ENDIAN, BIG_ENDIAN, ...)
│   │   │   └── temporal_emd.py  ← TimeEMD (EMD_EFECTO, EMD_CAUSA, EMD_INTEGRADA)
│   │   ├── ncube.py         ← N-cubo n-dimensional (núcleo de datos)
│   │   ├── system.py        ← Sistema IIT: condicionamiento, substracción, bipartición
│   │   └── solution.py      ← Representación visual de resultados
│   │
│   ├── funcs/
│   │   ├── emd.py           ← emd_efecto, emd_causal, seleccionar_emd
│   │   ├── format.py        ← Formateo de biparticiones para consola
│   │   ├── labels.py        ← Etiquetas alfabéticas, lil_endian, reindexar
│   │   └── partitions.py    ← Generadores de biparticiones y subsistemas
│   │
│   ├── io/
│   │   ├── manager.py       ← Carga TPMs y gestiona rutas de salida
│   │   ├── logger.py        ← SafeLogger con colores y archivos .log
│   │   └── profiler.py      ← Perfil de ejecución HTML (pyinstrument)
│   │
│   └── strategies/
│       ├── brute_force.py   ← Fuerza bruta exhaustiva
│       ├── q_nodes.py       ← Algoritmo Q-Nodes (greedy submodular)
│       ├── pyphi_wrapper.py ← Envuelve la librería pyphi (referencia)
│       └── geometric.py     ← GeoMIP Método 2 (programación dinámica)
│
├── data/
│   ├── README.md        ← Descripción de cada dataset disponible
│   ├── samples/         ← TPMs en CSV (N2–N8, notación little-endian)
│   └── results/         ← Salidas de análisis (Excel)
│
└── docs/
    └── algoritmos.md    ← Descripción técnica de cada estrategia
```

---

## Flujo de funcionamiento

```
exec.py
  └─► main.py  (o main_batch.py con --batch)
        └─► Manager.cargar_red()
              └─► Lee data/samples/N{n}{página}.csv
        └─► Estrategia(tpm, estado_inicial)
              └─► sia_preparar_subsistema(condicion, alcance, mecanismo)
                    1. System(tpm, estado)       → crea n-cubos desde la TPM
                    2. system.condicionar()       → aplica condiciones de fondo
                    3. candidato.substraer()      → genera subsistema objetivo
              └─► aplicar_estrategia()
                    → evalúa biparticiones sobre el subsistema
                    → calcula EMD efecto por partición
                    → retorna Solution con φ mínimo
        └─► print(solucion)                       → resultado en consola
```

### ¿Qué calcula el framework?

Dado un sistema de N nodos con una TPM, el framework encuentra la **bipartición** del subsistema que **minimiza la pérdida de información** (valor φ mínimo).

- `φ = 0` → sistema perfectamente particionable (información separable)
- `φ > 0` → el sistema integra información causalmente

### Parámetros de entrada (cadenas de bits de longitud N)

| Parámetro       | Bit = 1               | Bit = 0                      |
|-----------------|-----------------------|------------------------------|
| `estado_inicial`| nodo activo (ON)      | nodo inactivo (OFF)          |
| `condiciones`   | variable presente     | variable condicionada (fija) |
| `alcance`       | futuro incluido       | futuro marginalizado         |
| `mecanismo`     | presente incluido     | presente marginalizado       |

---

## Estrategias disponibles

| Estrategia    | Clase            | Complejidad     | Cuándo usar                        |
|---------------|------------------|-----------------|------------------------------------|
| Fuerza Bruta  | `BruteForce`     | O(2^(m+n))      | Sistemas pequeños (N ≤ 6), exacta  |
| Q-Nodes       | `QNodes`         | Polinomial      | Sistemas medianos, resultado rápido|
| PyPhi         | `Phi`            | —               | Validación con librería de referencia|
| GeoMIP        | `GeometricSIA`   | Sub-exponencial | Sistemas grandes, modo batch       |

---

## Modo de ejecución

### Requisitos

- Python ≥ 3.11
- [`uv`](https://github.com/astral-sh/uv) instalado (`pip install uv`)

### Instalación

```bash
git clone <url-del-repo>
cd projecto-analisis-20261
uv sync
```

### Análisis individual

**1. Configura `main.py`:**

```python
estado_inicial = "1000"   # 4 nodos, solo A activo
condiciones    = "1110"   # A, B, C presentes; D condicionado
alcance        = "1110"   # A, B, C en futuro; D marginalizado
mecanismo      = "1110"   # A, B, C en presente; D marginalizado
```

**2. Elige la estrategia (descomenta en `main.py`):**

```python
analizador = BruteForce(tpm, estado_inicial)
# analizador = QNodes(tpm, estado_inicial)
# analizador = GeometricSIA(tpm, estado_inicial)
```

**3. Ejecuta:**

```bash
uv run exec.py
```

La TPM se carga automáticamente desde `data/samples/N4A.csv`
(4 nodos → N4, página A → configurado en `exec.py`).

### Procesamiento en lote (GeoMIP)

```bash
# Variables de entorno opcionales
export IIT_INPUT_XLSX="data/results/Pruebas_Metodo2.xlsx"
export IIT_OUTPUT_XLSX="data/results/resultados.xlsx"
export IIT_ESTADO_INI="1000000000"   # 10 nodos

uv run exec.py --batch
```

### Configuración avanzada en `exec.py`

```python
from src.base.application import aplicacion
from src.models.enums.temporal_emd import TimeEMD

aplicacion.set_pagina_red_muestra("B")          # usa N{n}B.csv en lugar de A
aplicacion.set_tiempo_emd(TimeEMD.EMD_CAUSA)    # EMD causal en lugar de efecto
aplicacion.desactivar_profiling()               # sin reportes HTML
```

### Profiling de rendimiento

Reportes HTML de ejecución generados en:
```
review/profiling/NET{n}{página}/{DD_MM_YYYY}/{HH}hrs/
```
Abre el `.html` en un navegador para analizar costos temporales por función.

### Logs de ejecución

```
.logs/{DD_MM_YYYY}/{HH}hrs/{nombre}.log
.logs/last_{nombre}.log   ← última ejecución
```

---

## Agregar una nueva red

**Opción 1 — Generar aleatoriamente:**
```python
from src.io.manager import Manager
Manager("100000").generar_red(6, determinista=False)  # crea data/samples/N6B.csv
```

**Opción 2 — Archivo manual:**

Coloca el CSV en `data/samples/` con nombre `N{n}{letra}.csv`.
- Formato: `2^N filas × N columnas`, separado por comas
- Indexación little-endian (fila 0 = estado `000...0`, fila 1 = `100...0`)
