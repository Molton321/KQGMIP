# Validación cruzada — correctitud y optimalidad de los resultados (Fase 11)

**Fecha:** 2026-06-09 · **Reproducible con:** `uv run scripts/validate_vs_others.py`
(y `scripts/validate_correctness.py` / `scripts/validate_optimality.py` para la validación interna).

Responde a la pregunta: *¿los resultados obtenidos son correctos y óptimos según los
requerimientos oficiales?* contrastando contra **todas** las fuentes externas disponibles.

## 1. Contra el proyecto original de la docente (`.core/core_00`)

| Verificación | Resultado |
|---|---|
| TPMs `N5A/N8A/N10A/N15B.csv` vs las nuestras | **Idénticas byte a byte** |
| `Pruebas_Metodo2.xlsx` y `resultados_Geometric.xlsx` | **Idénticos** a los de `data/results/` |
| Filas de `resultados_Geometric.xlsx` (N15A continua) reproducidas con nuestra `GeometricSIA` | **6/6 OK** (estado `100…0`, condición todo-unos; diferencia ≤ 2·10⁻⁵ relativa, precisión float32 validada en Fase 6) |
| Oráculo k=2 (`tests/fixtures/golden_k2.py`) | Cross-validado en Fase 10: el `BruteForce` de core_00 reproduce los 10/10 valores |

**Conclusión:** nuestro pipeline reproduce exactamente la base de la docente; misma δ, mismos datos.

## 2. Contra terceros — CSVs `data/results_others/{kqnodes,qnodes}` (fuente comparable)

Esta fuente usa la **misma convención** (sus k=2 reproducen el ground truth oficial de
`Pruebas_Metodo2.xlsx`), por lo que la comparación es válida. Cobertura: N5A/N8A/N10A/N15B/
N20A/N22A/N25A(parcial) × k∈{2,3,4,5}.

| Comparación | Casos | Ganamos (δ menor) | Empate | Perdemos |
|---|---|---|---|---|
| Tabla oficial (N10A…N25A), ambas estrategias | 880 × 2 | 660 × 2 | 220 × 2 | **0** |
| N8A (al vuelo), ambas estrategias | 196 × 2 | 133 × 2 | 63 × 2 | **0** |

- **k=2: empate exacto en el 100 %** (220/220 en tabla oficial; 49/49 en N8A) — consistencia
  triple: nosotros ≡ terceros ≡ GeoMIP oficial/PyPhi. Ambas implementaciones encuentran la
  misma bipartición óptima.
- **k≥3: ganamos el 100 % de los casos no empatados y no perdemos ninguno**, con brechas de δ
  de hasta ~9.9 a favor nuestro en N22A/N25A.
- **Causa del gap k≥3 (verificada, no asumida):** las particiones k≥3 de los terceros son
  **inválidas según la definición oficial** (`docs/Proyecto_KQMIP.md` §2.1): sus bloques dejan
  elementos del mecanismo sin asignar (no cubren el universo). Nuestro validador `KPartition`
  las rechaza; completada la cobertura de un ejemplo (N10A test 1, k=3), su partición da
  δ oficial **3.707** frente a nuestra **0.953**.

## 3. Contra terceros — workbook `data/results_others/DatosPruebas2026_1.xlsx` (NO comparable)

En N10A k=2, **21/47** (QNodes) y **42/49** (Geometric) de sus pérdidas están **por debajo del
mínimo exhaustivo validado** (p. ej. reportan 0.25 y 0.1 donde el mínimo exacto es 0.47265625,
confirmado por BruteForce, PyPhi, la docente y los CSVs de §2), y **0** coinciden con el óptimo.
Nada puede estar por debajo del mínimo exacto de la misma función objetivo: ese workbook usa
**otra métrica de pérdida** y no es comparable con la δ oficial. Su `results_kGeoMIP_N10_k3`
presenta además particiones k=3 que omiten elementos del mecanismo (misma violación de §2.1).

## 4. Optimalidad contra el exacto (`ExhaustiveK`) — filas N5A de terceros

(Sección completada al finalizar la corrida exacta; ver bitácora.)

## 5. Veredicto

1. **Correctitud:** validada por cuatro vías independientes (docente, PyPhi, terceros-CSV,
   suite interna de 269 tests con igualdad bit a bit de las optimizaciones de Fase 11).
2. **Optimalidad k=2:** exacta — coincidencia universal de todas las fuentes comparables.
3. **Optimalidad k≥3:** nuestras cotas voraces **dominan** a los terceros comparables en el
   100 % de los casos y nunca pierden; donde el exacto es computable, ver §4.
4. Las discrepancias con el workbook xlsx de terceros se explican por **convenciones
   incompatibles de métrica y de definición de k-partición**, no por errores nuestros: la spec
   §2.1 exige bloques que cubran ambos universos y nuestros resultados lo cumplen siempre.
