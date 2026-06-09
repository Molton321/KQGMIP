# PLANEAMIENTO — Proyecto K-QGMIP (KGeoMIP + KQNodes)

> Hoja de ruta por fases para convertir esta **plantilla de bipartición (k=2)** en un
> framework completo de **k-particiones (k ∈ {2,3,4,5})** que escale en número de nodos
> `n` (hasta N25 y más). Portafolio: algoritmos **exactos** (Stirling) para validación,
> las dos estrategias núcleo **`KGeoMIP`** y **`KQNodes`**, un **baseline determinista de
> clustering / detección de comunidades** (espectral / KMeans — precedente oficial "Estrategia
> KM") y, como variante de comparación **opcional**, **metaheurísticas (GA / SA / Tabú)**.
>
> Documento vivo. Cada fase tiene: **objetivo · tareas · archivos · criterios de aceptación
> (DoD) · dependencias**. El estado se actualiza en la tabla de seguimiento (§4).

---

## 1. Contexto y diferencia entre lo actual y lo solicitado

| Dimensión               | Estado actual (plantilla)                     | Objetivo (documento oficial)                                                                |
| ----------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Particiones             | Solo **k=2** (biparticiones)                  | **k ∈ {2,3,4,5}**                                                                           |
| Estrategias             | `GeometricSIA`, `QNodes`, `BruteForce`, `Phi` | **`KGeoMIP`**, **`KQNodes`** (+ exacto y PyPhi para validar)                                |
| Escala `n`              | Probado n≤10                                  | n>5 obligatorio; debe resolver **N25A** y mayores                                           |
| Búsqueda                | Greedy / geométrica exacta                    | + **baseline clustering/espectral** (determinista) y **GA / SA / Tabú** opcional (n grande) |
| Tabla de costos         | Parcial (solo desde estado inicial)           | Calculada y **reutilizada para todo k**                                                     |
| Tests / logs / bitácora | No hay tests; logs básicos                    | **Tests + logs + bitácora** obligatorios                                                    |
| Nomenclatura            | `projecto-analisis-20261`                     | **KGeoMIP / KQNodes** consistente                                                           |
| Documentación           | README desalineado                            | Manual Técnico + Manual Usuario + video + presentación                                      |

**Aclaración de alcance clave:** `k` se mantiene pequeño (≤5); lo que crece es `n`. Por eso
las metaheurísticas operan sobre el espacio de **asignaciones de nodos a k grupos** (en las
capas presente `t` y futuro `t+1`), evaluadas con la **EMD-efecto analítica** (coste O(n) por
candidato), evitando construir tablas de costos O(2ⁿ × 2ⁿ) que serían inviables para n=25.

---

## 2. Principios de diseño

1. **Correctitud antes que velocidad.** Primero exacto + tests; luego perfilar; luego optimizar.
2. **k=2 debe reproducir exactamente** los resultados de la plantilla original (test de regresión).
3. **Reutilizar el núcleo** (`System`, `NCube`, EMD) sin romper la fundamentación teórica.
4. **SOLID + Strategy + Template Method** (heredar de `SIA`), como exige el documento.
5. **Determinismo controlado** en metaheurísticas: semilla fija (`aplicacion.semilla_numpy`)
   para reproducibilidad de experimentos.
6. **Sin deuda técnica:** dependencias fijadas a la última estable (jun 2026), `ruff` + `mypy` + `pytest`.
7. **Documentar en paralelo** (regla del doc: ~30 min de doc por cada hora de código) y registrar
   cada cambio en la bitácora.
8. **Código**: Todo el código en **inglés** (identificadores, docstrings y comentarios). Por
   exigencia de la rúbrica oficial (`docs/Proyecto_KQMIP.md` §4.1 línea 123 y §4.5 línea 155) el
   código va **completamente documentado con docstrings** que expliquen método, parámetros y
   precondiciones, y con **comentarios en línea en las secciones complejas o no obvias**, además de
   **tests unitarios**. Se permite español solo en `PLANNING.md`, `README.md`, los documentos
   de `docs/` y la bitácora `logs/ai_agent_changelog.md`.
   > Decisión 2026-06-07 (revierte el "sin comentarios/docstrings" previo): la rúbrica puntúa la
   > completitud de documentación y comentarios, por lo que se documenta el código, pero en inglés.
9. **Una rama por fase.** Cada fase se entrega en `feature/faseN-<slug>` y, al terminarla
   (validada y en verde), se hace commit + push + PR antes de iniciar la siguiente en una rama nueva.
   Detalle del ciclo obligatorio en `CLAUDE.md` §"Flujo de trabajo por fases".

---

## 3. Estructura objetivo del repositorio

> **Actualización 2026-06-07:** la estructura canónica pasa a ser la **oficial** indicada en
> `docs/Proyecto_KQMIP.md` §4.1 (línea 119): las estrategias viven en **`src/controllers/strategies/`**,
> siguiendo el layout del repo base correcto **20263** (`src/controllers/`, `src/models/{base,core,enums}/`,
> `src/funcs/`, `src/middlewares/`, `src/constants/`). La estructura **real implementada** usa
> **archivos planos** en `src/controllers/strategies/` (no subdirectorios por estrategia), coherente
> con el repo 20263. El árbol de abajo refleja el **estado actual real** tras Fases 0-5A.

```text
KQGMIP/                              # repo/carpeta renombrada (nomenclatura oficial)
├── exec.py                          # punto de entrada (individual / --batch)
├── main.py · main_batch.py
├── pyproject.toml                   # deps reales + grupo dev
├── README.md                        # reescrito y alineado (Fase 8)
├── PLANNING.md                  # este documento
├── CLAUDE.md                        # guía para agentes (incl. bitácora obligatoria)
├── pyphi_config.yml
├── .core/                          # proyectos originales de Bi-particion (referencia, no tocar)
│   └── core_00
│   └── core_01
├── logs/
│   └── ai_agent_changelog.md        # BITÁCORA: fecha, acción, parámetros reales, justificación
├── docs/
│   ├── (PDFs y .md oficiales — no tocar)
│   └── manuales/                    # ENTREGABLES A CREAR en Fase 8 (basados en specs de docs/)
│       ├── Manual_Tecnico_KQGMIP.tex
│       └── Manual_Usuario_KQGMIP.tex
├── data/
│   ├── samples/                     # N2A … N10A … N25A (generados)
│   └── results/                     # salidas Excel + métricas
├── src/
│   ├── base/                        # application.py, sia.py
│   ├── constants/                   # base.py, errors.py, tags.py
│   ├── controllers/
│   │   ├── manager.py               # carga TPM, genera redes
│   │   └── strategies/              # 8 ARCHIVOS PLANOS (no subdirectorios)
│   │       ├── force.py             # BruteForce (k=2 exacto)
│   │       ├── geometric.py         # GeometricSIA (k=2 legacy)
│   │       ├── q_nodes.py           # QNodes (k=2 legacy)
│   │       ├── phi.py               # PyPhi wrapper (validación)
│   │       ├── exhaustive_k.py      # ExhaustiveK (k=2..5 ground truth) ← FASE 2
│   │       ├── kgeomip.py           # KGeoMIP (k=2..5 geométrico) ← FASE 3
│   │       ├── kqnodes.py           # KQNodes (k=2..5 submodular) ← FASE 4
│   │       └── clustering.py        # ClusteringSIA (k=2..n baseline) ← FASE 5A
│   ├── funcs/
│   │   ├── emd.py                   # effect_emd, causal_emd, delta_k, select_emd
│   │   ├── partitions.py            # generadores biparticiones, subsistemas
│   │   ├── labels.py                # lil_endian, big_endian, reindex, select_state
│   │   ├── format.py                # fmt_bipartition, fmt_kpartition
│   │   ├── cost_table.py            # CostTable (tabla T reusable) ← FASE 3
│   │   ├── k_refine.py              # greedy_k_partition (motor compartido) ← FASE 3-4
│   │   ├── accelerate.py            # Numba JIT prep (FASE 6)
│   │   └── parallel.py              # Joblib/multiprocessing prep (FASE 6)
│   ├── middlewares/
│   │   ├── slogger.py               # SafeLogger
│   │   └── profile.py               # @profile decorator
│   ├── models/
│   │   ├── base/                    # application.py, sia.py
│   │   ├── core/
│   │   │   ├── ncube.py
│   │   │   ├── system.py
│   │   │   ├── solution.py
│   │   │   └── partition.py         # KPartition ← FASE 1
│   │   └── enums/
│   │       ├── distance.py
│   │       ├── notation.py
│   │       └── temporal_emd.py
│   └── viz/                         # NUEVO: visualización hipercubo / k-particiones (FASE 7)
└── tests/
    ├── unit/                        # 142 tests passing
    ├── integration/                 # (vacío, para Fase 7/9)
    └── fixtures/                    # golden_k2.py (oráculo PyPhi k=2)
```

---

## 4. Seguimiento de fases

| Fase | Nombre                                                                                     | Estado           | Depende de |
| ---- | ------------------------------------------------------------------------------------------ | ---------------- | ---------- |
| 0    | Cimientos y saneamiento                                                                    | ✅ Completada    | —          |
| 1    | Núcleo de dominio k-genérico                                                               | ✅ Completada    | 0          |
| 2    | k-particiones exactas (ground truth)                                                       | ✅ Completada    | 1          |
| 3    | KGeoMIP (geométrico)                                                                       | ✅ Completada    | 1, 2       |
| 4    | KQNodes (submodular)                                                                       | ✅ Completada    | 1, 2       |
| 5    | Baselines comparativos: clustering/espectral (det.) ✅ + metaheurísticas (opc., diferidas) | ✅ 5A Completada | 1, 2       |
| 6    | Eficiencia y PCD (paralelismo)                                                             | ✅ Completada    | 3, 4, 5    |
| 7    | Experimentación y métricas                                                                 | ✅ Completada    | 3, 4, 5    |
| 8    | Documentación y manuales                                                                   | ✅ Completada    | todas      |
| 9    | Validación final y entrega                                                                 | 🟨 En progreso   | todas      |
| 10   | Pulido: --state CLI/UI, validación cruzada vs .core/core_00, tuning GA, rejilla oficial #30 | 🟨 En progreso   | todas      |
| 11   | Escala N25 (rejilla exige QNodes+Geometric a n=25): CostTable vectorizada por niveles, marginal local, cache por k, I/O xlsx estándar | 🟨 En progreso   | 3, 4, 6, 10 |

Leyenda: ⬜ Pendiente · 🟨 En progreso · ✅ Completada · ⛔ Bloqueada

> **Fase 10 (#30 rejilla oficial):** `DatosPruebas2026_1.xlsx` → `Resultados_DatosPruebas2026_1.xlsx`
> (la plantilla nunca se sobrescribe). **N10A (49/49) y N15B (50/50)** llenados con KQNodes/KGeoMIP
> (k=2..5) y validados: k=2 reproduce el GeoMIP oficial de `Pruebas_Metodo2.xlsx`. **n≥20 documentado
> como techo práctico** (medido: ~103 s/celda KGeoMIP a n=20, OOM a n=25 → Invariante 7); celdas
> vacías con nota al pie, no inventadas.

> **Fase 11 (escala N25):** el techo n≥20 de la Fase 10 **no era fundamental**: era el dict de tuplas
> Python de la CostTable (~30+ GB de overhead a m=25) y el `np.mean` sobre el tensor completo en cada
> evaluación de QNodes. Prototipos validados (2026-06-09): tabla vectorizada por niveles **exacta
> (err 0.0)** vs legacy, m=25 en ~120 s / 3.36 GB / pico 7.4 GB; marginal local 894 ms → 1–60 ms por
> bipartición a n=25. Ver FASE 11 abajo.

---

## FASE 0 — Cimientos y saneamiento

**Objetivo:** dejar la base reproducible, con dependencias reales, tooling y red de seguridad
(tests de caracterización) antes de tocar la lógica.

**Tareas**

- Corregir `pyproject.toml`: declarar dependencias **reales** (`numpy`, `scipy`, `pandas`,
  `openpyxl`, `colorama`, `pyinstrument`, `pyttsx3`) y las que el código importa pero faltan
  (`pyphi`, `pyemd`). Añadir grupo `dev`: `pytest`, `pytest-cov`, `ruff`, `mypy`, `hypothesis`.
- **Resolver el riesgo PyPhi ↔ Python 3.14** (ver §5 Riesgos): verificar si PyPhi instala en
  3.14.5; si no, aislar la validación PyPhi en un entorno/extra opcional y no bloquear el core.
- Configurar `ruff` (lint+format) y `mypy`; opcional `pre-commit`.
- Crear `logs/ai_agent_changelog.md` (plantilla de bitácora) y mover a `CLAUDE.md` las
  instrucciones de agente que hoy contaminan el README.
- Crear `tests/` con **tests de caracterización** que fijen la salida actual de `BruteForce`,
  `QNodes` y `GeometricSIA` para k=2 en N3/N4/N5 (red de seguridad para refactors).
- **Triaje de QNodes:** comparar contra `BruteForce`/PyPhi en N3–N6; aislar si es bug de
  implementación o ruptura de submodularidad; documentar y decidir fix vs reimplementar Queyranne.
- Añadir `matplotlib` (gráficas, Fase 7).
- Generar `data/samples/N25A.csv` (y tamaños intermedios faltantes) con `Manager.generar_red`
  o extrayéndola de `PruebasIniciales.xlsx`; **demostrar carga real a n=25** (validar techo).

**Archivos:** `pyproject.toml`, `CLAUDE.md`, `logs/ai_agent_changelog.md`,
`tests/unit/test_regression_k2.py`, `tests/fixtures/`.

**DoD:** `uv sync` instala todo; `uv run pytest` pasa en verde; `ruff`/`mypy` sin errores
críticos; existe N25A; la bitácora tiene su primera entrada.

---

## FASE 1 — Núcleo de dominio k-genérico

**Objetivo:** generalizar la representación de "partición" de 2 grupos a **k grupos** y formalizar
la pérdida δ_k, manteniendo k=2 idéntico al legacy.

**Tareas**

- `models/partition.py`: tipo `KPartition` (asignación de cada n-cubo presente/futuro a uno de
  k bloques; validación de disjunción, cobertura y no-vacuidad).
- Extender `System` con `k_particionar(asignacion)` → reconstrucción por **producto tensorial de
  k partes** y su distribución marginal.
- `funcs/emd.py`: δ_k = EMD(dist_original, ⊗ marginales de las k partes). Confirmar que para k=2
  coincide con `emd_efecto` actual.
- Tipado estricto + docstrings; tests unitarios (incluye propiedad: k=2 ≡ bipartición legacy).

**DoD:** evaluar una k-partición arbitraria devuelve δ_k correcto; k=2 reproduce la regresión de
Fase 0; cobertura de tests del módulo > 85%.

---

## FASE 2 — k-particiones exactas (ground truth)

**Objetivo:** método exacto para n pequeño que produzca la **k-MIP óptima global**, base de la
métrica "tasa de acierto" y de la validación.

**Tareas**

- `strategies/exhaustive_k/`: enumeración de particiones de Stirling S(n,k) (con poda de
  triviales) y selección de δ_k mínima.
- Validación cruzada con **PyPhi** para k=2 y casos 3–6 nodos.
- Tests: óptimo conocido en N3/N4 para k=2 y k=3.

**DoD:** para N≤6 y k∈{2,3} el exacto coincide con PyPhi (k=2) y con cálculo manual; documentado
el límite de tamaño donde deja de ser viable.

---

## FASE 3 — KGeoMIP (estrategia geométrica, k-particiones)

**Objetivo:** extender GeoMIP a k-particiones reutilizando la **tabla de costos T**.

**Tareas**

- `funcs/cost_table.py`: tabla T con BFS modificado y factor γ = 2^(−d_H) (Algorithm 1 del PDF),
  **calculada una sola vez** y reusable para todo k. Para n grande: versión por niveles /
  bajo demanda / muestreo (no materializar O(2ⁿ×2ⁿ)).
- `strategies/kgeomip/` clase **`KGeoMIP(SIA)`**: k-partición como k−1 cortes (hiperplanos) guiados
  por T; análisis jerárquico (corte grueso → refinar) para n grande.
- Tests de consistencia: KGeoMIP(k=2) ≡ GeoMIP legacy; KGeoMIP vs exacto en n pequeño.

**DoD:** KGeoMIP resuelve k∈{2..5}; reproduce k=2; tabla T se calcula una vez por sistema.

---

## FASE 4 — KQNodes (estrategia submodular, k-particiones)

**Objetivo:** extender QNodes/Queyranne a k-particiones.

**Tareas**

- `strategies/kqnodes/` clase **`KQNodes(SIA)`**: bipartición submodular + extensión a k vía
  partición jerárquica recursiva (k−1 cortes) con memoización.
- Tests: KQNodes(k=2) ≡ QNodes legacy; KQNodes vs exacto en n pequeño.

**DoD:** KQNodes resuelve k∈{2..5}; reproduce k=2; comparación de calidad vs KGeoMIP documentada.

---

## FASE 5 — Baselines comparativos (clustering/espectral + metaheurísticas opcionales)

**Objetivo:** dotar al portafolio de estrategias alternativas a KGeoMIP/KQNodes para n grande:
un **baseline determinista de clustering** (requerido, rápido, reproducible — precedente oficial
"Estrategia KM") y, **opcionalmente**, metaheurísticas si queda tiempo.

### 5A — Baseline clustering / detección de comunidades (REQUERIDO)

Estrategia determinista que trata la k-MIP como un problema de **partición de grafo**: se construye
un grafo de afinidad entre los nodos del subsistema (capas t / t+1) a partir de la influencia
mutua (p.ej. magnitud de las marginales / entradas relevantes de la TPM) y se corta en k bloques.

**Tareas**

- `strategies/clustering/` clase baseline (hereda de `SIA`): construir matriz de afinidad `W`
  (n×n) desde el subsistema; obtener k bloques con **clustering espectral** (Laplaciano vía
  `scipy.sparse.csgraph` + `scipy.linalg`/`sklearn` k-means sobre los autovectores) y/o
  **detección de comunidades** (modularidad). `KMeans` como variante simple (replica "Estrategia KM").
- Puntuar la asignación resultante con la pérdida k-genérica `δ_k` (Fase 1) — no con la métrica
  interna del clustering: el clustering solo **propone** la partición; el oráculo de calidad es δ_k.
- Determinismo: semilla fija (`aplicacion.semilla_numpy`); sin dependencia de orden de iteración.
- Tests: reproduce una partición conocida en n pequeño; comparar su δ_k contra el exacto (Fase 2).

**DoD 5A:** el baseline resuelve k∈{2..5} hasta N25A en segundos; salida determinista; calidad
(δ_k) medida y documentada frente al exacto (n pequeño) y frente a KGeoMIP/KQNodes.

### 5B — Metaheurísticas GA / SA / Tabú (OPCIONAL — solo si hay tiempo)

**Tareas**

- `strategies/metaheuristics/` framework común: representación (cromosoma = asignación de nodos a
  k grupos en capas t/t+1), `fitness = δ_k` (EMD analítica), operadores e interfaz `SIA`.
- **GA**: población de configuraciones de hiperplanos; cruce/mutación que respeten la topología
  del hipercubo; elitismo. **SA**: mutación + enfriamiento para escapar óptimos locales.
  **Tabú**: refinamiento local con memoria de corto plazo. Híbrida/memética (GA+Tabú) opcional.
- Parámetros configurables (población, generaciones, tasa mutación, temperatura, longitud tabú)
  vía `application`/config; **semilla fija** para reproducibilidad.
- Tests: en n pequeño la metaheurística alcanza el óptimo exacto (tasa de acierto alta).

**DoD 5B (si se aborda):** GA/SA/Tabú resuelven k∈{2..5} en N25A en tiempo razonable; parámetros
documentados; calidad medida contra exacto (n pequeño) y contra el baseline 5A.

> Nota de prioridad: 5A es parte del portafolio entregable; 5B es variante de comparación opcional.
> Si el tiempo aprieta, se entrega el portafolio Exacto + KGeoMIP + KQNodes + baseline clustering,
> y las metaheurísticas se documentan como trabajo futuro.

---

## FASE 6 — Eficiencia y PCD (programación concurrente/distribuida)

**Objetivo:** maximizar rendimiento **después** de tener correctitud, según perfilado real.

**Tareas**

- Perfilar (pyinstrument) para hallar cuellos reales (construcción de T, Hamming, evaluación de
  fitness).
- JIT con **Numba** en bucles calientes (cost table, distancias) si el perfilado lo justifica.
- **Paralelización (PCD):** evaluación de población/candidatos y cálculo de T por nodos
  independientes (`multiprocessing`/`joblib`; `Ray` solo si se necesita multi-máquina).
- **GPU opcional** (numba.cuda / cupy) para la tabla de costos en n grande.
- Memoria: TPM en `uint8`, distribuciones en `float32`, T sparse/bajo demanda.

**DoD:** speedup medible y documentado vs versión secuencial sin perder correctitud (tests siguen
en verde).

---

## FASE 7 — Experimentación y métricas

**Objetivo:** generar la evidencia experimental que evalúa el proyecto.

**Tareas**

- Runner batch sobre malla (n, k, estrategia) con timeout, exportando a Excel/CSV.
- Métricas: **tasa de acierto exacto, error relativo en Φ, distancia Jaccard, speedup vs PyPhi,
  escalabilidad (tiempo vs n / vs k), uso de memoria** (umbrales del Cuadro 5.1 del PDF).
- Gráficas interativas si es posible: escalabilidad, precisión, comparativa KGeoMIP vs KQNodes vs baseline
  clustering vs metaheurísticas (si se implementaron).
- `src/viz/`: visualización de k-particiones sobre el hipercubo (k−1 hiperplanos) para la demo interactiva.

**DoD:** tablas y figuras reproducibles desde un comando; resultados para N≤25 y k∈{2..5}.

---

## FASE 8 — Documentación y manuales (incremental)

**Objetivo:** cubrir los entregables documentales (40% Manual Técnico, 30% Usuario, 30% transversal).

**Nota importante:** En `docs/` ya existen las **ESPECIFICACIONES** (requisitos) de ambos manuales:

- `docs/Manual_Técnico_KQMIP.md` → **Spec** del Manual Técnico (no tocar)
- `docs/Manual_Usuario_KQMIP.md` → **Spec** del Manual Usuario (no tocar)

Los **ENTREGABLES REALES** a crear en `docs/manuales/` son:

- `docs/manuales/Manual_Tecnico_KQGMIP.tex` → basado en la spec técnica
- `docs/manuales/Manual_Usuario_KQGMIP.tex` → basado en la spec de usuario

**Tareas**

- `docs/manuales/Manual_Tecnico_KQGMIP.tex`: fundamentos matemáticos, **UML** (clases, paquetes,
  secuencia), pseudocódigo, análisis de complejidad (temporal/espacial en n y k), resultados
  experimentales, reflexión crítica, **uso de IA generativa**.
- `docs/manuales/Manual_Usuario_KQGMIP.tex`: instalación, uso, parámetros, troubleshooting,
  ejemplos, referencia rápida, enlace al **video tutorial**.
- Reescribir **README.md** alineado (k≤5, nomenclatura KGeoMIP/KQNodes, sin stack ficticio, estructura real plana).
- Guion de **presentación** (≤15 min) + demo en vivo.

**DoD:** manuales completos y consistentes en nomenclatura; README fiel al código real; video grabado.

---

## FASE 9 — Validación final y entrega

**Objetivo:** cierre de calidad.

**Tareas**

- End-to-end en todos los datasets; verificación de consistencia k=2 con legacy y PyPhi.
- Revisión de estilo/formato de docs; tabla de resultados final; checklist de criterios oficiales.
- **Limpieza y modernización de entry points:**
  - Actualizar `main_batch.py` para soportar **todas las 7 estrategias** × k=2..5 × grid n×k (FASE 7 runner).
  - Actualizar `main.py` con ejemplos KGeoMIP(k=3), KQNodes(k=4), Clustering(method=kmeans/spectral).
  - Verificar `exec.py` dispatcher funciona con nuevas estrategias.
  - Eliminar `__pycache__`, `.pyc`, archivos temporales del repo (gitignore).
  - Alinear PLANING.md §3 con estructura real (ya hecho en esta validación).
- Etiquetado de versión, bitácora al día.

**DoD:** todos los criterios del documento de evaluación cubiertos; tests en verde; entry points modernizados; entregables listos.

---

## FASE 11 — Escala N25 (CostTable vectorizada, marginal local, cache por k, I/O xlsx)

**Objetivo:** cumplir la rejilla oficial `DatosPruebas2026_1.xlsx` hoja `25A-Elementos`, que exige
columnas **QNodes y Geometric** para k∈{2,3,4,5} a n=25. Elimina el techo práctico n≥20 documentado
en Fase 10, que era de implementación (estructura de datos y orden de operaciones), no algorítmico.

**Motivación verificada (2026-06-09, prototipos en esta máquina: 15 GiB RAM, 8 cores):**

- La CostTable legacy materializa un `dict[tuple, ndarray]` con una entrada por vértice del
  hipercubo: a m=25 son 2^25 ≈ 33.5 M entradas con overhead de objetos Python (~30+ GB) → OOM.
  La misma DP por niveles de Hamming sobre un array `(2^m, n)` float32 indexado por entero de
  estado da **igualdad exacta (error 0.0)** en m=8/10/12 y construye m=25 en **~120 s, 3.36 GB,
  pico de RAM 7.4 GB**.
- `QNodes.submodular_function` marginaliza el tensor completo O(2^n) por cubo y evaluación
  (~894 ms por bipartición a n=25 × ~20k evaluaciones ≈ 9+ h). La marginal **local** (fijar las
  dimensiones conservadas al estado inicial y promediar el bloque restante, O(2^descartadas))
  baja a **1–60 ms** en el rango medio; es lo que este plan ya prescribía en §3 ("fitness con
  marginal local O(2^dims), no recalcular sobre el tensor completo").
- El experimento `NCUBE_DTYPE=uint8` del working tree (sin commitear) se **descartó por bug**:
  `np.abs(uint8 − uint8)` hace wraparound (0−1=255 → costo corrupto 127, medido) y el cast uint8
  de la marginal trunca 0.5→0. La motivación de memoria era válida; la ejecución, incorrecta.

**Tareas**

- CostTable vectorizada por niveles (array `(2^m, n)` float32, orden popcount, gathers numpy),
  manteniendo la API (`cost`, `candidate_bipartitions`) y el **orden lexicográfico** de enumeración
  de candidatos del BFS legacy (mismo desempate en `argmin`). Test de igualdad exacta vs legacy.
- Marginal local en `NCube`/`System` (slice al estado inicial + media del bloque, memoizada por
  kept-set) y uso en `QNodes.submodular_function`. Test de igualdad vs `bipartition()` +
  `marginal_distribution()` (valores diádicos exactos en TPM 0/1).
- Cache del trabajo caro entre k=2..5 por subsistema (la propia spec de `cost_table.py`:
  "computed once per system … independently of k"); aplica a CostTable y a la secuencia Queyranne.
- I/O `.xlsx` estandarizado en un módulo único: lector del formato oficial (hojas
  `N{n}{página}-Elementos` con Estado inicial / Alcance / Mecanismo) y escritor de la rejilla de
  salida (Partición/Pérdida/Tiempo × estrategia × k), compartido por `main_batch.py`,
  `scripts/fill_official_grid.py` y la UI Streamlit.
- Llenado de `20A/22A/25A-Elementos` en `Resultados_DatosPruebas2026_1.xlsx` (reemplaza la nota
  de techo de Fase 10).

**DoD:** tests de igualdad en verde + regresión k=2 intacta; smoke N25 (KGeoMIP y KQNodes) corre
dentro de la RAM disponible; rejilla oficial n≥20 llenada; `pytest`/`ruff`/`mypy` en verde;
bitácora al día.

---

## 5. Riesgos y mitigaciones

| Riesgo                                               | Impacto                      | Mitigación                                                                                                     |
| ---------------------------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------- |
| ~~PyPhi no instala en Python 3.14.5~~ **DESCARTADO** | —                            | Verificado: PyPhi 1.2.1.dev funciona en 3.14.5 + NumPy 2.4.6 (importa y calcula)                               |
| **QNodes defectuoso (subóptimo 62% en n pequeño)**   | KQNodes heredaría el defecto | Triaje en Fase 0/1 contra `BruteForce`/PyPhi; decidir fix vs reimplementar Queyranne; verificar submodularidad |
| **GIL activo (build estándar, no free-threaded)**    | Hilos no paralelizan CPU     | PCD basada en **procesos** (`joblib`/`multiprocessing`), no hilos                                              |
| Tabla de costos O(2ⁿ×2ⁿ) inviable para n=25          | Memoria/tiempo               | Cálculo por niveles / bajo demanda / muestreo; fitness por EMD analítica sin materializar T completa           |
| Metaheurísticas no deterministas                     | Dificultan validación        | Semilla fija + comparación contra exacto en n pequeño + repeticiones con media/desv.                           |
| Romper compatibilidad k=2 al refactorizar            | Pérdida de correctitud       | Tests de caracterización (Fase 0) como red de seguridad                                                        |
| "Últimas versiones jun 2026" desconocidas hoy        | Deuda/incompatibilidad       | Fijar a la última estable al implementar cada fase; no inventar versiones                                      |

---

## 6. Glosario de nomenclatura (consistencia obligatoria)

- **KGeoMIP** — extensión geométrica a k-particiones (clase, carpeta, docs).
- **KQNodes** — extensión submodular a k-particiones (clase, carpeta, docs).
- **k-MIP / δ_k** — k-partición de mínima información y su pérdida (EMD).
- **T** — tabla de costos de transiciones (γ = 2^(−d_H)), reutilizable para todo k.
- **Baseline clustering** — estrategia comparativa determinista (espectral / detección de
  comunidades / KMeans) que propone la k-partición vía partición de grafo; precedente oficial
  "Estrategia KM". Su calidad se mide siempre con δ_k, no con la métrica interna del clustering.

---

## Anexo A — Estado verificado y decisiones (jun 2026)

Registro de hechos **comprobados empíricamente** (no de memoria) y decisiones derivadas.
Regla del proyecto: nada crítico avanza sobre un supuesto sin probar.

### A.1 Hechos verificados

| Hecho                                                   | Evidencia                                                                                  |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Núcleo `System`/`NCube`/`emd_efecto` correcto           | `BruteForce` ≡ `GeoMIP` en 21/21 casos (N3–N6)                                             |
| **GeoMIP correcto** (óptimo exacto)                     | coincide con exhaustivo en 21/21                                                           |
| **QNodes defectuoso**                                   | subóptimo en 13/21 (p.ej. N3C 0.0→0.5); falla casos separables                             |
| Queyranne es **exacto** para submodular simétrica O(n³) | literatura (Springer; arXiv 2605.01473) → el 62% de error indica defecto/no-submodularidad |
| PyPhi funcional en 3.14.5 + NumPy 2.4.6                 | `Network`+`Subsystem` calculan                                                             |
| Loader usa float64                                      | `genfromtxt → float64` (uint8/float32 = mejora real)                                       |
| `marginalizar` es O(2^m)                                | 87 ms@m20, 1.45 s@m24 (cuello L2)                                                          |
| NumPy admite hasta 64 dims                              | `reshape((2,)*n)` ok hasta n=64; barrera = memoria                                         |
| GIL activo (no free-threaded)                           | `sys._is_gil_enabled()=True` → PCD por procesos                                            |
| Capacidad medida                                        | GeoMIP 0.06 s@n10, 2.5 s@n15; QNodes 0.41/0.03 s                                           |
| Datos oficiales presentes                               | `Pruebas_Metodo2` (ground truth PyPhi), `DatosPruebas2026_1` (rejilla k×n)                 |
| Stirling: herramienta correcta                          | `more_itertools.set_partitions` (NO graphillion)                                           |

### A.2 Pendiente de probar (no asumir)

- Carga/proceso real a **n=25** (falta `N25A.csv`; solo proyección de memoria).
- Tiempo de GeoMIP a n=20–25 (extrapolado, no medido).
- Causa raíz del defecto de QNodes (bug vs submodularidad) → triaje.
- Submodularidad simétrica de la pérdida EMD-efecto (teórico).

### A.3 Decisiones consolidadas

- **Portafolio:** Exacto (`more_itertools`) + **KGeoMIP** + **KQNodes** + **baseline espectral**
  (precedente oficial: columna "Estrategia KM"). GA/SA/Tabú = variante opcional final.
- **Triaje de QNodes** entra en Fase 0/1 **antes** de construir KQNodes.
- **PCD por procesos** (`joblib`/`multiprocessing`); GIL activo descarta hilos.
- **Memoria:** TPM `uint8`, distribuciones `float32`; techo realista n≈25.
- Añadir **`matplotlib`** (gráficas). `numba` opcional según perfilado.
- **Formato de salida = rejilla oficial** `DatosPruebas2026_1` (Partición/Pérdida/Tiempo por k
  y estrategia), comparable contra `Pruebas_Metodo2` (PyPhi) para métricas.
- Oráculo de validación: `BruteForce`/exacto (primario) + PyPhi (cross-check 6–10 nodos).

### A.4 Fase 10 (opcional) — UI Streamlit

Interfaz mínima (subir TPM, elegir k y estrategia, ver k-partición y φ, visualizar hipercubo).
Solo si hay tiempo tras Fases 0–9. No es requisito del proyecto.

---

## Anexo A.5 — Decisiones del 2026-06-07 (rebase a 20263 y convenciones)

Origen: `https://github.com/Molton321/projecto-analisis-20263.git`** (rama `main`, que ya integra
`copilot/make-commit-of-claude-info`). El `src/` unificado de 20261 se derivó de un snapshot
**viejo\*\* (`.core/core_00`); 20263 trae código de algoritmos más reciente.

### Hechos verificados (empíricos, esta sesión)

| Hecho                                                   | Evidencia                                                                    |
| ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Samples idénticos 20261 vs 20263                        | `cmp` byte a byte en N3A–N15B → golden δ no se invalidan                     |
| BF y GeoMIP equivalentes (20263 ≡ src actual ≡ oráculo) | δ coinciden en **8/8** (N3A–N6A)                                             |
| **QNodes de 20263 casi correcto**                       | acierta **7/8** vs oráculo (solo falla N3B 0.5 vs 0.46875)                   |
| **QNodes del src actual defectuoso**                    | acierta solo **2/8**; confirma el defecto heredado de la base vieja          |
| 20263 tiene deuda menor                                 | `force.py` usa `np.infty` (removido en NumPy 2.0) → falla en el stack actual |
| N25A generado y techo medido                            | uint8: 57 s / pico 1.64 GB; NCubes float64 ~6.25 GB > RAM libre 6.6 GB       |
| Estructura oficial = `src/controllers/strategies/`      | `docs/Proyecto_KQMIP.md` §4.1 línea 119                                      |
| La rúbrica exige docstrings + comentarios               | `docs/Proyecto_KQMIP.md` §4.1 línea 123 y §4.5 línea 155                     |
| Nombre oficial del proyecto                             | **K_QGMIP** (título de `docs/Proyecto_KQMIP.md`)                             |

### Decisiones consolidadas

1. **Base canónica:** seguir en 20261 (estructura unificada) **portando lo nuevo de 20263**
   (sobre todo el **QNodes corregido**; también las optimizaciones de GeoMIP: matriz precomputada,
   early-exit `emd==0`). Re-validar golden tras portar.
2. **Convención de código:** **inglés** + docstrings completos + comentarios en secciones complejas
   - tests (revisa §2.8). La premisa "QNodes defectuoso 62%" aplica al **código viejo**, no al de 20263.
3. **Estructura objetivo:** layout oficial **`src/controllers/strategies/`** (= 20263); reorganizar
   el `src/` actual a ese layout (supersede §3).
4. **Nombre:** renombrar el paquete/proyecto a **K_QGMIP** según la documentación.
5. **Remote git:** como último paso, re-apuntar `pull`/`push` del 20261 a **20263**.
6. **Tooling:** `uv.lock` versionado; `pyemd` como extra opcional; `matplotlib` añadido.
7. **N25A** generado; el techo n≈25 queda validado (la TPM cabe en uint8; el cuello es construir
   los NCubes en float64 → motiva uint8/float32 de la Fase 6).
