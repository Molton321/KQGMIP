# K-QGMIP — Partición de Mínima Información y k-particiones

Framework de **Teoría de la Información Integrada (IIT)** que encuentra la **Partición de Mínima
Información (MIP)** de un sistema binario descrito por su **Matriz de Probabilidad de Transición
(TPM)**. Extiende la bipartición clásica (k=2) a **k-particiones, k ∈ {2,3,4,5}** con dos estrategias
núcleo —**KGeoMIP** (geométrica) y **KQNodes** (submodular)— y escala hasta **n ≈ 25 nodos**.

Dado un sistema y su TPM, busca la k-partición que **minimiza la pérdida de información** `δ_k`
(`δ_k = 0` ⇒ partición perfecta; `δ_k > 0` ⇒ información integrada causalmente).

> Especificación oficial: `docs/Proyecto_KQMIP.md` · Hoja de ruta: `PLANNING.md`

---

## Inicio rápido

Requisitos: Python 3.14 y [`uv`](https://github.com/astral-sh/uv).

```bash
git clone <url-del-repo> && cd KQGMIP
uv sync                     # dependencias base
uv sync --extra web         # + interfaz web (Streamlit + Plotly)
```

### 1. Interfaz web (lo más fácil — sin escribir comandos ni código)

```bash
uv run streamlit run streamlit_app.py     # o:  uv run python streamlit_app.py
```

Se abre en `http://localhost:8501`. Permite, desde el navegador: **generar una TPM**, elegir
**estrategia / k / subsistema**, y ver la **partición**, su `δ_k`, la distribución y las **figuras
estáticas e interactivas**.

### 2. Línea de comandos por banderas (sin editar código)

```bash
uv run exec.py --net N10A --k 3 --strategy kgeomip
uv run exec.py --net N4A  --k 2 --strategy kqnodes
```

Estrategias: `kgeomip`, `kqnodes`, `clustering`, `genetic`, `annealing`, `tabu`, `exhaustivek`.
Opcionales: `--page B`, `--method kmeans` (clustering), `--condition/--purview/--mechanism`,
`--profile`. Sin argumentos ejecuta una demostración.

### 3. Ruta avanzada (fijar el subsistema a mano)

Editar los valores al inicio de `main.py` y `uv run main.py`. Para procesar una tabla de
subsistemas desde Excel: `uv run exec.py --batch --strategy kqnodes --k 4`.

---

## Estrategias

Todas heredan de `SIA` y se puntúan con la **misma** pérdida `δ_k`.

| Estrategia | Clase | k | Rol |
|---|---|---|---|
| **KGeoMIP** | `KGeoMIP` | 2–5 | Núcleo geométrico (cortes sucesivos guiados por la tabla de costos) |
| **KQNodes** | `KQNodes` | 2–5 | Núcleo submodular (minimización tipo Queyranne) |
| **Clustering** | `ClusteringSIA` | 2–n | Baseline determinista (espectral / KMeans); sólo *propone* la partición |
| **Genetic / Annealing / Tabu** | `GeneticSIA` … | 2–5 | Metaheurísticas comparativas (deterministas con la semilla global) |
| **ExhaustiveK** | `ExhaustiveK` | 2–5 | Óptimo exacto por enumeración — *ground truth* sólo para n pequeño |
| BruteForce / GeometricSIA / QNodes / Phi | — | 2 | Referencias k=2 (regresión y validación PyPhi) |

**KGeoMIP/KQNodes son heurísticas voraces:** para k=2 dan el óptimo (= legado validado); para k≥3 son
cotas superiores y a veces subóptimas (la metaheurística **Tabú** suele recuperar el óptimo). Por eso
conviene tomar el **mínimo entre estrategias**.

---

## Datos (TPM)

`data/samples/N{n}{página}.csv`: `2^n` filas × `n` columnas, little-endian (la fila 0 es `00…0`),
0/1 deterministas o probabilidades continuas. Se cargan automáticamente por `n` y página.

```bash
uv run scripts/generate_tpm.py --n 4               # genera N4?.csv (0/1)
uv run scripts/generate_tpm.py --n 6 --continuous  # probabilidades continuas
```

…o desde la **interfaz web** (botón «Generar TPM»), sin línea de comandos.

---

## Verificación y experimentación

```bash
uv run pytest                              # 207 tests (regresión k=2, k=3..5 vs exacto, determinismo…)
uv run scripts/validate_optimality.py      # ¿son óptimas? exacto (n≤4) + convergencia (N10A/N15A)
uv run scripts/validate_correctness.py     # δ_k = recomputado, y ≤ exacto, por estrategia
uv run scripts/run_benchmark.py            # tabla de estrategias × redes × k -> data/results/
uv run scripts/make_figures.py             # figuras estáticas (PNG)
uv run scripts/make_interactive.py         # figuras interactivas (HTML, Plotly)
```

**Cómo se valida que las particiones son las mejores:** donde el exacto es tratable (n≤4) el sistema
(mejor estrategia) iguala el óptimo enumerado por fuerza bruta (4/4); a n=10/15, tres búsquedas
independientes (geométrica, submodular y metaheurística) **convergen** al mismo `δ_k`, lo que es
fuerte evidencia de óptimo global. El consolidado vive en `data/results/benchmark_results_FINAL.csv`.

---

## Estructura

```
KQGMIP/
├── streamlit_app.py            # interfaz web (Streamlit)
├── exec.py                     # CLI por banderas (individual / --batch)
├── main_batch.py               # procesamiento por lotes desde Excel
├── src/
│   ├── constants/              # constantes centralizadas (base, errors, tags)
│   ├── controllers/
│   │   ├── manager.py          # carga/genera TPMs (carga en float32)
│   │   └── strategies/         # force, geometric, q_nodes, phi, exhaustive_k,
│   │                           #   kgeomip, kqnodes, clustering, metaheuristics
│   ├── funcs/                  # emd (δ_k), cost_table, k_refine, metaheuristic,
│   │                           #   runner (registro único de estrategias), labels…
│   ├── middlewares/            # slogger (logs), profile (@profile)
│   ├── models/{base,core,enums}/  # sia/application · ncube/system/solution/partition · enums
│   └── viz/                    # figuras estáticas (matplotlib) e interactivas (Plotly)
├── scripts/                    # benchmark, figuras, validación, generación de TPM
├── data/{samples,results}/     # TPMs CSV · resultados Excel/CSV + figuras
├── tests/{unit,integration,fixtures}/
└── docs/                       # especificación oficial + manuales
```

`src/funcs/runner.py` es el **único** registro estrategia→constructor: la UI, el CLI y los scripts
construyen y ejecutan estrategias a través de él (`run_analysis`, `build_strategy`, `parse_net_label`).

---

## Instalación y extras

```bash
uv sync                 # base
uv sync --extra web     # Streamlit + Plotly (interfaz web + figuras interactivas)
uv sync --extra viz     # sólo Plotly (figuras interactivas)
uv sync --extra emd     # pyemd (EMD causal opcional de comprobación)
```

`uv.lock` se versiona. Reportes de profiling: `review/profiling/…` · logs: `logs/…`.

---

## Stack

| Componente | Uso |
|---|---|
| NumPy 2.4 · SciPy 1.17 · pandas 3.0 | tensores/EMD · clustering espectral · E/S |
| more_itertools | particiones de Stirling (exacto) |
| matplotlib · plotly *(extra)* | figuras estáticas · interactivas |
| streamlit *(extra)* | interfaz web |
| pyphi *(validación)* · pyemd *(extra)* | oráculo IIT k=2 · EMD causal |
| joblib · psutil | paralelismo por procesos (PCD) |
| pytest · ruff · mypy *(dev)* | tests · lint · tipos |

GIL activo → el paralelismo es **por procesos** (no hilos).

---

## Convenciones

- Nomenclatura obligatoria y consistente: **KGeoMIP** y **KQNodes** (la «K» = k-particiones).
- Código en **inglés** (identificadores, docstrings, comentarios); salidas/logs en español.
- Toda estrategia hereda de `SIA` y valida contra el oráculo (`BruteForce`/exacto, PyPhi).
- Techo honesto: **n ≈ 25**; no se promete escalar más.
