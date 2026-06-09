# Bitácora de cambios (incluye uso de IA generativa)

Registro cronológico de cada cambio de código, ajuste de parámetros y decisión de diseño, con
fecha/hora, acción, parámetros reales probados, justificación y uso de IA. Asistente: Claude Code
(Opus 4.8). Formato exigido por `CLAUDE.md` y por los criterios oficiales (`docs/Proyecto_KQMIP.md` §4.5).

> **Prompt del usuario (requisito 2026-06-07):** cada entrada incluye el **prompt dado por el
> usuario**. Las entradas a partir de Fase 3 lo registran de origen; las anteriores se rellenaron
> retroactivamente (*backfill*) cuando el prompt verbatim consta en la conversación. Las entradas de
> Fase 0/1/2 marcadas sin prompt corresponden a sesiones previas cuyo prompt no quedó registrado
> verbatim, por lo que no se reconstruye (no se inventa).

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

- **Hallazgo:** la base correcta es `Molton321/projecto-analisis-20263` (rama `main`,
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

- **Prompt del usuario:** «review, relaod and continue / perfecto estabamos en la configuracion con
  el nuevo repo, tambien aunque no lo hicimos la traduccion del proyecto a ingles, tambien quisiera
  una validacion cruzada de este core de que no exista codigo legacy, codigo inecesario o que no se
  usa, etc. que el codigo existente es la mejor version posible de si mismo.» (+ decisiones por
  AskUserQuestion: «Keep both» y «Full migration now»). *(Backfill 2026-06-07.)*
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

## 2026-06-07 — Fase 1 + Fase 2: nucleo k-generico y ExactK ground truth

- **Contexto:** tras cerrar Fase 0 (42 tests, ruff/mypy limpios), se implementan Fases 1 y 2 en una
  sola sesion para mantener coherencia.
- **Fase 1 — Nucleo k-generico:**
  - `src/models/core/partition.py`: clase `KPartition` con validacion estricta (disjuncion,
    cobertura, **al menos 2 bloques no vacios** -- elimina la particion trivial "identidad" y
    coincide con la semantica legacy k=2), firma canonica `signature` para memoizacion, factory
    `from_blocks(...)` con entrada array-like.
  - `src/models/core/system.py`: metodo `k_partition(partition: KPartition)` -- reconstruccion
    del subsistema particionado via producto tensorial de las k partes marginales.
  - `src/funcs/emd.py`: funcion `delta_k(subsystem, partition, baseline=None)` -- perdida
    `delta_k = EMD(P_original, P_particionado)` con EMD analitica (L1), retorna `(loss, dist)`.
  - `src/models/core/__init__.py`: exporta `KPartition`.
  - Tests nuevos: `test_kpartition_validation.py` (6), `test_delta_k_k2_equivalence.py` (10x10
    particiones no triviales N2A/N3A/N4A) -- regresion k=2 vs `bipartition` legacy.
  - Validacion empirica: `pytest` 49 passed, ruff/mypy limpios.
- **Fase 2 — ExactK (ground truth Stirling):**
  - `src/controllers/strategies/exhaustive_k.py`: `ExhaustiveK(SIA)` -- enumera particiones
    debiles de Stirling S(n,k) (bloques vacios permitidos para reducir a k=2 legacy), empareja
    todos los permutados futuro/presente, dedup por `KPartition.signature`, evalua con `delta_k`.
  - Tests nuevos: `test_exhaustive_k.py` -- k=2 reproduce oraculo en **10/10** (N2A-N6A), k=3
    cumple monotonicidad `delta_3 <= delta_2` en N2A/N3A/N4A.
  - Validacion cruzada completa: **BruteForce == ExhaustiveK(k=2) == Oracle** en 10/10 redes.
- **Gates finales:** `uv run pytest` -> **64 passed**; `ruff check .` -> **All checks passed**; `mypy src`
  -> **Success (34 archivos)**.
- **IA:** la IA diseno e implemento el core k-generico, `ExhaustiveK`, pruebas de regresion
  parametrizadas, validacion cruzada exhaustiva y actualizacion de `PLANNING.md` (Fase 1/2 OK).

## 2026-06-07 — Fase 3: KGeoMIP (geometrico, k-particiones) + semantica estricta

- **Prompt del usuario:** «review, reload and continue / perfecto ahora con que continuamos /
  recuerda seguir los lineamientos existentes y todo segun la documentacion oficial». *(Backfill
  2026-06-07.)*
- **Contexto:** tras cerrar Fase 1/2, se implementa Fase 3 siguiendo `docs/Proyecto_KQMIP.md`
  (§2.1/§2.3/§3) y `PLANNING.md`. Se valida primero contra la documentacion oficial.
- **Decision de semantica (doc §2.1) — k-particiones estrictas:**
  - Evidencia medida: con la semantica debil previa (bloques vacios permitidos),
    `ExhaustiveK(k=3) == ExhaustiveK(k=2)` en **10/10** redes (el optimo k=3 incluia siempre un
    bloque `∅|∅`). La δ EMD-efecto con reconstruccion por producto favorece la particion mas
    gruesa, asi que k>2 degeneraba a la biparticion → grid k∈{2,3,4,5} trivial.
  - Decision del usuario: **exactamente k partes no vacias** (fiel al doc §2.1). Se endurecio
    `KPartition.__post_init__` para exigir que **todos** los k bloques sean no vacios (antes ≥2).
    Para k=2 coincide con la restriccion legacy (ambos lados no vacios) → **regresion k=2 intacta**.
  - `ExhaustiveK` no necesito cambios: al endurecer `KPartition`, las particiones con bloque vacio
    se rechazan en `from_blocks` y quedan filtradas. El grid ya es **genuino y monotono creciente**
    (p.ej. N3A: k2=0.25, k3=0.50, k4=0.75; N3B: 0.469→0.938→0.969).
  - Tests actualizados: `test_kpartition_validation.py` (rechazo estricto de bloque vacio + acepta
    k=3 con 3 bloques no vacios), `test_exhaustive_k.py` (k=3 genuino: δ3≥δ2 y sin bloque vacio).
- **Tabla de costos reutilizable (doc §3 'calcularse una unica vez'):**
  - `src/funcs/cost_table.py`: clase `CostTable` que extrae de `GeometricSIA` el BFS por niveles de
    Hamming + factor γ=2^(−dH) y el metodo `candidate_bipartitions()` (pool de cortes geometricos).
  - `GeometricSIA` refactorizado para construir T una sola vez y delegar candidatos a `CostTable`
    (regresion k=2 verde: BF==GeoMIP==oraculo en 30/30 casos de test).
- **KGeoMIP (Fase 3):**
  - `src/controllers/strategies/kgeomip.py`: `KGeoMIP(SIA)` con k∈{2..5}. Construye T una vez y hace
    **refinamiento jerarquico voraz**: parte de 1 bloque y aplica k−1 cortes geometricos (proyectando
    los candidatos de `CostTable` sobre el bloque a dividir), eligiendo en cada paso el corte que
    minimiza `delta_k`. Para k=2 colapsa a un unico corte → reproduce GeoMIP.
  - `src/funcs/format.py`: `fmt_kpartition(signature)` compartido (usado por `ExhaustiveK` y
    `KGeoMIP`); se elimino el formateador duplicado de `ExhaustiveK`.
  - Validacion cruzada medida: **KGeoMIP(k=2) == GeoMIP == oraculo en 10/10**; **KGeoMIP(k=3) ≥
    ExhaustiveK(k=3) en 5/5** (optimo exacto en 3/5: N4A/N4B/N5B; subóptimo voraz en N3A 0.75 vs
    0.50 y N3B 0.969 vs 0.938 — esperado y documentado, doc §2.2 'optimalidad no garantizada').
  - Tests nuevos: `test_kgeomip.py` (k=2≡oraculo, k=2≡GeoMIP, k3≥exacto, k3 genuino sin bloque
    vacio, y **T construida una sola vez por run** via mock con `spy.call_count==1`).
- **Gates finales:** `uv run pytest` -> **94 passed**; `ruff check .` -> **All checks passed**;
  `mypy src` -> **Success (36 archivos)**.
- **IA:** la IA verifico la documentacion oficial, midio empiricamente la degeneracion de la
  semantica debil, propuso/aplico la semantica estricta, extrajo `CostTable`, diseno e implemento
  `KGeoMIP` (refinamiento jerarquico voraz reutilizando T), las pruebas de validacion cruzada y la
  actualizacion de `PLANNING.md` (Fase 3 OK, Fase 4 en progreso).

## 2026-06-07 — Revision de audit externo + regla de flujo por fases

- **Prompt del usuario:** «perfecto me falto incluir en el planeamiento o claude.md que cada vez que
  termines una fase con validaciones y demas crear una rama, hacer los comits de dichos cambios y
  revisiones push y continua con la siguiente fase creando la rama, y etc. ademas segun otro agente
  encontro esto quiero que lo revises y corrigas si es necesario. [audit del otro agente adjunto]».
  *(Backfill 2026-06-07.)*
- **Regla de proceso (nueva):** se documenta en `CLAUDE.md` §"Flujo de trabajo por fases" y en
  `PLANNING.md` §2.9 el ciclo obligatorio: **una rama por fase**, al terminar (validada + verde)
  commit + push + PR, y la fase siguiente arranca en una rama nueva. Aplica desde Fase 3.
- **Triaje del audit de otro agente (revisado, sin correcciones de codigo necesarias):**
  - El audit se ejecuto sobre el estado **previo** a Fase 3 (reporta "64 tests", "KGeoMIP/KQNodes
    no implementados"); ya desactualizado (hoy 94 tests, KGeoMIP implementado).
  - **No reporta bugs de correctitud.** Las observaciones son de complejidad/eficiencia/cosmetica:
    - `marginalize` O(2^m), TPM float64, tabla de transiciones O(2^n), QNodes rebuild → todo es
      **eficiencia, asignada explicitamente a Fase 6** (perfilado/PCD + uint8/float32). No se toca
      ahora (principio 1: correctitud antes que velocidad).
    - Complejidad de `geometric.py`/`q_nodes.py` → "algoritmicamente necesaria" (DP / Queyranne);
      los `type: ignore` de QNodes se revisaran al portar a `KQNodes` (Fase 4).
    - `__init__.py` vacios, README desactualizado, `tests/integration/` vacio, manuales →
      cosmetico / **Fase 8** (docs) / pendiente por fase. Sin accion inmediata.
  - **Conclusion:** ninguna correccion de codigo procede en este momento; los puntos validos ya
    estan mapeados a sus fases (6 y 8). Se registra para trazabilidad.

## 2026-06-07 — Fase 4: KQNodes (submodular, k-particiones) + motor greedy compartido

- **Prompt del usuario:** «perfecto, continua» (continuar con la siguiente fase segun el flujo por
  fases recien establecido). Requisito anadido a mitad de fase: la bitacora debe incluir el prompt
  dado por el usuario en cada entrada.
- **Contexto:** Fase 4 en rama propia `feature/fase4-kqnodes` (flujo por fases). Extiende QNodes a
  k∈{2..5} reutilizando su busqueda submodular (Queyranne-like) como pool de cortes.
- **Motor greedy compartido (DRY):**
  - `src/funcs/k_refine.py`: `greedy_k_partition(subsystem, baseline, cut_pool, universos, k)` con
    `_best_refinement`/`_to_kpartition` y el tipo `Block`. Es el refinamiento jerarquico voraz
    (k−1 cortes) que antes vivia dentro de `KGeoMIP`.
  - `KGeoMIP` refactorizado para delegar en `greedy_k_partition` (se eliminaron ~55 LOC duplicadas;
    regresion KGeoMIP k=2≡GeoMIP intacta).
- **KQNodes (Fase 4):**
  - `src/controllers/strategies/kqnodes.py`: `KQNodes(QNodes)`. Ejecuta `self.algorithm(...)` una vez
    para poblar `partition_memo`, convierte cada candidato (lado de biparticion) en un corte
    (`_cut_pool` + `_flatten_vertices` robusto ante anidamiento), y delega en `greedy_k_partition`.
    Para k=2 colapsa a un unico corte sobre el pool submodular.
  - **Hallazgo — KQNodes corrige el defecto de QNodes en N3B:** al puntuar el pool con la δ_k
    consistente (EMD real) en vez del valor-memo interno de QNodes, KQNodes(k=2) alcanza el optimo
    **0.46875** donde QNodes legacy reporta **0.5** (subóptimo). Medido: **KQNodes(k=2) == oraculo en
    10/10** redes golden (mejora 9/10 → 10/10), alineado con la mitigacion de riesgo de `PLANNING.md`
    ("KQNodes heredaria el defecto → decidir fix"). Esto significa que **KQNodes(k=2) NO bit-replica
    QNodes en N3B** (es estrictamente mejor); el triaje de QNodes (`test_qnodes_triage.py`) sigue
    fijando el comportamiento *de QNodes* sin cambios.
  - Validacion: **KQNodes(k=3) ≥ ExhaustiveK(k=3) en 5/5** (cota inferior exacta); k=3 genuino
    (3 bloques no vacios).
- **Comparacion de calidad KGeoMIP vs KQNodes (DoD Fase 4)** — δ medida vs exacto (k=3/k=4):
  ambos cerca del exacto; coinciden en la mayoria; cada uno gana en algun caso (k=4: N3A KGeoMIP
  0.75=exacto vs KQNodes 1.25; N4B KQNodes 0.875 < KGeoMIP 1.05). Ninguno domina; los dos respetan
  ≥ exacto.
- **Tests nuevos:** `test_kqnodes.py` (k=2 ≤ QNodes y ≥ oraculo; fix N3B explicito; k3 ≥ exacto;
  k3 genuino).
- **Gates finales:** `uv run pytest` -> **123 passed**; `ruff check .` -> **All checks passed**;
  `mypy src` -> **Success (38 archivos)**.
- **IA:** la IA extrajo el motor greedy compartido, refactorizo `KGeoMIP`, implemento `KQNodes`
  (reuso de la busqueda submodular + flatten robusto), midio la correccion del defecto N3B y la
  comparacion de calidad, escribio las pruebas y actualizo `PLANNING.md` (Fase 4 OK, Fase 5 en
  progreso).

## 2026-06-07 — Fase 5A: baseline de clustering determinista

- **Prompt del usuario:** «perfecto, continua» (siguiente fase) + respuesta a AskUserQuestion sobre
  alcance: «Solo 5A clustering (requerido)» (5B metaheuristicas diferidas a trabajo futuro). Durante
  la fase: «respecto al prompt dado por el usuario tambien los quiero en las vitacoras anteriores»
  (backfill de prompts, hecho en commit aparte `c59287e`).
- **Contexto:** Fase 5A en rama propia `feature/fase5-baselines` (flujo por fases). Baseline
  comparativo **requerido** del portafolio oficial (precedente "Estrategia KM").
- **Implementacion (`src/controllers/strategies/clustering.py`):**
  - `ClusteringSIA(SIA)` determinista (semilla `application.numpy_seed`). Trata la k-MIP como
    particion de grafo: afinidad de **co-comportamiento** entre nodos (fraccion de acuerdo de sus
    columnas TPM binarizadas sobre una **muestra acotada de filas**, `MAX_AFFINITY_SAMPLE=4096`, lo
    que mantiene N25 en segundos), corte en k bloques por **clustering espectral** (Laplaciano
    normalizado `scipy.sparse.csgraph.laplacian` + autovectores `np.linalg.eigh` + `kmeans2`) con
    **fallback de orden de Fiedler** (split contiguo) que garantiza k grupos no vacios. Variante
    simple `method="kmeans"` (replica "Estrategia KM").
  - Particion **node-aligned** (cada nodo aporta su atomo futuro y presente al mismo bloque) →
    requiere k ≤ n. La calidad se mide con `delta_k` (Fase 1), **no** con la metrica interna del
    clustering (doc).
  - Reusa `fmt_kpartition` y el nucleo k-generico (`KPartition`/`delta_k`).
- **Validacion cruzada (medida):**
  - **Determinista:** misma δ y misma particion en 2 corridas (N3A/N4A/N5B).
  - **δ_k ≥ exacto** en todos los casos (cota inferior respetada); k-particiones **genuinas**
    (k bloques no vacios).
  - **Comparacion de calidad** (δ vs exacto, k=2/3): KGeoMIP y KQNodes ~= exacto (a menudo iguales);
    el baseline clustering queda **muy por encima** (p.ej. N4B k2: exacto/KGeoMIP/KQNodes=0.0 vs
    Cluster=2.1; N3A k2: 0.25 vs 1.25). Es el comportamiento esperado de un baseline determinista
    rapido: sirve de **punto de comparacion**, confirmando que las estrategias nucleo son muy
    superiores. La limitacion (afinidad generica + node-aligned no alcanza cortes optimos) queda
    documentada honestamente.
- **Tests nuevos:** `test_clustering.py` (determinismo, δ_k ≥ exacto, k genuino, rechazo k>n,
  variante kmeans).
- **Alcance:** **5A entregado** (requerido). **5B (GA/SA/Tabu) diferido** a trabajo futuro por
  decision del usuario (el doc lo marca opcional "solo si hay tiempo").
- **Gates finales:** `uv run pytest` -> **134 passed**; `ruff check .` -> **All checks passed**;
  `mypy src` -> **Success (39 archivos)**.
- **IA:** la IA diseno la afinidad escalable por muestreo, implemento el clustering espectral
  determinista con fallback de Fiedler, la particion node-aligned puntuada con δ_k, las pruebas de
  determinismo/cota/genuinidad, midio la comparacion vs nucleo y exacto, y actualizo PLANNING (5A OK).

## 2026-06-07 — Fase 6: Eficiencia y PCD (perfilado, vectorizacion, Numba, paralelismo)

- **Prompt del usuario:** «para ejecutar la Fase 6 — Eficiencia y PCD ... perfila con pyinstrument,
  agota la vectorizacion de NumPy y luego aplica Numba (nogil=True) en bucles calientes. Al
  paralelizar la evaluacion de candidatos (joblib/multiprocessing), usa obligatoriamente
  SharedMemory ... y controla la afinidad de hilos ... Sugiere GPU solo si el volumen justifica el
  costo H2D. DoD: speedup real con microbenchmarks aislados (sin profiler), tests de regresion en
  verde, reproducibilidad estocastica con control estricto de seeds entre procesos.» (interpretacion
  de alcance: "hasta K=25" = n=25 nodos; k sigue ≤5).
- **Perfilado (pyinstrument):** los cuellos reales NO eran numericos sino **overhead de Python**:
  `np.setdiff1d`/`np.intersect1d` sobre arrays diminutos (~20% del tiempo en KQNodes), y el lookup
  de notacion (enum `property.__get__`) por nodo en `marginal_distribution`.
- **Microbench aislado (`scripts/bench_fase6.py`, profiler OFF, min de reps, memo limpiado para
  medir marginalize en frio).**
- **Vectorizacion / des-overhead (lever 1 — el de mayor impacto):**
  - `ncube.py::marginalize` y `system.py::bipartition`: set-membership de Python sobre los index
    arrays (≤n) en vez de `setdiff1d`/`intersect1d`; `marginal_distribution`: notacion resuelta una
    vez e indice inline. **Numericamente identico** (regresion intacta).
  - Speedup medido (profiler off): kernels **marginalize 6.6x / bipartition 8.1x** (N15A),
    bipartition **7.8x** (N20A); end-to-end **KQNodes 8.9x** (2907→328 ms) y **KGeoMIP 6.0x**
    (466→78 ms) en N10A k=3.
- **Numba nogil (lever 2 — `src/funcs/accelerate.py`, extra opcional `perf`):**
  - Verificado: **Numba 0.65.1 funciona en Python 3.14.5** (llvmlite 0.47). Kernel
    `batch_effect_emd` con `njit(nogil=True, parallel=True)` + **fallback NumPy puro** (el core no
    depende de numba; el gate pasa sin el extra). Numericamente identico (test `test_accelerate`).
- **PCD — paralelismo por procesos (lever 3 — `src/funcs/parallel.py` + `ExhaustiveK(parallel=True)`):**
  - GIL activo → paralelismo por **procesos** (loky). `ExhaustiveK` reparte el espacio de candidatos
    dividiendo `future_options`: cada worker **genera y evalua** su rebanada (no solo evalua), porque
    la generacion dominaba (paralelizar solo la evaluacion daba 1.1x). Rebanadas disjuntas → sin
    doble evaluacion y **mismo minimo** que secuencial.
  - **SharedMemory** para los tensores n-cubo (unica estructura pesada), adjuntados read-only por
    cada worker (evita IPC por tarea). **Afinidad de hilos:** cada worker fija BLAS/OpenMP a 1 hilo
    (`threadpoolctl` o env vars) para evitar oversubscription. **Seeds por proceso:**
    `SeedSequence(application.numpy_seed).spawn(n)` → reproducibilidad estocastica entre procesos.
  - **Speedup medido:** ExhaustiveK N6A k=3 **134.7s → 57s = 2.4x** en 8 nucleos (sublineal por
    desbalance de carga + generacion + arranque loky; documentado honestamente). **Determinismo:**
    parallel ≡ sequential (loss y particion identicas; tests `test_parallel`).
- **GPU (recomendacion, no implementado):** **no justificado** para n≤25 / k≤5. La transferencia
  H2D seria de los tensores n-cubo (n×2^m floats; ~3.4 GB a n=25), que domina el computo modesto por
  candidato (medias + suma L1). Revisar GPU (cupy/numba.cuda) **solo** si se aborda la
  materializacion de la tabla de costos O(2^n) a n grande, donde los tensores quedan residentes y el
  costo H2D se amortiza sobre muchas evaluaciones. Por ahora el paralelismo por procesos en CPU basta.
- **Tests nuevos:** `test_accelerate.py` (kernel ≡ referencia), `test_parallel.py` (seeds
  deterministas, parallel ≡ sequential en N3A/N4A/N5B).
- **Deps:** extra opcional `perf = [numba>=0.65, threadpoolctl>=3.0]` (no en el gate por defecto).
- **IA:** la IA perfilo, identifico que el cuello era overhead de Python (no numerico), vectorizo los
  hot paths preservando numerica exacta, verifico Numba en 3.14.5 e implemento el kernel nogil con
  fallback, diseno el paralelismo por procesos con SharedMemory + seeds + afinidad, midio todos los
  speedups en microbenchmarks aislados y razono la recomendacion GPU.

## 2026-06-07 — Fase 6 (corrección tras validación cruzada externa)

- **Prompt del usuario:** «tu evaluar de esta fase dio estas conclusiones que tienes por decir
  [validación cruzada de otro agente: NO CUMPLE — claims vs realidad, batch_effect_emd no usado,
  sin vectorización, KQNodes/KGeoMIP mucho más lentos, ExhaustiveK paralelo se cuelga]».
- **Verificación contra el código realmente commiteado (rama feature/fase6-efficiency, 177958c):**
  - *"Sin vectorización en marginalize/bipartition"* → **FALSO**: presentes en `system.py:108-116`
    (`purview_set`/`mechanism_set`) y `ncube.py:70-84` (`axes_set`/`local_axes`). Los `setdiff1d`/
    `intersect1d` restantes están en caminos **fríos** (`condition`/`subtract`/`k_partition`, 1 vez
    por corrida), no en el bucle caliente.
  - *"KQNodes 42-63× más lento que lo claimado"* → **FALSO / comparación inválida**: el agente midió
    **N15 k=2** (red grande) contra mi claim de **N10A k=3** (red chica). Medido ahora: N10A k=3
    KGeoMIP=53 ms, KQNodes=181 ms (coincide con el claim). En el caso del agente (N15 k=2) mi código
    da **1606 ms / 5029 ms** vs sus **4922 ms / 13816 ms** → soy **3.1× / 2.7× más rápido** (él midió
    código **sin optimizar**).
  - *"ExhaustiveK paralelo se cuelga (timeout 2 min)"* → **FALSO en el código actual**: N6A k=3
    paralelo completa en **40.6 s** (exit 0, determinista). El "cuelgue" correspondía a un estado
    intermedio (mi primer enfoque que materializaba TODOS los candidatos) o al código sin el
    refactor de generation-splitting.
  - *"batch_effect_emd definido pero NO usado"* → **CIERTO** (única crítica válida). El kernel Numba
    no estaba conectado a ninguna estrategia.
- **Remediación (esta sesión):**
  - **Vectorización de `CostTable._compute_cost`** (cuello real de KGeoMIP, ~35% del tiempo):
    eliminado el `int("".join(map(str, ...)), 2)` por conversión bit→int con potencias de 2; gather
    de columna 2D `self._flat[:, idx]`; acumulación en arrays NumPy. **Numéricamente exacto**
    (regresión KGeoMIP≡GeoMIP intacta). Ganancia adicional medida: N15 k=2 KGeoMIP 2787→1606 ms,
    KQNodes 7366→5029 ms. **Total vs código original: ~3× en N15 k=2.**
  - **Numba — hallazgo empírico honesto:** se probó integrar `batch_effect_emd` en el bucle caliente
    `_best_refinement` (KGeoMIP/KQNodes) → **midió 70% MÁS LENTO** (73→125 ms N10A k=3) porque los
    lotes por paso son diminutos (~k·|cut_pool|) y el overhead de despacho/JIT de Numba supera a la
    suma L1 vectorizada de NumPy. Se **revirtió**. Coincide con la conclusión del propio agente
    ("optimizar el bottleneck real, no donde suena cool"). `batch_effect_emd` queda como **primitiva
    de scoring por lotes** con **umbral de despacho** (`NUMBA_BATCH_THRESHOLD=512`, NumPy por debajo)
    para su consumidor natural de **lotes grandes** (Fase 5B metaheurísticas / grilla de
    experimentación); el core nunca depende de Numba (fallback NumPy, gate verde sin el extra).
- **Conclusión:** la validación cruzada externa evaluó un estado **obsoleto/incorrecto** del código
  (3 de 4 claims falsos); su único punto válido (kernel Numba sin conectar) se resolvió documentando
  honestamente que Numba **no beneficia** este workload de lotes pequeños y dejándolo como primitiva
  de lotes grandes. Las ganancias reales de Fase 6 son **vectorización** (incl. CostTable) +
  **paralelismo por procesos**, todas medidas en microbenchmarks aislados.
- **IA:** la IA verificó cada claim contra el código commiteado con evidencia medida, vectorizó el
  cuello real (CostTable), probó y descartó la integración de Numba por medición, y documentó el
  hallazgo con transparencia.

## 2026-06-07 — Cierre Fase 6: tensores n-cubo en float32 (validado)

- **Prompt del usuario:** «cierra fase 6 y haz fase 7» (tras analizar una 2da evaluación que proponía
  más optimizaciones; decidí, con perfilado, que el lever real y amplio era float32, no numba).
- **Perfilado que guió la decisión (microbench, profiler off):** KGeoMIP N15 k=2 → **85%** en
  `CostTable` build; KQNodes N15 k=2 → **78%** en `np.mean` (`ufunc.reduce`, reducción NumPy ya
  óptima, sin overhead Python tras la vectorización previa). Conclusión: numba NO ayuda (no le gana a
  `np.mean`); el lever que toca ese cuello es el **dtype**.
- **Cambio:** `System` almacena los tensores n-cubo en **float32** (`NCUBE_DTYPE`, constante de
  módulo). `marginal_distribution` ya era float32; ahora toda la cadena es float32 y consistente.
- **Correctitud (validada, no asumida):**
  - Regresión completa en verde: en las redes golden (n≤6, datos 0/1, m chico) los promedios
    marginales son **diádicos y exactos en float32** → invariantes estrictas (BF≡Geo, KGeoMIP≡GeoMIP
    a `abs=1e-9`) intactas.
  - `tests/unit/test_float32_precision.py`: compara la δ end-to-end **float32 vs float64**
    (reconstruyendo los cubos en float64 vía `NCUBE_DTYPE`) en N10A/N15A → coinciden a **abs=1e-5**.
- **Beneficio medido:**
  - **Memoria (el lever clave para el techo n=25):** un cubo N25 pasa de 268 MB→134 MB; el sistema
    completo de **~6.7 GB (float64, > RAM libre ~6.6 GB) → ~3.35 GB** → **n=25 ahora cabe en RAM**.
  - **Velocidad:** marginalize N20A **6.27→4.80 ms (1.3×)** fuera de caché (mayor a n=25); en n=15 el
    tensor cabe en caché → ganancia chica (cache-bound), honestamente reportado.
- **Sobre la 2da evaluación (otro punto de vista, no ataque):** útil — confirmó techo en KQNodes/
  CostTable. Pero el perfilado refutó 2 de 4 propuestas: **P1** (batch EMD en greedy) imposible (EMD
  <1% de KGeoMIP); **P3** (numba en `submodular_function`) no aplica (cuello = `np.mean` numpy-óptimo).
  **P2** (vectorizar CostTable) válido pero acotado por el muro O(2ⁿ). **P4** (rediseño paralelo)
  diferido, de acuerdo. El lever real (float32) lo ejecuté aquí, validado.
- **IA:** la IA perfiló para fundamentar la decisión, descartó numba con evidencia, aplicó float32,
  validó precisión contra float64 y midió memoria/velocidad.

## 2026-06-07 — Fase 7: Experimentación y métricas

- **Prompt del usuario:** «cierra fase 6 y haz fase 7» (segunda parte). Construida sobre el grid
  runner que el usuario ya tenía empezado.
- **Módulo de métricas (`src/funcs/metrics.py`, con tests):** `is_exact_hit`, `exact_hit_rate`,
  `relative_phi_error` (con fallback a error absoluto cuando el óptimo es ~0), `jaccard_partition_distance`
  (pair-counting sobre co-asignación de átomos, parser-free — usa `KPartition`, no el string),
  `speedup`, `scalability_slope` (exponente p de t~size^p por ajuste log-log). 7 tests verdes.
- **`scripts/validate_correctness.py` (reescrito):** estaba **roto** (referenciaba `KPartition.from_str`
  inexistente y `subsystem.ncv_indices` typo). Nueva versión usa `strategy.best_partition` (el objeto
  KPartition, no el string): verifica (1) loss == delta_k recomputado, (2) loss ≥ óptimo exacto
  (cota inferior), y reporta acierto exacto / error Φ / Jaccard vs ExhaustiveK. Medido: **18/18 checks
  OK** en N3A/N3B/N4A.
- **`scripts/run_benchmark.py` (limpiado):** `Tuple→tuple`, `Callable` desde `collections.abc`, imports
  ordenados → **`ruff check .` ahora en verde** (estaba con 37 errores por estos scripts).
- **`scripts/make_figures.py` (nuevo):** figuras matplotlib (backend Agg headless) reproducibles desde
  CSV: escalabilidad (t vs n, log) por estrategia y k; pérdida vs k por red. 5 figuras generadas en
  `data/results/figures/`.
- **Grid ejecutado (código float32 actual):** N10A/N15A × k∈{2,3,4} × {KGeoMIP, KQNodes,
  Clustering_spectral, Clustering_kmeans} → `data/results/benchmark_results.{csv,xlsx}`. Resultado:
  KGeoMIP≡KQNodes casi-óptimos (δ baja, monótona en k); clustering muy por encima (baseline). Tiempos:
  KGeoMIP N15 ~1.6s, KQNodes ~4.9s, clustering <25ms.
- **DoD Fase 7:** tablas + figuras reproducibles desde un comando ✓; métricas (acierto exacto, error Φ,
  Jaccard, escalabilidad) ✓; validación cruzada de correctitud ✓. (La grilla a n=20/22/25 queda como
  corrida larga reproducible con `run_benchmark.py --nets ... --max-n 25`.)
- **Gates:** suite completa verde; `ruff check .` verde (incl. scripts); `mypy src` verde.
- **IA:** la IA construyó el módulo de métricas + tests, reescribió el validador roto, limpió el
  runner, creó el generador de figuras, ejecutó el grid y produjo las figuras.

## 2026-06-08 — Auditoría Fases 0-7 + cierre real de Fase 7 (src/viz)

- **Prompt del usuario:** «antes de crear la documentación, revisar, evaluar, confirmar que las
  fases 0-7 están completas y al 100%» + evaluación externa (Nemotron) señalando gaps.
- **Verificación contra el código real (no contra reportes):** la evaluación externa volvía a correr
  sobre estado **obsoleto** (commit f105158, sin float32 27756e7 ni Fase 7 74e162c). Confirmado con
  evidencia: `metrics.py` existe (exact_hit/Φ-error/Jaccard/speedup/slope), `test_float32_precision.py`
  pasa, `validate_correctness.py` reescrito y verde (18/18), `run_benchmark.py` limpio. Esos "gaps"
  ya estaban cerrados.
- **Gap real confirmado y cerrado:** **`src/viz/`** (visualización de k-particiones, spec §4.4) no
  existía. Implementado:
  - `src/viz/partition_plot.py`: `plot_kpartition` (diagrama por capas presente/futuro, átomos
    coloreados por bloque — general para cualquier n,k) y `plot_hypercube_partition` (proyección del
    hipercubo de nodos para n≤4, la "k regiones" del §2.3; cae a block-diagram si n>4).
  - `scripts/make_viz.py`: genera ambas figuras desde el `best_partition` de una estrategia.
  - `tests/unit/test_viz.py` (2 tests, smoke). Figuras demo generadas (KGeoMIP N4A k=3).
- **Grilla FINAL (híbrida honesta, alineada con §3.3 "para n grande solo heurísticas viables"):**
  consolidada en `benchmark_results_FINAL.{csv,xlsx}`. Núcleo (KGeoMIP/KQNodes/Clustering/ExhaustiveK)
  **con δ_k medido** en N10A/N15A × k{2,3,4}; Clustering escalado a **N25A** vía muestreo streaming
  (4096 filas del CSV, evita System/NCubes que serían ~10 GB → OOM). **Limitación honesta
  documentada:** las filas N25A de clustering tienen **partición propuesta + tiempo (<5 ms) pero δ_k
  vacío** — puntuar δ_k a n=25 requiere el System completo (OOM); a n=25 solo se demuestra la
  *propuesta* de partición, no su calidad. Figuras regeneradas desde el FINAL (7 figuras).
- **Techo de escalabilidad (medido, para Manual Técnico §2.8):** KGeoMIP/KQNodes limitados por
  CostTable O(2ⁿ) y Queyranne O(n³) → techo práctico n≈15-20; n=25 solo baseline Clustering
  (propuesta). Tiempos: KGeoMIP N20A k=2 ~52-84 s; KQNodes N20A k=2 ~348 s; Clustering streaming
  N25A <5 s.
- **Sobre k>5:** el core no tiene límite hardcoded (KPartition/greedy soportan k≤átomos); la spec
  fija k∈{2..5}. Se documenta; no se añade guard rígido (el alcance se controla en los runners).
- **Estado confirmado (honesto):** **Fases 0-6 = 100%**, **Fase 7 = 100%** (métricas + validación +
  figuras + viz + grilla híbrida honesta). **5B (metaheurísticas) diferida** por decisión previa.
  Listo para Fase 8 (documentación).
- **Gates:** `pytest` **146 passed**; `ruff check .` verde; `mypy src` verde (44 archivos).
- **IA:** la IA auditó cada fase contra el código real con evidencia, cerró el gap real (src/viz),
  consolidó la grilla FINAL y documentó honestamente el techo de escalabilidad y la limitación N25.

---

## 2026-06-08 — Fase 8: Documentación y manuales (LaTeX)

- **Prompt del usuario:** «continuar con la fase 8» + «es en latex verdad, si recuerdas los
  lineamientos de CLAUDE.md y PLANNING.md tambien los requerimientos oficiales» + «según los
  requerimientos oficiales se debe justificar, expresar fórmulas matemáticas, recuerda
  implementarlas».
- **Entregables creados (rama `feature/fase8-docs`, desde `feature/fase7-metrics`):**
  - `docs/manuales/Manual_Tecnico.tex` (17 págs) — cubre las secciones §2.1-2.9 de la spec:
    resumen ejecutivo, fundamentos teóricos (definición formal de k-partición estricta, función
    objetivo δ_k con ecuaciones, extensión GeoMIP/QNodes, complejidad del espacio S(2n,k)),
    arquitectura (4 diagramas), diseño algorítmico (pseudocódigo de `GreedyKPartition` y
    `CostTable`), análisis de complejidad (tabla por componente), implementación, resultados
    experimentales (tablas desde `benchmark_results_FINAL.csv` + 6 figuras), limitaciones y trabajo
    futuro, apéndices (demostración k=2⇒bipartición, reproducción, referencias, uso de IA).
  - `docs/manuales/Manual_Usuario.tex` (~10 págs) — §2.1-2.9: visión general accesible, requisitos,
    instalación paso a paso (uv), placeholder de video, guía de uso con **salida real capturada**
    (`uv run main.py` → KGeoMIP k=3 N10A, φ=0.1875), parámetros, troubleshooting, ejemplos,
    referencia rápida, glosario.
  - `docs/manuales/preambulo.tex` — preámbulo compartido: Times 11pt carta, babel español
    (`es-tabla,es-noshorthands`), microtype (justificación), amsmath (fórmulas), listings con
    `literate` para acentos UTF-8, algorithm/algpseudocode, booktabs, hyperref.
  - `docs/manuales/diagrams/{01_arquitectura,02_clases,03_paquetes,04_secuencia}.puml` — fuentes UML
    editables en PlantUML (espejo de los diagramas TikZ del PDF).
  - `docs/manuales/{Makefile,README.md,.gitignore}` — build (`make`), instrucciones, ignore de
    artefactos.
- **Diagramas:** se intentó renderizar PlantUML pero el entorno no tenía `plantuml`/`dot` ni permisos
  sudo iniciales; se dibujaron los 4 diagramas UML en **TikZ** (autocontenidos en el PDF) +
  `pgf-umlsd` para el de secuencia. Se conservan los `.puml` como fuente editable.
- **Verificación de compilación (regla "verificar, no asumir"):** el usuario instaló
  `texlive-pictures/latexextra/langspanish/mathscience`; ambos manuales **compilan con `pdflatex`**
  (Manual_Tecnico 17 págs, Manual_Usuario ~10 págs), **0 referencias indefinidas**. Se revisaron
  visualmente las páginas de diagramas: se corrigieron solapamientos del diagrama de clases y de
  paquetes (coordenadas explícitas) y una flecha que cruzaba la caja "constants/enums". PDFs
  compilados versionados como entregables.
- **Requerimientos oficiales atendidos:** formato carta/Times 11pt, texto justificado (microtype),
  fórmulas matemáticas con editor LaTeX (Ecs. 1-4: δ_k, EMD analítica, optimización, Stirling),
  diagramas UML 2.x (clases/paquetes/secuencia/arquitectura), pseudocódigo monoespaciado, tablas
  numeradas, sección de uso de IA generativa, referencias. README (WIP del usuario) ya apunta a
  `docs/manuales/`; no se modificó para no pisar sus cambios sin commitear.
- **Datos reales usados (no inventados):** tablas de pérdida/tiempo desde `benchmark_results_FINAL.csv`
  (N10A/N15A × k{2,3,4}); cotas de complejidad verificadas contra el código (`CostTable` O(m·2^m),
  cut pool O(n), δ_k O(2ⁿ), Queyranne O(n³)); salida de consola capturada en vivo.
- **PLANNING:** Fase 8 → ✅; Fase 9 (validación final/entrega) → 🟨.
- **IA:** la IA estructuró y redactó ambos manuales, dibujó los diagramas TikZ/PlantUML, extrajo
  resultados reales del repo y verificó la compilación a PDF iterando sobre los errores de LaTeX.

---

## 2026-06-08 — Fase 9-A: metaheurísticas (GA/SA/Tabú) + integración + pyemd + CSV por comando

- **Prompt del usuario:** «continuemos con la fase 9, además retomemos todo eso que dejamos como
  opcionales e implementémoslo». Decisiones confirmadas vía AskUserQuestion: orden Algoritmos→UI;
  metaheurísticas = las tres (GA+SA+Tabú); rejilla = híbrido honesto.
- **Motor compartido `src/funcs/metaheuristic.py`:** codificación átomo→bloque (vector de etiquetas
  de longitud |F|+|M|), decodificación a `KPartition` estricta, reparación a factibilidad
  (surjectiva sobre k bloques), evaluador memoizado con `delta_k`. Algoritmos: `genetic_search`
  (cruce uniforme + mutación + elitismo + torneo), `simulated_annealing_search` (δ_k como energía,
  enfriamiento geométrico), `tabu_search` (mejor vecino no tabú + aspiración + tenencia).
- **Estrategias `src/controllers/strategies/metaheuristics.py`:** `GeneticSIA`, `AnnealingSIA`,
  `TabuSIA` (heredan de SIA, se puntúan con δ_k, **deterministas** vía `application.numpy_seed=73`).
  Integradas en el dispatcher de `main.py` (genetic/annealing/tabu).
- **Tests `tests/unit/test_metaheuristics.py` (21):** δ_k ≥ exacto (ExhaustiveK), alcanzan el óptimo
  exacto en N3A/N4A (abs 1e-4), determinismo (misma semilla → misma pérdida y partición), partición
  estricta (sin bloque vacío). Verificado: las tres dan loss=0.125 = óptimo en N4A k=3.
- **Integración E2E `tests/integration/test_end_to_end.py` (6 → llena tests/integration):** pipeline
  load→strategy→Solution para las 6 estrategias k-partita; cota heurística ≤ exacto; regresión
  KGeoMIP(k2)=GeometricSIA; roundtrip generar→cargar→analizar TPM.
- **pyemd (EMD causal):** ya cableado en `emd.py` (`causal_emd`/`select_emd`); pyemd 2.0.0 presente.
  `tests/unit/test_emd_causal.py` (3, `importorskip`): EMD=0 idénticas, no-negativa/simétrica,
  `select_emd` despacha a causal/efecto según `application.emd_time`.
- **CSV por comando:** `Manager.generate_network(..., assume_yes=False)` (modo no interactivo para
  CLI/UI) + `scripts/generate_tpm.py` (`--n --continuous --seed --yes`). Verificado en dir temporal.
- **Gates:** `pytest` **191 passed**; `ruff` verde; `mypy` verde. Sin tocar manuales (siguen sin
  commitear por decisión del usuario) ni el WIP de entrada del usuario (exec/main_batch/CLAUDE).
- **IA:** la IA diseñó el motor de metaheurísticas y los tests de validación contra el oráculo,
  cableó la EMD causal opcional y la generación de CSV no interactiva.

---

## 2026-06-08 — Fase 9-B/9-C: figuras interactivas (Plotly) + UI web (Streamlit)

- **Prompt del usuario:** «retomemos todo eso que dejamos como opcionales… figuras estáticas e
  interactivas… UI/UX bien desarrollada». Orden confirmado: algoritmos/base primero, luego UI.
- **Figuras interactivas `src/viz/interactive.py` (Fase 9-B):** `plot_kpartition_interactive`
  (diagrama de bloques de dos capas presente/futuro, hover por bloque), `plot_loss_vs_k_interactive`
  (δ_k vs k, una línea por estrategia), `plot_scalability_interactive` (tiempo vs n, eje y log).
  Plotly se importa de forma perezosa; `src/viz/__init__.py` reexpone los tres vía `__getattr__`
  (no fuerza el extra opcional). Export a HTML autocontenido con `scripts/make_interactive.py`
  (genera `loss_vs_k_*.html`, `scalability_k*.html`, `partition_*_*.html` con plotly.js por CDN).
  Verificado: 6 HTML generados desde `benchmark_core_meta.csv` + demo KGeoMIP N4A k3.
- **Registro de estrategias `src/funcs/runner.py`:** centraliza `STRATEGY_BUILDERS` (7 estrategias
  k-partitas), `STRATEGY_HELP`, `run_analysis(...)` headless (redirige stdout, devuelve `Solution`
  + `KPartition`), `available_samples()`, `load_tpm()`. Compartido por la UI y los scripts.
- **UI web `app/streamlit_app.py` (Fase 9-C):** Streamlit de un archivo. (1) Datos: elegir muestra
  existente o **generar TPM nueva desde el navegador** (0/1 o continua, semilla, `assume_yes=True`);
  (2) Estrategia: selector de las 7 estrategias + ayuda, slider de k (2..min(5,2n)), método de
  clustering, máscaras de subsistema avanzadas; (3) Resultados: métrica δ_k/tiempo, partición,
  diagrama interactivo de la partición, tabla de la distribución marginal, y rejilla benchmark
  interactiva si existe `benchmark_results_FINAL.csv`. Arranque headless verificado (HTTP 200,
  `/_stcore/health` 200, sin trazas de error).
- **Dependencias opcionales (`pyproject.toml`):** extras `viz = [plotly>=5.20]` y
  `web = [streamlit>=1.40, plotly>=5.20]`. Instaladas vía `uv add --optional`. No bloquean `uv sync`
  base. Plotly 6.8.0, Streamlit 1.58.0 verificados.
- **Tests:** `tests/unit/test_runner.py` (registro=ayuda, descubre N10A/N15A, shape N4A, las 7
  estrategias corren E2E con δ_k finito, ninguna mejora al exacto, nombre inválido → KeyError) y
  `tests/unit/test_interactive_viz.py` (`importorskip` plotly; cada helper devuelve `go.Figure`,
  una traza por estrategia, eje log). 13 tests nuevos, en verde.
- **Gates:** `ruff` verde (incl. `app/`), `mypy src` verde (48 archivos). Sin tocar los manuales
  (siguen sin commitear) ni el WIP de entrada del usuario.
- **IA:** la IA diseñó los tres tipos de figura interactiva, el registro headless de estrategias y
  la UI web completa (generación de CSV + análisis + visualización), con sus tests.

---

## 2026-06-08 — Fase 9-A (cierre): rejilla híbrida honesta + validación de instalación limpia

- **Rejilla benchmark con metaheurísticas (datos reales medidos, no inventados):**
  - **Núcleo N10A/N15A × k{2,3,4}** con las 7 estrategias (KGeoMIP, KQNodes, Clustering ×2,
    GA/SA/Tabú), δ_k real. `scripts/run_benchmark.py --nets N10A N15A --ks 2 3 4`.
  - **N20A KGeoMIP** k{2,3,4}: δ_k computado en **~82 s/k** (loss 0.4993/0.9987/1.4982). El núcleo
    geométrico **sí escala a n=20**; KQNodes (Queyranne O(n³·2ⁿ)) y el exacto son impracticables
    ahí (se intentó la rejilla N20/N22 completa y se canceló por inviable en tiempo de sesión).
  - **N25A clustering**: propone partición pero δ_k queda en blanco (reconstrucción 2²⁵ excede
    memoria) → **techo de escalabilidad documentado**.
  - Consolidado reproducible con `scripts/consolidate_results.py` →
    `benchmark_results_FINAL.csv/.xlsx` (53 filas). Figuras estáticas + interactivas regeneradas
    desde el FINAL (escalabilidad ya muestra el punto n=20).
- **Hallazgo de comparación honesto:** Tabú sigue de cerca el óptimo de KGeoMIP/KQNodes; GA/SA
  alcanzan el óptimo en k pequeño pero se quedan atrás en k mayor sobre el espacio 4^(2n) con los
  presupuestos de iteración por defecto (es el comportamiento esperado de una metaheurística).
- **Validación de instalación limpia (entorno nuevo):** `git clone` a `/tmp` + `uv sync --extra web
  --extra emd` → (1) **generar CSV por comando** `scripts/generate_tpm.py --n 4 --yes` (creó N4D.csv);
  (2) análisis headless KGeoMIP N4A k=3 → loss 0.125 + partición; (3) **`pytest` 206 passed**;
  (4) figuras estáticas e interactivas generadas; (5) **UI web arranca** (HTTP 200, `/_stcore/health`
  200, sin errores). El sistema se recrea de cero. Clon temporal eliminado tras validar.
- **IA:** la IA orquestó las corridas del benchmark, midió los tiempos reales a n=20, escribió el
  consolidador reproducible y ejecutó la validación de instalación limpia paso a paso.

---

## 2026-06-08 — Saneamiento, arreglos de auditoría y validación de optimalidad

- **Prompts del usuario:** facilitar el uso (sin editar código), eliminar redundancia/deuda técnica,
  centralizar constantes, y dos auditorías externas (OOM de N25A, early-exit, dead code).
- **Facilidad de uso:** `exec.py` por banderas (`--net N10A --k 3 --strategy kgeomip`, sin editar
  fuente; profiling apagado por defecto); `main.py` simplificado a la ruta avanzada; UI web movida a
  la **raíz** (`streamlit_app.py`, antes en `app/`) y ahora `uv run python streamlit_app.py` funciona
  (se re-lanza bajo el runtime de Streamlit); API deprecada `use_container_width` → `width="stretch"`.
- **Registro único de estrategias (`src/funcs/runner.py`):** `STRATEGY_BUILDERS` + `resolve_strategy`
  (nombres case-insensitive + alias), `build_strategy`, `parse_net_label`. `exec.py`, `main.py`,
  `main_batch.py`, `run_benchmark.py`, `make_interactive.py`, `validate_correctness.py` y la UI dejan
  de duplicar el mapa nombre→constructor y el bucle "construir→redirigir→apply"; todo pasa por aquí.
- **Constantes centralizadas (`src/constants/base.py`):** `BLOCK_PALETTE` (paleta antes duplicada en
  `viz/interactive.py` y `viz/partition_plot.py`), `DELTA_K_TOLERANCE`, `PATH_RESULTS`.
- **Arreglos de auditoría (verificados contra el código):**
  - 🔴 **OOM N25A — causa real:** `Manager.load_network` cargaba `float64` (np.genfromtxt por defecto)
    y la conversión a `float32` creaba una copia → pico ~10 GB. Ahora carga `dtype=np.float32`
    directamente (0/1 exacto; continuos < 1e-6). `main_batch.py` ya no duplica el `genfromtxt`: usa
    `Manager.load_network`. Resultados idénticos (N10A k3 = 0.942383). El `self.network_tpm` que la
    1.ª auditoría señalaba era sólo una *referencia* (no copia) — confirmado y eliminado igual (DRY).
  - 🟡 **Early-exit `δ=0`** añadido al worker paralelo de `ExhaustiveK` (el secuencial ya lo tenía).
  - 🟢 **Dead code** `BruteForce.analyze_full_network` (+ tag e imports huérfanos) eliminado.
  - 🟢 `np.sort` innecesario del muestreo de afinidad de `ClusteringSIA` eliminado.
  - Tests de precisión `float32` ampliados con un caso de **TPM continua** (antes sólo 0/1).
- **Validación de optimalidad (`scripts/validate_optimality.py`):** ¿son óptimas las particiones?
  Exacto donde es tratable (n≤4, k≤3: el sistema acierta 4/4) + evidencia convergente a n grande
  (N10A/N15A: las tres estrategias coinciden en k=2..5). Hallazgo honesto: KGeoMIP/KQNodes son
  **voraces** (cotas superiores para k≥3, p. ej. N3A k=3 0.75 vs 0.5 exacto); **Tabú** recupera el
  óptimo. Sale a `optimality_validation.{xlsx,md}`.
- **Incidente de concurrencia (registrado):** un agente paralelo (`opencode`) reescribió
  `data/samples/N10A.csv` (formato float, valores distintos) a mitad de sesión; se **detectó por el
  cambio de dtype/valores**, se restauró el canónico desde git y se reejecutó la verificación contra
  él. Lección: no correr agentes en paralelo sobre `data/samples/`.
- **Gates:** `pytest` **207 passed**, `ruff` y `mypy` verdes. Sin commitear manuales, `README.md`
  (reescritura pendiente) ni `src/models/core/solution.py` (cambio en curso de `opencode`).
- **IA:** la IA hizo el saneamiento, aplicó los arreglos de ambas auditorías verificándolos contra el
  código, construyó la validación de optimalidad y detectó/contuvo la corrupción de datos concurrente.

---

## 2026-06-08 — Estandarización de estilo (sin comentarios `#`), auditoría de archivos y tema de la UI

- **Prompts del usuario:** (1) aplicar a *todos* los archivos el estándar de estilo ya aplicado a mano
  en `src/controllers/*`; (2) hacer una validación cruzada archivo por archivo de por qué debe existir
  cada uno (sospecha de que `scripts/*` y otros sobran); (3) arreglar `streamlit_app.py` (mantiene la
  estructura en clase pero perdió comportamiento y "colores"). Aclaración explícita a mitad de tarea:
  **no usar comentarios de tipo `#`; documentar sólo con docstrings `"""`** según los requerimientos.
- **Estándar de estilo aplicado (≈30 archivos):** docstring de módulo en todos los módulos que no lo
  tenían (constants, funcs, middlewares, models, enums), docstrings en funciones/métodos públicos que
  faltaban, y **eliminación de todos los comentarios `#` en prosa** (su contenido se trasladó a
  docstrings; se conservan sólo directivas funcionales `# noqa`, `# type:`, `# pragma: no cover`).
  Verificado: 0 comentarios `#` en prosa en `src/` y raíz. Cero cambios de lógica (sólo documentación
  y formato). `ruff format` reformateó 31 archivos; `ruff check` y `mypy src` quedan en verde.
- **Auditoría de archivos (validación cruzada, no asumida — Invariante 4):** la sospecha de que
  `scripts/*` sobra resultó **mayormente falsa**. Referencias verificadas: el README usa
  `generate_tpm`, `validate_optimality`, `validate_correctness`, `run_benchmark`, `make_figures`,
  `make_interactive`; y `docs/manuales/Manual_Tecnico.tex` incrusta (`\includegraphics`) figuras que
  produce `make_viz.py` (`partition_KGeoMIP_N4A_k3.png`, `hypercube_…`) y `make_figures.py`
  (`scalability_k*.png`, `loss_vs_k_*.png`). Todos los módulos de `src/funcs` y `src/viz` tienen
  importadores. Conclusión honesta: **no hay archivos claramente muertos que borrar** (el único ya
  muerto, `src/funcs/accelerate.py` + su test, ya estaba eliminado). Único candidato borderline:
  `scripts/bench_fase6.py` (sólo referenciado en la bitácora; microbench de la Fase 6) — se **conserva**
  por ser la evidencia del trabajo de eficiencia/PCD que pide la rúbrica; queda señalado por si el
  usuario quiere recortarlo.
- **UI web (`streamlit_app.py`):** se mantiene la clase `StreamlitApp`. Comportamiento restaurado que
  se había perdido: mensaje `st.success("Análisis completado.")` y guía de estado vacío `st.info(...)`
  cuando no hay TPM cargada. **Tema de color cohesivo nuevo** (nunca existió en git) siguiendo la
  documentación oficial de theming de Streamlit (https://docs.streamlit.io/develop/concepts/configuration/theming):
  paleta violeta/índigo en `.streamlit/config.toml` (`[theme]`, vía oficial) + capa CSS fina
  (`_inject_theme`) para el banner degradado de cabecera y las tarjetas de métrica; insignia de color
  por *familia* de estrategia (núcleo / baseline / metaheurística / exacta). No se inventó señal de
  optimalidad (no existe en `AnalysisResult`): el color es por familia, no por calidad.
- **Doc:** corregida la referencia obsoleta a `main.py` (eliminado) en `README.md`.
- **Gates:** `ruff check` y `ruff format --check` limpios; `mypy src` sin errores. `pytest` se ejecuta
  **una sola vez al final** de la fase (regla del usuario: no correr tests hasta terminar). Sin
  commitear `docs/manuales/` (gated) ni los archivos WIP del usuario sin pedirlo.
- **IA:** la IA aplicó el estándar de estilo en todo el árbol, hizo la validación cruzada de archivos
  (incluida la verificación de referencias en README y manuales), consultó la documentación oficial de
  Streamlit para el theming y reconstruyó la UI con el tema y el comportamiento restaurado.

### Continuación (misma fecha): DRY de viz, borrado de bench_fase6, limpieza de scripts

- **DRY en `src/viz` (a petición del usuario, "dedup only"):** `_block_color` estaba **duplicado**
  literalmente en `partition_plot.py` e `interactive.py`. Se extrajo a `src/viz/palette.py`
  (`block_color`), única fuente. En `partition_plot.py` se factorizó además el *boilerplate*
  repetido de matplotlib en tres helpers (`_import_matplotlib`, `_block_legend`, `_save_figure`),
  eliminando la triple repetición del bloque de import/leyenda/guardado. Sin cambio de interfaz
  (las funciones estáticas siguen guardando PNG; las interactivas devuelven Figure) — verificado:
  PNG estáticos e interactivo (5 trazas) se renderizan; `test_viz`/`test_interactive_viz` en verde.
- **`scripts/bench_fase6.py` eliminado** (decisión del usuario): microbench de la Fase 6, sólo
  referenciado en la bitácora; los números de speedup ya viven aquí y en los manuales.
- **Limpieza de `scripts/*` al estándar sin `#`:** docstrings en lugar de comentarios de prosa
  (se conservan `# noqa`, `# isort: split` y los ejemplos de uso dentro de docstrings).
- **Conflicto detectado — format-on-save del editor vs. ruff (importante para el usuario):** un
  formateador al guardar (isort con perfil distinto al de ruff) estaba (1) **reordenando imports de
  los controllers** que el usuario había dejado a mano (I001), y (2) **subiendo los `from src ...`
  por encima de `sys.path.insert`** en los 7 scripts, lo que los **rompía en tiempo de ejecución**
  (`ModuleNotFoundError: No module named 'src'`). Se restauró el orden correcto y se añadió
  `# isort: split` tras el bootstrap (directiva funcional, tolerada por ruff) para fijar la frontera.
  Recomendación al usuario: alinear el isort del editor con ruff (o usar ruff como organizador de
  imports) y/o desactivar el format-on-save, o estos archivos volverán a romperse al guardar.
- **Gates finales:** `ruff check`/`ruff format --check` y `mypy src` en verde; suite `pytest`
  re-ejecutada tras el refactor de viz. `generate_tpm.py` ejecutado de verdad (creó N3D.csv) para
  confirmar que los scripts vuelven a correr.

## 2026-06-09 — Fase 10 (pulido): estado inicial configurable (CLI + UI) + arreglo QNodes subsistema pequeño

**Prompt del usuario (resumen):** reportó una "discrepancia" entre la implementación original de la
docente (`.core/core_00/QNodes`, `BruteForce` con `estado_inicial="1000"`, `condiciones/alcance/
mecanismo="1110"` → φ=0.25, bipartición ⎛B⎞⎛A,C⎞ / ⎝∅⎠⎝a,b,c⎠) y su `KQNodes`, que daba φ=0.0000 y
una partición distinta al ejecutarse con `--condition 1000 --purview 1110 --mechanism 1110`. Luego
preguntó por qué, con la misma pérdida, los subconjuntos podían diferir. Y recordó la **bitácora
obligatoria** (no se había registrado el trabajo reciente).

- **Diagnóstico (verificar, no asumir — Invariante 4):** no había bug en `KQNodes`. La discrepancia
  era de **entradas**: (1) la CLI fijaba el estado inicial a `"1"*n` (no existía forma de pasar otro),
  así que `--net N4A` usaba `"1111"` y no `"1000"`; (2) el usuario había puesto el valor del estado
  (`1000`) en `--condition`, donde correspondía `1110`. Al alimentar el código con los parámetros
  exactos de la docente (`state=1000`, `condition=1110`, `purview=mechanism=1110`), **`BruteForce`,
  `KQNodes` y `KGeoMIP` dan los tres φ=0.25** con la misma partición (verificado por volcado del
  objeto `partition`: idénticos salvo orden de bloque y notación `mecanismo|purview` vs apilado).
- **Respuesta a "misma φ, subconjuntos distintos":** es legítimo. La MIP es el *argmin* de δ_k y el
  argmin **no es único**: una bipartición y su complemento describen el mismo corte, y los sistemas
  simétricos tienen **óptimos degenerados (empatados)** donde varias particiones comparten la δ_k
  mínima. `BruteForce` devuelve la *primera* del mínimo (orden de iteración); las heurísticas greedy
  rompen empates a su manera. Lo validado es **φ** (Invariante 3), no qué partición empatada se reporta.
- **`exec.py`: nueva bandera `--state`** (validada a `n` dígitos; por defecto `"1"*n`). La CLI ya puede
  reproducir casos arbitrarios; comprobado que `--net N4A --strategy kqnodes --state 1000 --condition
  1110 --purview 1110 --mechanism 1110` reproduce exactamente el resultado de la docente (marginales
  `[0,0,1]` / `[0,0.25,1]`, φ=0.25).
- **`streamlit_app.py`: estado inicial editable** (`_render_initial_state`, espejo de `--state`):
  cadena binaria de `n` dígitos, validada (longitud y `0/1`), con *fallback* a todo-unos; fluye por
  `tpm_loaded` → `load_tpm`/`run_analysis`. La UI deja de estar fijada a todo-unos.
- **`q_nodes.py`: arreglo de subsistema ≤ 2 vértices** (cambio del usuario, conservado y documentado):
  el bucle de fases necesita ≥ 3 vértices, así que con ≤ 2 se evalúa cada lado *singleton*
  directamente para poblar `partition_memo` (lo consume el cut pool aguas abajo). La explicación se
  movió de comentario `#` a **docstring** (regla del usuario: documentar sólo con `"""`).
- **Polish acompañante (cambios del usuario, integrados):** `manager.py` carga la TPM con
  `np.loadtxt(dtype=float32)` (más estricto, sin pico de copia); `runner.py` corre `ExhaustiveK` con
  `parallel=True`; `solution.py` amplía la detección `k=` en la cabecera; etiquetas de la rejilla de
  benchmark en la UI más claras.
- **Conflicto recurrente — format-on-save del editor vs. ruff:** al reabrir `q_nodes.py` el isort del
  editor reescribió los imports a un perfil con paréntesis colgantes (rompía `ruff check`) y borró el
  comentario que se había añadido. Se normalizó con `ruff check --fix` + `ruff format` como últimas
  escrituras (ver nota de memoria del proyecto). Pendiente real: alinear el isort del editor con ruff.
- **Gates:** `ruff check` y `mypy src` en verde (49 archivos); `tests/unit/test_qnodes_triage.py`
  12/12 (la lógica del arreglo ≤2 es idéntica a la ya probada en `87b78e1`). Suite completa `pytest`
  se reserva para el cierre de fase (regla del usuario: no correr tests en cada cambio).
- **IA:** la IA hizo el diagnóstico cruzado contra `.core/core_00/QNodes` y `BruteForce`, identificó
  el desajuste de entradas, añadió `--state` en CLI y UI, documentó el arreglo de QNodes y registró
  esta bitácora.

### Continuación (2026-06-09): validación cruzada contra el proyecto original `.core/core_00`

**Prompt:** "validación cruzada con el proyecto original `.core/core_00/`, realiza los tests
necesarios y recuerda los `.xlsx` y `Pruebas*.xlsx`".

- **TPMs idénticas:** se verificó `diff` byte a byte de las muestras compartidas entre
  `data/samples/` y `.core/core_00/GeoMIP/data/samples` + `.core/core_00/QNodes/src/.samples`:
  todas **SAME** (N2A..N6A, N8A, N10A, N15A/B, N3C). La comparación es sobre los mismos datos.
- **Batería contra el `BruteForce` original (oráculo k=2):** ejecutado el `BruteForce` y el `QNodes`
  del proyecto original (en su propio venv) sobre N2A..N6A con subsistema completo (estado y máscaras
  todo-unos). El **`BruteForce` original reproduce exactamente** los 10 valores de
  `tests/fixtures/golden_k2.py::ORACLE_LOSS` (N2A=0, N3A=0.25, N3B=0.46875, N3C=0, N4A=0, N4B=0,
  N4C=0, N5A=0, N5B=0.125, N6A=0.46875). El `QNodes` **viejo** de `.core/core_00` es claramente
  subóptimo (solo 2/10 igualan al BF: N4C, N5A) — confirma el defecto histórico que motivó su
  reemplazo (CLAUDE.md "antes 2/8 con la base vieja").
- **Mis estrategias contra el oráculo:** `BruteForce`, `GeometricSIA`, `KGeoMIP(k=2)` y `KQNodes(k=2)`
  igualan el oráculo en **10/10**; el `QNodes` portado en 9/10 (N3B=0.5, el defecto congelado en
  `QNODES_SUBOPTIMAL`). Es decir, mi `KQNodes` nuevo **recupera incluso N3B** vía el cut pool de
  k-particiones, mejor que el `QNodes` aislado.
- **Ground truth oficial (`data/results/Pruebas_Metodo2.xlsx`, PyPhi k=2):** se comprobó la
  consistencia interna Pyphi-vs-GeoMIP por hoja: 3 elem 24/24, 4 elem 49/49, 5 elem 49/49, 6 elem
  50/50, 8 elem 49/49, 10 elem 50/50, 15A 38/38, 15B 38/38, 20 elem 3/4. El GeoMIP oficial reproduce
  a PyPhi casi perfectamente; encadenado con lo anterior: **mi Geo == BruteForce original == PyPhi**.
- **Procedencia documentada** en el docstring de `tests/fixtures/golden_k2.py` (los valores golden son
  la salida del `BruteForce` de referencia, validada el 2026-06-09).
- **Tests:** suite completa `uv run pytest -q` en verde (204 tests).
- **IA:** la IA orquestó la batería cruzada (corriendo el proyecto original en su venv), comparó TPMs
  y losses, leyó la estructura de `Pruebas_Metodo2.xlsx` y verificó la cadena de validación.

### Continuación (2026-06-09): evaluación de los hallazgos de otro modelo (tuning GA, docs ExhaustiveK, rechazo de híbrido y streaming)

**Prompt:** el usuario compartió 4 propuestas de otro modelo (híbrido KQNodes→Tabu, tuning de
Genetic, documentar ExhaustiveK parallel, streaming CostTable) y delegó la decisión, recordando la
misión: implementación **óptima/eficiente** y verificada. Se **verificó cada afirmación** (Invariante
4) antes de actuar; varias eran inexactas.

- **Tuning de Genetic (implementado).** Defaults reales eran `30/40` (no `30/50`). Medición directa
  contra el óptimo exacto en N6A k=3: `GA 30/40 = 1.0625` (**11.5%** de error, coincide con el
  hallazgo del otro modelo) vs `GA 60/80 = 0.95312` (**0.0%**, alcanza el óptimo). Se subió a
  `60/80`. Para cumplir la regla "constantes sólo en `src/constants/`" se creó
  `src/constants/metaheuristics.py` con **todos** los hiperparámetros de GA/SA/Tabu centralizados y
  documentados; `src/funcs/metaheuristic.py` los lee como defaults. Nuevo test de convergencia
  `test_genetic_converges_near_exact_after_tuning` (N6A k=3, error relativo < 2%).
- **Docs de ExhaustiveK (implementado).** Afirmación del otro modelo inexacta: el default real es
  `parallel=False, n_jobs=-1` (no `True`/`4`); el `parallel=True` ya estaba cableado en el registro
  (`runner.py`). Se mejoró el docstring del módulo y de `__init__` con uso, semántica de
  `parallel`/`n_jobs`, y la nota de complejidad `S(2n,k)` super-exponencial + speedup empírico ~2-3×
  con 4 procesos para n≥6 (doc §4.2).
- **Híbrido KQNodes→Tabu (RECHAZADO con evidencia).** Se añadió temporalmente un hook
  `initial_labels` a `tabu_search` y se midió Tabu **sembrado con KQNodes** vs Tabu **aleatorio** vs
  KQNodes solo, en N6A/N10A/N15A k=3,4,5. Resultado: **la siembra no aporta** (Tabu_seed ≈ Tabu_rand
  en todos los casos; única "mejora" en N15A k=4 fue 0.00002, ruido). Además **Tabu ya supera a
  KQNodes** sin sembrar (N6A k=5: 1.50 vs 1.94). Conclusión: una clase nueva `HybridKQNodesTabu` sería
  complejidad sin beneficio medible sobre `TabuSIA` (viola KISS y la misión de eficiencia). Se
  **revirtió** el hook `initial_labels` (sin caller = código muerto). El hallazgo honesto: Tabu es el
  mejor refinador; KQNodes es un buen *upper bound* greedy que Tabu mejora en k alto.
- **Streaming CostTable (DIFERIDO).** Riesgo de cambiar resultados vs la versión eager; el techo n≈25
  ya está documentado honestamente; baja prioridad según el propio otro modelo. No se implementa.
- **Pendiente derivado:** el tuning de GA deja **obsoletas las cifras de Genetic** en los CSV de
  benchmark publicados (ahora GA es mejor). La rejilla se regenerará en la tarea #30 (rejilla oficial);
  las estrategias pesadas (KGeoMIP/KQNodes en n=15/20) no cambian, así que no se re-corre aún por
  eficiencia.
- **Gates:** `ruff check` y `mypy src` en verde (50 archivos); `test_metaheuristics.py` 22/22.
- **IA:** la IA verificó las afirmaciones del otro modelo con mediciones (no asumió), implementó las
  dos mejoras netas (GA, docs), y **rechazó con datos** las dos sin beneficio/riesgosas.

### Continuación (2026-06-09): #30 rejilla oficial — llenado de DatosPruebas2026_1 (N10A validado)

**Prompt:** "update BENCHMARK_CSV" + continuar con #30 (rejilla oficial).

- **BENCHMARK_CSV refrescado:** sólo las filas de `Genetic` de `benchmark_results_FINAL.csv` se
  re-corrieron con el GA 60/80 (el resto de estrategias son deterministas, no cambian → no se re-corre
  por eficiencia). Mejoras grandes: N15A k=3 0.556→0.054, N10A k=3 2.38→0.96, N10A k=4 3.88→2.39.
- **Convención de la rejilla validada (no asumida):** la rejilla `DatosPruebas2026_1.xlsx` da por
  subsistema sólo `Alcance (purview)` y `Mecanismo`, sin condición de fondo. Se dedujo y **verificó**
  contra `Pruebas_Metodo2.xlsx` (losses GeoMIP/PyPhi conocidos para N10A, estado `1000000000`):
  estado = "Estado inicial" de la hoja, **condición = todo-unos**, máscaras desde las letras. Mi
  `GeometricSIA` reproduce 4/4 casos de prueba exactos (0.47265625, 0.0048828125, 0.015625, 0.00390625).
- **Script `scripts/fill_official_grid.py`:** lee la plantilla oficial y escribe en un fichero
  **separado** (`Resultados_DatosPruebas2026_1.xlsx`, la plantilla nunca se sobrescribe); corre
  `KQNodes` (columna QNodes) y `KGeoMIP` (columna Geometric) para k=2,3,4,5 por subsistema; guarda fila
  a fila (reanudable). Mapeo de columnas por bloque de k documentado en `K_BASE_COLUMN`.
- **N10A llenado (49 filas) y validado:** k=2 Geometric **y** k=2 QNodes igualan el GeoMIP oficial en
  **49/49** subsistemas. k=3/4/5 son las cotas heurísticas (upper bounds validados por la suite).
- **Gates:** `ruff check` limpio en el script nuevo.
- **IA:** la IA dedujo la convención faltante (condición) y la **verificó contra ground truth** antes
  de llenar, evitando producir una rejilla incorrecta.

### Continuación (2026-06-09): #30 — N15B validado + techo honesto para n≥20

- **N15B llenado (50 filas) y validado:** k=2 Geometric y QNodes igualan el GeoMIP oficial **50/50**
  (`Pruebas_Metodo2.xlsx`, hoja "15B elementos").
- **Decisión de alcance (datos duros, no asumidos):** se midió `KGeoMIP` sobre el subsistema completo
  de N20A = **~103 s por celda** (la construcción de la CostTable O(2^20) domina); a n=25 hace **OOM**.
  Llenar N20A/22A/25A completos serían horas/días e infactible a n=25 — contra el mandato de
  eficiencia. Por decisión del usuario se **detiene en N15B** y se documenta el techo (Invariante 7).
- **Anotación honesta en el workbook de resultados:** las hojas `20A/22A/25A-Elementos` de
  `Resultados_DatosPruebas2026_1.xlsx` quedan con las celdas de resultado **vacías (no inventadas)** y
  una nota al pie explicando la restricción de cómputo (~103 s/celda a n=20, OOM a n=25; para n=25 sólo
  escala el baseline de Clustering, que no está en las columnas QNodes/Geometric).
- **Estado #30:** N10A (49/49) y N15B (50/50) completos y validados contra el ground truth oficial;
  n≥20 documentado como límite práctico. La plantilla oficial nunca se sobrescribió.

## 2026-06-09 — FASE 11: escala N25 (apertura de fase)

**Prompt:** "perfecto, te creo realiza las implementaciones… estas correcciones son de una nueva
fase recuerda ponerlas en PLANNING.md… ve desarrollando e implementando por nivel de importancia."
Contexto previo: "si revisas bien la documentación oficial y además los .xlsx, piden N=25 tanto en
QNodes como con GeoMIP, así que sí, debe haber una manera para que esos 2 lleguen a tales N."

- **Verificación de la spec (no asumida):** `DatosPruebas2026_1.xlsx` hoja `25A-Elementos` tiene
  columnas QNodes **y** Geometric para k=2,3,4,5 (50 pruebas). El techo n≥20 de Fase 10 incumple
  la rejilla → se abre FASE 11 (rama `feature/fase11-escala-n25`).
- **Prototipos medidos antes de decidir (parámetros reales):**
  - CostTable vectorizada por niveles (`/tmp/proto_vect_cost_table.py`): igualdad **exacta
    (max_abs_err = 0.0)** vs `CostTable` legacy con float32 en m=8/10/12; m=20 en 1.6 s;
    **m=25 en 119.8 s, T=3.36 GB, pico RAM 7.4 GB** (máquina: 15 GiB, 8 cores). El cuello real
    era el `dict[tuple, ndarray]` (~1 KB/entrada × 2^25 ≈ 30+ GB), no la matemática.
  - Marginal local a n=25: una bipartición de 25 cubos pasa de **894 ms** (marginalize completo
    actual) a **1.2–60 ms** (slice al estado + media del bloque) en el rango |W_p|∈[5,20].
  - Bug detectado en el diff sin commitear del working tree (`NCUBE_DTYPE=uint8` y propagación):
    `np.abs(uint8−uint8)` wraparound → costo corrupto **127** (medido con la legacy sobre flat
    uint8); cast uint8 de `marginal_distribution` trunca 0.5→0. **Se descartó el diff** con
    `git restore` (6 ficheros) en vez de commitearlo; la idea de memoria (raíz uint8) se podrá
    retomar sólo con casts float32 explícitos antes de toda aritmética.
- **PLANNING.md:** fila Fase 11 en la tabla de seguimiento + sección FASE 11 con motivación
  verificada, tareas y DoD.
- **IA:** la IA cuestionó su propio veredicto previo ("KQNodes inviable a n=25") al releer la
  rejilla oficial por mandato del usuario, y lo refutó con prototipos medidos antes de implementar.

### Continuación (2026-06-09): FASE 11 — CostTable vectorizada por niveles (producción)

- **`src/funcs/cost_table.py` reescrito:** `CostTable` pasa a ser la versión vectorizada
  (array `(2^m, num_nodes)` float32 indexado por entero little-endian del estado; DP por niveles
  de Hamming con gathers numpy, chunking `COST_TABLE_CHUNK_ROWS = 1<<20` en
  `src/constants/strategies.py` — constante centralizada a petición del usuario, SOLID/KISS/DRY).
  Sin copia apilada `(n, 2^m)` (ahorra ~3.4 GB a m=n=25). La implementación original se conserva
  íntegra como `LegacyCostTable` (referencia ejecutable para tests; docstring advierte OOM n≳20).
- **Reproducción exacta garantizada (Invariante 1):** `candidate_bipartitions` replica el orden
  BFS legacy — verificado empíricamente que `paths[level]` legacy == orden lexicográfico de
  combinaciones de bits volteados (m=6/8/10, todos los niveles); el vectorizado lo realiza con
  máscaras bit-reversed descendentes + `argmin` (primera ocurrencia = desempate `<` estricto del
  legacy); acumulación float64 secuencial en el mismo orden que el bucle Python.
- **Tests nuevos `tests/unit/test_cost_table_vectorized.py` (38 casos):** igualdad bit a bit de
  tabla completa, pool de candidatos (incluye TPMs deterministas 0/1, propensas a empates exactos)
  y `cost()`, vs `LegacyCostTable`, en m=4/6/8/10 + caso rectangular (9 nodos × 6 dims).
- **Gates:** 38/38 nuevos + regresión k=2 (`test_regression_k2`, `test_kgeomip`,
  `test_delta_k_k2_equivalence`: 62/62) en verde; `ruff` y `mypy` limpios.
- **IA:** la IA verificó la propiedad de orden BFS≡lex antes de depender de ella y mantuvo la
  legacy como especificación ejecutable en lugar de borrarla.

### Continuación (2026-06-09): FASE 11 — marginal local O(2^descartadas) en QNodes/δ_k

- **`NCube.marginal_value(axes, initial_state, little_endian)`:** equivalente local de
  `marginalize(axes)` + indexar en el estado inicial — fija primero las dims conservadas (vista)
  y promedia solo el bloque restante: O(2^|descartadas|) vs O(2^|dims|). Memo propio
  (`value_memo`, clave canónica en orden de `dims`) sin materializar tensores marginalizados.
- **`System.bipartition_marginal_distribution` / `k_partition_marginal_distribution`:** wrappers
  finos sobre `marginal_value` con la misma semántica de ejes que `bipartition`/`k_partition`
  (validación de universos extraída a `_validated_block_mapping`, DRY). Consumidores:
  `QNodes.submodular_function` (camino caliente del greedy, hereda KQNodes) y `delta_k`
  (fitness compartido por KGeoMIP/KQNodes en `greedy_k_partition`).
- **Equivalencia medida, no asumida:** en TPMs deterministas 0/1 (dominio del proyecto) la
  igualdad con la vía completa es **bit a bit** (medias diádicas); en float32 aleatorio no diádico
  el orden de suma pairwise difiere en **máx. 1 ulp = 1.19e-07** (barrido exhaustivo de todas las
  biparticiones de sistemas de 3/4/6 nodos). Tests: exactitud para determinista, cota 2 ulp para
  aleatorio (`tests/unit/test_local_marginal.py`), + regresión QNodes contra `QNODES_LOSS` golden.
- **Speedup medido (parámetros reales):** QNodes subsistema completo N20A: **365 s → 5.4 s (67×)**,
  loss=0.4992504119873047 (misma vía de cómputo, igualdad probada). Bug propio detectado y
  corregido durante el cambio: el refactor devolvía `union_marginal_vector` en lugar de
  `delta_marginal_vector` (se revirtió antes de commitear).
- **Gates:** 115 tests (local_marginal + regression_k2 + kqnodes + qnodes_triage +
  delta_k_k2 + kgeomip) en verde; `ruff` y `mypy src` limpios.

### Continuación (2026-06-09): FASE 11 — cache del trabajo caro entre k=2..5 + smoke N25 QNodes

- **Hito medido:** QNodes sobre el subsistema completo de **N25A: 107 s, pico RAM 3.4 GB**
  (loss=0.49980735778808594). El "techo n≈20" de la Fase 10 queda eliminado para la columna
  QNodes de la rejilla oficial.
- **`apply_strategy_for_ks(condition, purview, mechanism, ks)`** en `KGeoMIP` y `KQNodes`:
  la preparación cara (subsistema + CostTable / secuencia Queyranne + cut pool) se ejecuta una
  vez y cada k corre solo su refinamiento greedy — materializa el contrato de la spec de la
  tabla T ("computed once per system … independently of k"). `apply_strategy` delega con
  `(self.k,)` (sin duplicación, DRY). Tiempo por k honesto: la preparación compartida se carga
  al primer k; los siguientes reportan solo su refinamiento (suman al wall-clock real).
- **`scripts/fill_official_grid.py`:** `_run_cell` → `_run_family`: una corrida por familia
  (QNodes/Geometric) por fila llena todas las k faltantes (~4× menos cómputo); reanudación por
  celda de pérdida intacta.
- **Tests `tests/unit/test_apply_strategy_for_ks.py`:** igualdad exacta (loss y partición) entre
  la corrida compartida y las corridas individuales por k en N5A/N6A × ambas estrategias;
  rechazo de k<2; deduplicación de ks.
- **Gates:** 66 tests (for_ks + kgeomip + kqnodes) en verde; `ruff`/`mypy src` limpios.

### Continuación (2026-06-09): FASE 11 — I/O .xlsx estandarizado (CLI + GUI)

- **`src/funcs/grid.py` (módulo único del contrato .xlsx):** lector del formato oficial
  (`GridSheet`/`GridTest`, anclas `Estado inicial`/`#Prueba`, máscaras de letras → bits),
  escritor reanudable (`GridResultsWriter`: la plantilla nunca se modifica, celdas llenas se
  omiten) y motor `fill_grid` (KQNodes+KGeoMIP × k=2..5 con `apply_strategy_for_ks`).
  Constantes de layout en `src/constants/grid.py` (columnas por bloque k validadas en Fase 10).
- **Consumidores unificados (DRY):** `scripts/fill_official_grid.py` queda como wrapper fino;
  `main_batch.py` autodetecta el formato (hojas `*-Elementos` → motor de rejilla; si no, modo
  legacy `Pruebas_Metodo2`); `streamlit_app.py` gana la sección "Rejilla oficial (.xlsx)" con
  selección de hojas y log de progreso (mismo motor, callback).
- **Detección de formato verificada (no asumida):** `Pruebas_Metodo2.xlsx` usa "elementos" en
  minúscula y la oficial "-Elementos" — el sufijo case-sensitive no colisiona (comprobado
  listando los sheetnames de ambos workbooks).
- **Tests `tests/unit/test_grid_io.py`:** máscaras de letras, parsing de anclas, rechazo de
  hojas sin anclas, contrato de reanudación de `missing_ks`, y `fill_grid` end-to-end sobre una
  plantilla sintética N3A (la plantilla queda intacta).
- **Gates:** suite completa en verde; `ruff check .` y `mypy src` limpios (52 ficheros).

### Continuación (2026-06-09): FASE 11 — terminología ("rejilla" → "tabla de evaluación/resultados") y docs

- **Observación del PM aceptada con verificación:** la spec oficial (`docs/Proyecto_KQMIP.md`)
  nunca usa "rejilla"; usa "tabla de costos" y "hojas". Se adopta **"tabla de evaluación oficial"**
  (entrada) y **"tabla de resultados"** (salida) en strings de UI/CLI y docs vivos (PLANNING.md,
  CLAUDE.md, README.md, Streamlit, main_batch). Los identificadores de código permanecen en inglés
  (`grid`, convención del proyecto); las entradas históricas de la bitácora no se reescriben.
- **CLAUDE.md:** contador de tests 142 → 269; referencia al módulo único `src/funcs/grid.py`.
