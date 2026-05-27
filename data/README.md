# Datos del proyecto

## Muestras disponibles (`samples/`)

Matrices de Probabilidad de Transición (TPM) en formato CSV, notación **little-endian**.

| Archivo  | Nodos | Estados | Tipo         |
|----------|-------|---------|--------------|
| N2A.csv  | 2     | 4       | Determinista |
| N3A.csv  | 3     | 8       | Determinista |
| N3B.csv  | 3     | 8       | Determinista |
| N3C.csv  | 3     | 8       | Determinista |
| N4A.csv  | 4     | 16      | Determinista |
| N4B.csv  | 4     | 16      | Determinista |
| N4C.csv  | 4     | 16      | Determinista |
| N5A.csv  | 5     | 32      | Estocástico  |
| N5B.csv  | 5     | 32      | Estocástico  |
| N6A.csv  | 6     | 64      | Estocástico  |
| N8A.csv  | 8     | 256     | Estocástico  |

### Formato del CSV

- **Filas**: estados del sistema en t (2^N filas)
- **Columnas**: probabilidad P(nodo_j = ON | estado_i) en t+1 (N columnas)
- **Separador**: coma (`,`)
- **Indexación**: little-endian (fila 0 = estado `000...0`, fila 1 = estado `100...0`, ...)

### Cómo seleccionar la muestra

En `exec.py` o directamente en `src/base/application.py`:

```python
aplicacion.set_pagina_red_muestra("A")   # carga N{n}A.csv
aplicacion.set_pagina_red_muestra("B")   # carga N{n}B.csv
```

El tamaño N se infiere del `estado_inicial` pasado al `Manager`.

### Cómo generar nuevas redes

```python
from src.io.manager import Manager
gestor = Manager("1000")  # 4 nodos
gestor.generar_red(4, determinista=True)   # genera N4B.csv, N4C.csv, ...
```

## Resultados (`results/`)

Directorio para almacenar salidas de análisis:
- Excel de entrada para modo batch (`Pruebas_Metodo2.xlsx`)
- Excel de salida con resultados (`resultados.xlsx`)
