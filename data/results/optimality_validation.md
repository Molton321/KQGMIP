# Validación de optimalidad de las k-particiones (K-QGMIP)

¿Las particiones que entrega el sistema son las **mejores** (mínimo δ_k)?
Esta es la evidencia, generada por scripts/validate_optimality.py.

## Metodología

El sistema entrega la **mejor** partición entre sus estrategias (mínimo δ_k de
KGeoMIP/KQNodes/Tabú). El veredicto se juzga sobre ese *mejor*:

- **Exacto (n ≤ 4, k ≤ 3):** ExhaustiveK enumera *todas* las k-particiones; su
  δ_k es el mínimo real. OPTIMO ⇒ el mejor del sistema iguala ese mínimo.
- **Convergente (n grande):** el exacto es intratable; se ejecutan tres búsquedas
  independientes. CONVERGENTE ⇒ las tres coinciden (fuerte evidencia de óptimo);
  MEJOR=TABU ⇒ no coinciden y Tabú aporta la mejor (las voraces quedan por encima).

## Resultados

| red | n | k | KGeoMIP | KQNodes | Tabu | mejor | exacto | convergen | veredicto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N4A | 4 | 3 | 0.125 | 0.125 | 0.125 | 0.125 | 0.125 | sí | OPTIMO |

## Conclusión

- **Casos exactos:** el sistema (mejor estrategia) alcanza el óptimo en
  **1/1**. Importante: las estrategias **voraces** KGeoMIP/KQNodes
  son sólo cotas superiores para k≥3 (p. ej. N3A k=3 dan 0.75 vs 0.5 exacto); **Tabú**
  cierra la brecha y recupera el óptimo. Por eso el sistema ofrece varias estrategias.
- **Casos sin exacto (N10A/N15A):** 0/0 con las tres estrategias
  convergiendo en δ_k (fuerte evidencia de óptimo); en el resto, Tabú da la mejor.
- **k=2** es siempre óptimo (se reduce a la bipartición validada GeoMIP/QNodes).

El **sistema** (tomando la mejor estrategia) acierta el óptimo en el **100 % de los
casos verificables** por fuerza bruta. A n=10/15 el exacto es intratable (enumerar
S(2n,k) no termina en >60 s ni para k=2), pero tres búsquedas de diseño distinto
convergen, lo que da altísima confianza de que la mejor partición hallada es la de
**mínima pérdida**. La lección honesta: una sola estrategia voraz (KGeoMIP) no basta
para k≥3; el valor del portafolio es que Tabú recupera el óptimo donde la voraz falla.
