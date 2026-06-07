# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Convención de código (2026-06-07):** todo el código va en **inglés** (identificadores,
> docstrings y comentarios), **completamente documentado con docstrings y comentarios en línea en
> secciones complejas** + tests, como exige la rúbrica oficial (`docs/Proyecto_KQMIP.md` §4.1/§4.5).
> Español solo en `PLANNING.md`, `README.md`, `docs/` y la bitácora.
> **Base correcta:** el repo upstream pasa a ser **20263** (`Molton321/projecto-analisis-20263`,
> rama `main`); se sigue en este repo portando lo nuevo de 20263 (ver `PLANNING.md` Anexo A.5).
> La hoja de ruta por fases está en `PLANNING.md` (léela antes de trabajar).

## Qué es este proyecto

Framework de **Teoría de la Información Integrada (IIT)** que busca la **Partición de Mínima
Información (MIP)** de un sistema binario descrito por una Matriz de Probabilidad de Transición
(TPM). El estado actual es una **plantilla de biparticiones (k=2)**; el objetivo del proyecto es
extenderla a **k-particiones, k ∈ {2,3,4,5}** mediante dos estrategias que heredan de `SIA`:
**`KGeoMIP`** (geométrica) y **`KQNodes`** (submodular), escalando en número de nodos hasta **n≈25**.

Nomenclatura **obligatoria** y consistente (repo, carpetas, clases, docs, video):
**`KGeoMIP`** y **`KQNodes`** (la 'K' = k-particiones).

**Portafolio de estrategias** (todas heredan de `SIA`, todas se puntúan con la misma pérdida δ_k):
1. **Exacto** (Stirling `S(n,k)` con `more_itertools`) — ground truth para n pequeño.
2. **`KGeoMIP`** y **`KQNodes`** — las dos estrategias núcleo del proyecto.
3. **Baseline clustering** (`src/.../strategies/clustering/`) — estrategia comparativa
   **determinista**: trata la k-MIP como partición de grafo (afinidad → **clustering espectral /
   detección de comunidades / KMeans** vía `scipy.sparse.csgraph`). Precedente oficial "Estrategia
   KM". El clustering solo **propone** la partición; la calidad se mide con δ_k, no con su métrica interna.
4. **Metaheurísticas GA/SA/Tabú** — variante de comparación **opcional** (solo si hay tiempo).

## Realidad verificada de la base (no asumir, ya comprobado)

- ✅ Núcleo `System` / `NCube` / `emd_efecto` es **correcto** (`BruteForce` ≡ `GeoMIP` en 21/21 casos).
- ✅ **`GeometricSIA` (GeoMIP) da el óptimo exacto** → base sólida para `KGeoMIP`.
- ✅ **`QNodes` corregido ya portado de 20263** (Fase 0): acierta **9/10** vs oráculo en N2A–N6A
  (antes 2/8 con la base vieja `.core/core_00`). Base válida para construir `KQNodes`. El defecto
  histórico y el triaje quedan congelados en `tests/unit/test_qnodes_triage.py`.
- ✅ PyPhi funciona en este entorno (Python 3.14.5 + NumPy 2.4.6); úsalo como cross-check.
- ⚠️ GIL **activo** (no free-threaded): paraleliza por **procesos** (`joblib`/`multiprocessing`), no hilos.

## Comandos

Gestión con [`uv`](https://github.com/astral-sh/uv) (Python 3.14.5).

```bash
uv sync                  # instalar dependencias
uv run exec.py           # análisis individual (configurado en main.py)
uv run exec.py --batch   # análisis por lotes desde Excel (main_batch.py)
uv run pytest            # tests (tras Fase 0; hoy aún no existen)
uv run ruff check . && uv run mypy src   # lint + tipos (tras Fase 0)
```

`exec.py` despacha a `main.py` (individual) o `main_batch.py` (`--batch`) tras fijar opciones en el
singleton `application`. La TPM se autocarga de `data/samples/N{len(initial_state)}{page}.csv`.

> **Convención de identificadores (2026-06-07):** todo el código fuente está en **inglés**. Los
> nombres de métodos/atributos que aparecen abajo usan ya la API en inglés. Las **cadenas
> de salida/logs/errores** se mantienen en español (la UX y los manuales son en español).

## Arquitectura (lo que hay que leer junto)

Patrón **Strategy + Template Method** sobre la clase abstracta `SIA` (`src/models/base/sia.py`):

1. `Manager.load_network()` (`src/controllers/manager.py`) carga la TPM.
2. La estrategia se construye con `(tpm, initial_state)` y se llama
   `apply_strategy(condition, purview, mechanism)`.
3. `SIA.sia_prepare_subsystem(...)` ejecuta el pipeline compartido: `System` (un `NCube` por nodo)
   → `condition` (condiciones de fondo) → `subtract` (purview/mechanism) → subsistema +
   `marginal_distribution`.
4. La estrategia busca particiones, puntúa con EMD y devuelve un `Solution`.

Modelo de datos clave (leer `system.py` y `ncube.py` **juntos** — la indexación de ejes no es obvia):
- `System` = colección de `NCube`; operaciones `condition`, `subtract`, `bipartition` (memoizada),
  `marginal_distribution`.
- `NCube` = columna de la TPM como tensor `(2,)*n`; `condition`/`marginalize` son puros y devuelven
  nuevos `NCube`. ⚠️ `marginalize` es **O(2^m)** (cuello de rendimiento: 1.45 s a m=24) — el fitness
  de k-particiones debe usar marginal **local** O(2^dims), no recalcular sobre el tensor completo.
- Vértices del subsistema = tuplas `(tiempo, indice)` con `tiempo ∈ {ACTUAL, EFECTO}` (`constants/base.py`).

Estrategias: la estructura **oficial (= 20263) ya está aplicada** (Fase 0). Las estrategias viven en
**`src/controllers/strategies/`** (`force.py`, `geometric.py`, `q_nodes.py`, `phi.py` y las nuevas
k-estrategias + `clustering/`), con `Manager` en `src/controllers/manager.py`, modelos en
`src/models/{base,core,enums}/` (`sia.py`/`application.py` en `base/`; `ncube.py`/`system.py`/
`solution.py` en `core/`), utilidades en `src/funcs/` y profiling/logging en `src/middlewares/`
(ver `PLANNING.md` Anexo A.5 para el mapeo del rename).

Configuración global: singleton `application` (`src/models/base/application.py`) — semilla, página de
red, métrica, notación, variante EMD, profiling. Lo leen estrategias/modelos/EMD directamente; fíjalo
en `exec.py` antes de `run()`.

Middlewares: `src/middlewares/slogger.py` (`SafeLogger`, logs en `logs/`), `src/middlewares/profile.py`
(`@profile`, HTML en `review/profiling/`). Constantes centralizadas en `src/constants/` (no usar
literales mágicos).

## Datos

- `data/samples/N{n}{letra}.csv`: TPM determinista 0/1, `2^N` filas × `N` cols, little-endian
  (fila 0 = `000…0`). Generar con `Manager(state).generate_network(n, deterministic=...)`.
- `data/results/`: datos oficiales — `Pruebas_Metodo2.xlsx` (ground truth PyPhi k=2),
  `DatosPruebas2026_1.xlsx` (**rejilla de evaluación** k∈{2,3,4,5} × n∈{10,15,20,22,25}),
  `pruebas_Metodo1.xlsx` (plantilla de métricas). El formato de salida debe replicar esta rejilla.
- Generados (`review/`, `.logs/`, `*.log`) están en `.gitignore`.

## Invariantes (reglas que no se rompen)

1. **k=2 debe reproducir exactamente** los resultados legacy de GeoMIP y QNodes (test de regresión).
2. **Toda estrategia hereda de `SIA`** y llama `sia_prepare_subsystem(...)` antes de buscar.
3. **Validar contra el oráculo:** cualquier resultado nuevo se compara con `BruteForce`/exacto
   (n pequeño) y PyPhi (6–10 nodos). No se confía en una estrategia sin esta comprobación.
4. **Verificar, no asumir:** afirmaciones sobre entorno/versiones/rendimiento se comprueban con un
   comando antes de darlas por ciertas (registrar en `PLANNING.md` Anexo A).
5. **Nomenclatura KGeoMIP/KQNodes** consistente en código y docs.
6. **Docstrings + tipos** en todo método público; tests para componentes nuevos.
7. **Techo n≈25**: no prometer escalar más; documentar la limitación honestamente.

## Flujo de trabajo por fases (obligatorio)

Cada fase de `PLANNING.md` se entrega en **su propia rama**. Al **terminar** una fase (y solo
cuando está terminada: código + docstrings/tipos + tests + validación cruzada contra el oráculo,
con **`pytest`/`ruff`/`mypy` en verde**), seguir este ciclo **antes** de empezar la siguiente:

1. **Rama por fase:** trabajar la fase en `feature/faseN-<slug>` (ej. `feature/fase3-kgeomip`),
   creada desde el tip de la fase anterior.
2. **Validar:** `uv run pytest -q && uv run ruff check . && uv run mypy src` en verde; validar el
   resultado nuevo contra `BruteForce`/exacto y, si aplica, PyPhi (Invariante 3).
3. **Bitácora:** registrar la fase en `logs/ai_agent_changelog.md` (parámetros reales + uso de IA) y
   actualizar la tabla de seguimiento de `PLANNING.md` (fase → ✅, siguiente → 🟨).
4. **Commit:** commits atómicos y descriptivos de **todos** los cambios de la fase (incluida la doc).
5. **Push + revisión:** `git push -u origin feature/faseN-...`; abrir PR para revisión (no se fusiona
   a `main` sin aprobación explícita del usuario; ver nota de remote en `PLANNING.md` Anexo A.5).
6. **Continuar:** crear la rama de la fase siguiente **desde** la rama recién subida y repetir.

No mezclar dos fases en una sola rama; no empezar la fase N+1 con la fase N a medias o en rojo.

## Bitácora obligatoria (incluye uso de IA)

Registrar **cada** cambio de código, ajuste de parámetros y decisión de diseño en
`logs/ai_agent_changelog.md`: fecha/hora, acción, **parámetros reales** probados (no ejemplos
figurados), justificación técnica y, cuando aplique, **qué generó o influyó la IA** (los criterios
oficiales exigen documentar el uso de IA generativa). Hacerlo en el momento, no al final.

## Stack real (jun 2026)

Declarado en `pyproject.toml` y en uso/objetivo: `numpy` 2.4.6, `scipy` 1.17.1, `pandas` 3.0.3,
`openpyxl`, `colorama`, `pyinstrument`, `pyphi` (validación), `joblib`/`psutil`/`tqdm`
(PCD/medición), `more_itertools` (particiones de Stirling — **no** graphillion), `matplotlib`
(gráficas, ya añadido). Clustering baseline: `scipy.sparse.csgraph`/`scipy.linalg` (espectral) y
`scikit-learn` (KMeans, si se usa). Grupo `dev`: `pytest`/`pytest-cov`/`ruff`/`mypy`/`hypothesis`.
Extra opcional: `pyemd` (métrica EMD alternativa; requiere compilación, no bloquea `uv sync`).
`uv.lock` se versiona. Opcional según perfilado: `numba`. Opcional UI: `streamlit`.
No usar: Polars, Ray/Dask, Cython (no aportan al alcance; serían deuda técnica).
