# Manuales del proyecto K-QGMIP (Fase 8)

Entregables de documentación en **LaTeX**, conformes a las especificaciones
oficiales (`../Manual_Técnico_KQMIP.md`, `../Manual_Usuario_KQMIP.md`,
`../Criterios de Evaluacion_Documentación.md`).

## Contenido

| Archivo | Descripción |
|---|---|
| `Manual_Tecnico.tex` | Manual Técnico: teoría (k-particiones, δ_k), arquitectura (UML), diseño algorítmico + pseudocódigo, complejidad, resultados, limitaciones, uso de IA. |
| `Manual_Usuario.tex` | Manual de Usuario: instalación, uso, parámetros, troubleshooting, ejemplos, referencia rápida. |
| `preambulo.tex` | Preámbulo compartido (Times 11pt carta, español, listings, algoritmos). |
| `diagrams/*.puml` | Fuentes UML editables en PlantUML (espejo de los diagramas TikZ del PDF). |
| `Manual_Tecnico.pdf`, `Manual_Usuario.pdf` | PDFs compilados (entregables). |

## Compilación

Requiere una distribución TeX con `tikz`, `pgf-umlsd`, `listings`, `booktabs`,
`algpseudocode`, `babel-spanish` (todo presente en Overleaf):

```bash
make            # ambos PDFs
make tecnico    # solo el técnico
make usuario    # solo el de usuario
```

O manualmente (dos pasadas para índice/referencias):

```bash
pdflatex -output-directory=build Manual_Tecnico.tex
pdflatex -output-directory=build Manual_Tecnico.tex
```

> También compila tal cual en **Overleaf**: subir esta carpeta y fijar
> `Manual_Tecnico.tex` como documento principal.

## Diagramas UML

Los diagramas del PDF están escritos en **TikZ** (autocontenidos). Las versiones
editables en **PlantUML** están en `diagrams/` y se renderizan con:

```bash
plantuml diagrams/*.puml
```

## Figuras experimentales

Las gráficas (`scalability_*.png`, `loss_vs_k_*.png`) y las visualizaciones de
particiones (`partition_*`, `hypercube_*`) se generan con:

```bash
uv run scripts/make_figures.py
uv run scripts/make_viz.py --net N4A --k 3 --strategy KGeoMIP
```

y quedan en `../../data/results/figures/`, desde donde las incluye el Manual
Técnico.
