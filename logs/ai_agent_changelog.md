# Bitácora de cambios (incluye uso de IA generativa)

Registro cronológico de cada cambio de código, ajuste de parámetros y decisión de diseño, con
fecha/hora, acción, parámetros reales probados, justificación y uso de IA. Asistente: Claude Code
(Opus 4.8). Formato exigido por `CLAUDE.md` y por los criterios oficiales (`docs/Proyecto_KQMIP.md` §4.5).

---

## 2026-06-06 — Inicio Fase 0: verificación de entorno y línea base

- **Acción:** verificación empírica del entorno (regla "verificar, no asumir").
  - Python 3.14.5, GIL activo (`sys._is_gil_enabled() = True`).
  - Instalados: numpy 2.4.6, scipy, pandas, openpyxl, colorama, pyinstrument, pyttsx3, pyphi,
    more_itertools, joblib, psutil, tqdm. **Faltan:** pyemd, matplotlib, numba.
- **Acción:** captura de golden δ (subsistema completo, `cond=alc=mec="1"*n`) en N2A–N6A.
  - Oráculo (BruteForce ≡ GeometricSIA): N2A 0.0, N3A 0.25, N3B 0.46875, N3C 0.0, N4A 0.0,
    N4B 0.0, N4C 0.0, N5A 0.0, N5B 0.125, N6A 0.46875. **Coinciden 10/10.**
  - QNodes (defectuoso): subóptimo en 8/10.
- **Acción:** generación de muestras con `Manager(estado).generar_red(n, determinista=True)`,
  semilla `aplicacion.semilla_numpy = 73`. Resultados: N20A.csv (42 MB, 4.0 s),
  N22A.csv (185 MB, 16.9 s), N25A.csv (1.7 GB, 156.9 s).
- **Acción:** medición del techo n=25.
  - Carga uint8 (pandas) de N25A: shape (33 554 432, 25), 57.3 s, pico RSS 1.64 GB.
  - Proyección NCubes: float64 6.25 GB, float32 3.12 GB, TPM uint8 0.78 GB. RAM libre ~6.6 GB →
    el cuello es construir los NCubes en float64; valida la necesidad de uint8/float32 (Fase 6).
- **IA:** la IA exploró el repo, escribió los scripts de verificación y los tests de caracterización.

## 2026-06-06 — Tooling e infraestructura

- **Acción:** reescritura de `pyproject.toml` (nombre `kqgmip`): dependencias reales + extra
  opcional `emd = [pyemd]` + grupo `dev` (pytest, pytest-cov, ruff, mypy, hypothesis) + config de
  ruff/mypy/pytest/coverage. `pythonpath = ["."]` para que `import src` funcione en tests.
- **Acción:** tests de caracterización (red de seguridad) en `tests/`:
  `tests/unit/test_regression_k2.py` (BF ≡ Geo + golden oráculo) y
  `tests/unit/test_qnodes_triage.py` (congela δ de QNodes y documenta el defecto). `tests/conftest.py`
  desactiva profiling. **Resultado: 49 passed.**
- **Acción:** `.gitignore`: se quita `uv.lock` (ahora se versiona) y se ignoran muestras grandes
  (`data/samples/N20*.csv`, `N22*.csv`, `N25*.csv`).

## 2026-06-07 — Corrección de base: el repo base correcto es 20263

- **Hallazgo (compañero):** la base correcta es `Molton321/projecto-analisis-20263` (rama `main`,
  ya integra `copilot/make-commit-of-claude-info`). El `src/` unificado de este repo se derivó de
  `.core/core_00` (snapshot viejo).
- **Acción:** clonado y comparación de 20263.
  - Samples idénticos byte a byte (N3A–N15B) → golden δ no se invalidan.
  - Equivalencia ejecutando el código de 20263 (parche temporal en `/tmp`: `tpm` opcional para
    single-state; `np.infty → np.inf` en `force.py`) sobre N3A–N6A:
    - **BF y GeoMIP de 20263 ≡ oráculo en 8/8.**
    - **QNodes de 20263 acierta 7/8** (falla N3B: 0.5 vs 0.46875), frente a **2/8 del QNodes actual**.
  - Deuda en 20263: `force.py` usa `np.infty` (removido en NumPy 2.0).
- **Decisión:** seguir en este repo + **portar lo nuevo de 20263** (QNodes corregido; optimizaciones
  de GeoMIP: matriz precomputada, early-exit `emd==0`); re-validar golden tras portar.
- **Decisión (convención de código):** revertir el "sin comentarios/docstrings" previo. La rúbrica
  oficial (`docs/Proyecto_KQMIP.md` §4.1 línea 123 y §4.5 línea 155) exige docstrings + comentarios
  en secciones complejas + tests. **Código en inglés, documentado.** Actualizados `PLANNING.md`
  §2.8 y Anexo A.5, y `CLAUDE.md`.
- **Decisión (estructura):** adoptar el layout oficial **`src/controllers/strategies/`** (= 20263),
  `docs/Proyecto_KQMIP.md` §4.1 línea 119.
- **Decisión (nombre):** renombrar a **K_QGMIP** según la documentación.
- **Pendiente:** re-apuntar el remote (pull/push) de este repo a 20263 como último paso.
- **IA:** la IA realizó la comparación de repos, la verificación de equivalencia y la redacción de
  estas decisiones en los documentos gobernantes.

## 2026-06-07 — Paso 1: reestructura al layout oficial

- **Acción:** reorganización de `src/` al layout oficial `src/controllers/strategies/` (= 20263)
  con `git mv` (preserva historia):
  - `src/base/` → `src/models/base/` (application, sia)
  - `src/models/{ncube,system,solution}.py` → `src/models/core/`
  - `src/io/manager.py` → `src/controllers/manager.py`
  - `src/io/{logger,profiler}.py` → `src/middlewares/{slogger,profile}.py`
  - `src/strategies/<n>/strategy.py` → `src/controllers/strategies/{force,geometric,q_nodes,phi}.py`
    (aplanado; los `tags.py` por estrategia se inlinearon en cada módulo).
  - Imports reescritos con `sed` (patrón uniforme), `__init__.py` creados.
- **Verificación:** `compileall` OK, imports OK, **49 tests verdes**.

## 2026-06-07 — Paso 2: portar QNodes corregido de 20263

- **Acción:** reescritura de `src/controllers/strategies/q_nodes.py` con la lógica de 20263
  (GeoMIP/.../controllers/strategies/q_nodes.py), adaptada a la API `(tpm, estado_inicial)`.
  Cambios clave que corrigen el defecto: `funcion_submodular` reconstruye el estado `temporal`
  en cada llamada (sin `clave_submodular` compartida ni memoización mal indexada); bucle de
  fases `range(len-2)`; sin early-return en `emd_delta==0`.
- **Resultado medido (N2A–N6A, subsistema completo):** QNodes ahora acierta **9/10** vs oráculo
  (BruteForce); único subóptimo **N3B** (0.5 vs 0.46875). Antes: 2/10.
- **Acción:** actualizados `tests/fixtures/golden_k2.py` (`QNODES_LOSS`, `QNODES_SUBOPTIMAL=["N3B"]`)
  y el triaje. **42 tests verdes** (bajan de 49 por menos casos parametrizados subóptimos).
- **Decisión:** las **optimizaciones de rendimiento de GeoMIP** de 20263 (matriz precomputada,
  `_estado_a_idx`, early-exit `emd==0`) se **difieren a la Fase 6** (optimización guiada por
  profiling); δ de GeoMIP ya es correcta (8/8), así que no aportan corrección, solo velocidad.
- **IA:** la IA realizó la reestructura, el port del QNodes y la actualización de tests/golden.

## 2026-06-07 — Ajustes: quitar pyttsx3 y unificar logs

- **Acción (decisión del usuario):** eliminar la feature de voz `pyttsx3` de `Solution`
  (`src/models/core/solution.py`): removidos `_anunciar`, `_obtener_voz_espanol`, params
  `quiere_hablar`/`voz` y el `Thread`. Quitada la dependencia `pyttsx3` de `pyproject.toml`
  (`uv sync` desinstaló pyttsx3 y sus deps graphillion/ordered-set/toolz; graphillion estaba
  vetado por CLAUDE.md). 42 tests siguen verdes.
- **Acción (decisión del usuario):** unificar logs en `logs/`. `LOGS_PATH` pasa de `.logs` a
  `logs/runtime`; el `.logs/` viejo se eliminó. `.gitignore` ignora `logs/runtime/` pero versiona
  `logs/ai_agent_changelog.md` (antes el patrón `logs/*` ocultaba la bitácora en el editor).

## 2026-06-07 — Paso 5: ruff/mypy limpios

- **Acción:** `ruff check .` → **All checks passed** (E402 resuelto moviendo los tags inline bajo
  los imports en force/geometric/phi; I001/F401/UP* con `--fix`; B904 con `raise ... from err`;
  B905 con `zip(..., strict=False)`).
- **Acción:** `mypy src` → **Success: no issues found** (32 archivos). Correcciones: `DUMMY_ARR`
  ahora `np.ndarray`; `memo` de NCube como `dict[..., tuple]`; `System.memo: dict`; `.get()` →
  indexado en geometric; anotaciones en `generar_subsistemas`/`generar_particiones` y en el dict de
  `seleccionar_emd` (`Callable[..., float]`); dos `# type: ignore` puntuales en el algoritmo
  dinámico de QNodes.
- **Verificación:** ruff + mypy limpios y **42 tests verdes**.

## 2026-06-07 — Paso 4 (rename) y Paso 6 (remote)

- **Acción (Paso 4):** nombre del proyecto a **K_QGMIP** (`pyproject.name = kqgmip`; título/intro de
  `README.md` actualizados). La reescritura completa del README es Fase 8.
- **Acción (Paso 6):** `git remote set-url origin` → `projecto-analisis-20263.git` (pull/push ahora
  referencian 20263). **No se hizo push.** Nota: la historia local diverge de la de 20263; un push
  futuro requerirá decidir merge/estrategia.

## 2026-06-07 — Docs: integrar baseline clustering + sincronizar tras reorg + evaluar Fase 0

- **Acción (a petición del usuario):** el baseline determinista de **clustering / detección de
  comunidades** (precedente oficial "Estrategia KM") solo figuraba en `PLANNING.md` Anexo A.3
  como decisión suelta; no estaba en el encabezado, §1, estructura §3, fases §4/§5, glosario §6 ni
  en `CLAUDE.md`. Integrado en todos: encabezado y tabla §1, carpeta `strategies/clustering/` en §3,
  **Fase 5 reescrita** como "Baselines comparativos" → **5A baseline clustering (REQUERIDO)** +
  **5B metaheurísticas GA/SA/Tabú (OPCIONAL)**, glosario §6, comparativa de Fase 7, y portafolio de
  estrategias + nota de stack (`scipy.sparse.csgraph`/`scikit-learn`) en `CLAUDE.md`.
- **Acción:** corregir rutas **obsoletas** en `CLAUDE.md` tras la reorg al layout oficial (Paso 1):
  `src/io/manager.py`→`src/controllers/manager.py`, `src/base/sia.py`→`src/models/base/sia.py`,
  `src/base/application.py`→`src/models/base/application.py`, `src/io/logger.py`→
  `src/middlewares/slogger.py`, `src/io/profiler.py`→`src/middlewares/profile.py`; quitado el texto
  "se reorganizará" (ya hecho) y "portar QNodes" (ya portado, 9/10). Corregido también el residuo
  `tool.coverage.omit` en `pyproject.toml` (`src/strategies/pyphi/*`→`src/controllers/strategies/phi.py`).
- **Evaluación de Fase 0 (verificada, no asumida):** DoD **cumplido**. `uv sync` ok;
  **`uv run pytest` → 42 passed**; **`ruff check .` → All checks passed**; **`mypy src` → Success
  (32 archivos)**; `data/samples/N25A.csv` existe (1.7 GB); bitácora con entradas sustantivas.
  Artefactos presentes: pyproject (deps reales + grupo dev + config ruff/mypy/pytest), `tests/`
  (regresión k=2 + triaje QNodes), QNodes corregido portado, reorg al layout oficial. **Conclusión:
  Fase 0 completa; siguiente = Fase 1 (núcleo k-genérico).**
- **IA:** la IA hizo la integración documental del baseline, la detección/corrección de rutas
  obsoletas y la verificación empírica del DoD de la Fase 0 ejecutando los gates.

## 2026-06-07 — Saneamiento del core, migración a inglés y limpieza de código muerto

- **Acción (arranque de sesión):** la base estaba **rota** en el árbol de trabajo. (1) El `.venv`
  se había creado bajo la ruta vieja `projecto-analisis-20261` → shebangs apuntaban a un Python
  inexistente (`mypy` no arrancaba); se recreó con `rm -rf .venv && uv sync --dev`. (2) Una
  migración a inglés a medio aplicar: `errors.py` renombró `ERROR_ESPACIOS_INCOMPATIBLES` →
  `ERROR_INCOMPATIBLE_SPACES` pero `system.py` seguía importando el nombre viejo (ImportError en la
  colección de pytest). Corregido el import + `W292` en `tags.py`. Tras el arreglo: **42 passed,
  ruff All checks passed, mypy Success (32 files)**.
- **Acción (validación cruzada del core — auditoría de código muerto):** barrido con `grep` de cada
  símbolo público sobre `src`/`tests`/entrypoints. **Eliminado código muerto inequívoco** (sólo
  auto-referenciado o nunca leído):
  - `labels.estados_binarios` + `dec2bin` (su único consumidor).
  - `slogger.log_execution` (decorador nunca aplicado).
  - `Manager.preparar_directorio_salida` + propiedad `output_dir` + constante `RESOLVER_PATH`.
  - `application.modo_estados` + `set_estados_activos/inactivos` + constante `ACTIVE`.
  - Ramas `as_matrix`/lista-no-generador de `generar_particiones` (todas las llamadas usan el
    generador por defecto).
  - 13 constantes sin uso en `constants/base.py` (`INFTY_NEG, FLOAT_ONE, ABC_LEN, ROWS_IDX, BITS,
    EQUIV_SYM, EQUAL_SYM, DASH_SYM, LINE_SYM, NEQ_SYM, SMALL_PHI_STR, INACTIVE, SAMPLES_PATH`).
  - **Decisión del usuario (preguntado):** *conservar* `BruteForce.analyze_full_network` + sus
    generadores (`generate_candidates/subsystems/partitions`) — produce la rejilla Excel que pide la
    Fase 7 — y la cadena `causal_emd`/`select_distance`/`hamming_distance` (métrica EMD_CAUSE opcional).
- **Acción (migración a inglés — Paso 3, antes diferido; el usuario pidió "full migration now"):**
  reescritos **todos** los archivos de `src/` + `exec.py`/`main.py`/`main_batch.py` + `tests/`:
  identificadores, docstrings y comentarios a **inglés**. Renombres transversales clave:
  `aplicacion→application` (+ atributos: `semilla_numpy→numpy_seed`, `pagina_red_muestra→
  sample_network_page`, `notacion_indexado→indexing_notation`, `tiempo_emd→emd_time`,
  `profiler_habilitado→profiler_enabled`); `aplicar_estrategia→apply_strategy`,
  `sia_preparar_subsistema→sia_prepare_subsystem`, `sia_subsistema→sia_subsystem`,
  `sia_dists_marginales→sia_marginal_dists`, `sia_tiempo_inicio→sia_start_time`;
  `System`: `condicionar→condition`, `substraer→subtract`, `bipartir→bipartition`,
  `distribucion_marginal→marginal_distribution`, `indices_ncubos→ncube_indices`,
  `dims_ncubos→ncube_dims`, `ncubos→ncubes`; `NCube`: `condicionar→condition`,
  `marginalizar→marginalize`, `indice→index`; `Solution`: `perdida→loss`,
  `tiempo_ejecucion→execution_time`, `distribucion_*→*_distribution`, `particion→partition`;
  `Manager.cargar_red→load_network`, `generar_red→generate_network`;
  `emd_efecto→effect_emd`, `emd_causal→causal_emd`, `seleccionar_emd→select_emd`,
  `literales→literals`, `reindexar→reindex`, `seleccionar_estado→select_state`,
  `fmt_biparticion(_q)→fmt_bipartition(_q)`, `gestor_perfilado→profiling_manager`;
  enums `EMD_EFECTO/EMD_CAUSA/EMD_INTEGRADA→EMD_EFFECT/EMD_CAUSE/EMD_INTEGRATED`,
  `EUCLIDIANA→EUCLIDEAN`; entrypoints `iniciar→run`; marcador pytest `triaje→triage`.
  **`condicion/alcance/mecanismo→condition/purview/mechanism`** (alineado con la terminología IIT
  que ya usaba `phi.py`).
- **Decisión (alcance de la traducción):** se traducen **identificadores + docstrings + comentarios**
  (lo que exige la rúbrica, §4.1/§4.5). Las **cadenas de salida/logs/errores se mantienen en
  español** porque la UX y los manuales (`docs/`) son en español; traducirlas desincronizaría la
  documentación. Comportamiento idéntico (las golden δ no cambian).
- **Verificación:** **42 passed**, **ruff All checks passed**, **mypy Success (32 files)**; barrido
  `grep` confirma cero referencias a identificadores en español; smoke test `uv run exec.py`
  (QNodes/N10A) imprime `Solution` correcta (φ=0.0312, UI en español).
- **Acción (docs):** actualizadas en `CLAUDE.md` las referencias de API a los nombres en inglés
  (`load_network`, `apply_strategy`, `sia_prepare_subsystem`, `condition/subtract/bipartition/
  marginal_distribution`, `application`, `generate_network`, `run`) + nota de convención de cadenas.
- **Config del repo:** el remote ya apunta a 20263 (Paso 6 previo); `.venv` recreado. Sin push
  (la historia local sigue divergiendo de 20263).
- **IA:** la IA hizo la auditoría de código muerto, la migración completa a inglés, la verificación
  por gates y la actualización documental.

## Pendiente

- Push/estrategia de merge contra 20263 (historia divergente) — decisión del usuario.
- Optimizaciones de rendimiento de GeoMIP de 20263 → Fase 6 (profiling).
- Siguiente fase funcional: **Fase 1** (núcleo de dominio k-genérico).

## 2026-06-07 (sesión de continuación) — Auditoría fresca del core migrado

- **Acción (auditoría de código muerto / malas prácticas sobre la versión en inglés):**
  barrido `grep` + lectura línea a línea de los 1745 LOC de `src/`. Confirmados los
  siguientes hallazgos (todos resueltos en esta sesión salvo donde se indica):
  - **Dead code eliminado:**
    - `GeometricSIA.labels` (inicializado, nunca leído).
    - `QNodes.labels`, `QNodes.m`, `QNodes.n`, `QNodes.purview_indices`,
      `QNodes.mechanism_indices` (declarados/Asignados, nunca leídos). También
      `vertices = list(present + future)` redundante con `phase_vertices` posterior.
    - Inicialización redundante de `GeometricSIA.transition_table[start, start]`
      con `[0.0] * n_vars` (nunca leída: `_compute_cost` la sobrescribe con
      `[None] * n_vars` y la clave `start→start` jamás se consulta).
  - **Bugs corregidos:**
    - `BruteForce.apply_strategy` usaba `set(causes.data)` / `set(effects.data)`,
      donde `.data` en un `np.ndarray` devuelve el memoryview (no los elementos);
      el resultado eran *bytes* en vez de índices. Reemplazado por
      `np.setdiff1d(causes, sub_mechanism)` (con docstring explicando el motivo).
      El bug era **latente** — solo afectaba la partición formateada para display
      en `analyze_full_network` (no en el EMD), por lo que los tests no fallaban.
    - `SafeLogger` fijaba `logger.setLevel(logging.ERROR)`, lo que silenciaba
      `debug()`/`info()` **antes** de llegar a los handlers (cuyo `setLevel(DEBUG)`
      quedaba muerto). Cambiado a `DEBUG` para que los handlers hagan el trabajo.
    - `SIA.apply_strategy` carecía de anotación de retorno `-> Solution`.
  - **Malas prácticas corregidas:**
    - `format.fmt_bipartition` usaba `+ BASE_TWO` (la constante que vale 2) como
      *padding* de ancho. Renombrada a `WIDTH_PADDING = 2` en `constants/base.py`
      y usado el nombre semánticamente correcto.
    - `format.fmt_bipartition` chequeaba `if purv_d` (truthy), que funciona
      para sets/listas pero **lanza `ValueError`** para `np.ndarray` con >1
      elementos. Cambiado a `if len(...)` para soportar uniformemente
      sets, listas, tuplas **y** numpy arrays (necesario porque ahora
      `np.setdiff1d` es el que puebla `bipart_dual`).
  - **Decisiones (lo que NO se tocó, con justificación):**
    - `Application.set_notation / set_distance / set_emd_time` están definidos
      pero no se llaman desde `src/`, `tests/` ni los entrypoints. **Se conservan**
      como API pública de configuración en runtime (coherente con `set_sample_network_page`
      y `enable_profiling`); son 3 métodos pequeños y forman la superficie de
      configuración.
    - `BruteForce.analyze_full_network` (con sus `generate_candidates` /
      `generate_subsystems`) sigue sin llamarse — sigue siendo la **rejilla Excel
      de la Fase 7**; se mantiene por acuerdo previo.
    - `phi.py` y `causal_emd / select_distance / hamming_distance` siguen
      siendo código de Fase 0 con `pyemd` opcional; sin cambios.
- **Verificación:** `uv run pytest` → **42 passed**; `uv run ruff check .` →
  **All checks passed**; `uv run mypy src` → **Success (32 files)**. Smoke test
  `uv run exec.py` (QNodes/N10A) → φ=0.0312, partición formateada correctamente
  (verifica el fix de `np.setdiff1d`); UI en español conservada.
- **IA:** la IA ejecutó la auditoría completa, aplicó las correcciones, ajustó
  `fmt_bipartition` para soportar numpy arrays, verificó los gates y
  actualizó la bitácora.

## 2026-06-07 (sesión de integración) — Cierre estricto de Fase 0 + preparación de rama en 20263

- **Acción (verificación obligatoria solicitada por el usuario):** lectura completa de
  `CLAUDE.md` y `PLANNING.md` antes de continuar trabajo de Fase 1. Decisión: **pausar Fase 1**
  hasta cerrar completamente Fase 0 e integración git.
- **Acción (DoD Fase 0, evidencias reales):**
  - `uv sync --dev` ejecutado OK.
  - `uv run pytest -q` → **42 passed**.
  - `uv run ruff check .` → **All checks passed**.
  - `uv run mypy src` → **Success (32 files)**.
  - `ls data/samples` confirma presencia de `N25A.csv` (además de N20A/N22A y datasets base).
  - bitácora (`logs/ai_agent_changelog.md`) mantenida al día.
- **Acción (saneamiento extra por criterio de calidad del usuario: no código muerto / no lógica innecesaria):**
  - `Manager`:
    - añadida resolución de samples por variable `IIT_SAMPLES_DIR` con fallback limpio a
      `data/samples` (`_resolve_samples_path`, KISS).
    - removidos `output_dir` y `preparar_directorio_salida` (código muerto: sin consumidores).
    - corregida estimación de tamaño en `generate_network` para distinguir `deterministic`
      (`int8`=1 byte) y no determinista (`float64`=8 bytes).
    - agregado guard-rail de sufijos (`Z`) para evitar bucle abierto.
  - `constants/base.py`:
    - consolidado `PATH_SAMPLES = "data/samples"` y eliminado `RESOLVER_PATH` (sin uso).
- **Verificación posterior al saneamiento:** gates nuevamente en verde
  (`pytest`/`ruff`/`mypy`, mismos resultados).
- **Estado de integración git (repo correcto):**
  - `origin` confirmado en `https://github.com/Molton321/projecto-analisis-20263.git` (fetch/push).
  - rama de trabajo actual: `claude/zen-brown-uAefq`.
  - pendiente operativo: crear rama nueva dedicada en 20263 y publicar commit consolidado.
- **IA:** la IA ejecutó la revisión completa de fase, aplicó el saneamiento KISS/DRY solicitado,
  revalidó los gates y dejó preparado el estado para el paso de integración en rama nueva.

## 2026-06-07 (Fase 1 en rama nueva) — Implementación mínima del núcleo k-genérico

- **Contexto:** el usuario autorizó continuar con Fase 1 bajo las reglas (correctitud primero,
  sin código innecesario, KISS/DRY/SOLID).
- **Acción (modelo de dominio):** añadido `src/models/core/partition.py` con clase `KPartition`
  validada y documentada:
  - normalización canónica de bloques,
  - validaciones de disjunción/cobertura/no-vacuidad,
  - firma determinista (`signature`) para memoización,
  - constructor `from_blocks(...)` con entradas array-like.
- **Acción (core):** añadido `System.k_partition(partition: KPartition)` en
  `src/models/core/system.py` para reconstrucción de subsistema particionado por bloques k,
  con validación explícita de universos presente/futuro.
- **Acción (métrica):** añadido `delta_k(...)` en `src/funcs/emd.py`:
  `δ_k = EMD(P(subsystem), P(partitioned_subsystem))`, retornando `(loss, partition_distribution)`.
- **Acción (tests nuevos):**
  - `tests/unit/test_kpartition_validation.py` (validez estructural y canonicidad);
  - `tests/unit/test_delta_k_k2_equivalence.py` (regresión de equivalencia k=2 vs `bipartition`
    legacy en N2A/N3A/N4A, 10 particiones no triviales por red).
- **Acción (export core):** `src/models/core/__init__.py` ahora exporta `KPartition`.
- **Parámetros reales de validación:**
  - `uv run pytest -q` → **49 passed**;
  - `uv run ruff check .` → **All checks passed**;
  - `uv run mypy src` → **Success: no issues found in 33 source files**.
- **IA:** la IA implementó la capa mínima de Fase 1, diseñó/ejecutó pruebas de regresión k=2 y
  verificó calidad con gates completos.
