# Descripción técnica de estrategias

## Conceptos base

### TPM (Transition Probability Matrix)

Matriz de dimensión `(2^N, N)` donde la fila `i` representa el estado del sistema
en el tiempo `t` y la columna `j` es la probabilidad de que el nodo `j` esté activo
en `t+1`. Indexada en notación little-endian: fila 0 = `000...0`, fila 1 = `100...0`.

### N-Cubo

Representación del comportamiento de un solo nodo como tensor `(2, 2, ..., 2)` de N
dimensiones. Permite operar eficientemente sobre condicionamiento y marginalización.

### Condicionamiento

`system.condicionar(dims)` → fija las variables `dims` en su estado inicial,
colapsando las dimensiones correspondientes de cada n-cubo.

### Substracción

`system.substraer(alcance, mecanismo)` → elimina n-cubos del alcance futuro y
marginaliza dimensiones del mecanismo presente, generando el subsistema objetivo.

### Bipartición

`system.bipartir(alcance, mecanismo)` → divide el subsistema en dos partes independientes:
- Parte 1: n-cubos en `alcance`, marginalizados sobre lo que no esté en `mecanismo`
- Parte 2: n-cubos fuera de `alcance`, marginalizados sobre `mecanismo`

### EMD Efecto

Distancia entre distribuciones marginales:

```
φ = Σᵢ |p_subsistema(i) - p_bipartición(i)|
```

Bajo independencia condicional, es la solución analítica a la Earth Mover's Distance.

---

## Estrategia 1: Fuerza Bruta (`BruteForce`)

**Archivo:** `src/controllers/strategies/force.py`

Evalúa todas las `2^(m+n-1) - 1` biparticiones no triviales del subsistema y
retorna la de menor φ.

**Flujo:**
```
biparticiones(futuros, presentes)
  → bipartir(arr_alcance, arr_mecanismo)
  → distribucion_marginal()
  → emd_efecto(dist_part, dist_subsistema)
  → actualiza mínimo si φ < small_phi
```

**Ventaja:** Exacta, garantiza el óptimo global.
**Limitación:** Exponencial en el tamaño del sistema.

---

## Estrategia 2: Q-Nodes (`QNodes`)

**Archivo:** `src/controllers/strategies/q_nodes.py`

Algoritmo greedy que construye incrementalmente conjuntos de nodos minimizando
la ganancia marginal submodular en cada paso.

**Estructura del algoritmo:**
```
Para cada fase i:
  omega = {v₀}
  delta = V \ {v₀}
  Para cada ciclo j:
    Para cada k en delta:
      calcular ganancia: emd(omega ∪ δₖ) - emd(δₖ)
    añadir a omega el δ de menor ganancia
  Formar par candidato (último omega, último delta)
  Guardar en memoria_grupo_candidato
Retornar la partición de menor emd global
```

**Memoización:**
- `memoria_delta`: EMD de nodos evaluados individualmente
- `memoria_grupo_candidato`: EMD de cada par candidato

**Ventaja:** Polinomial en la práctica. Buenos resultados sin evaluación exhaustiva.

---

## Estrategia 3: PyPhi (`Phi`)

**Archivo:** `src/controllers/strategies/phi.py`

Envuelve la librería [PyPhi](https://github.com/wmayner/pyphi) que implementa
el cálculo estándar de φ según la especificación IIT 3.0.

Útil para **validar** resultados de las otras estrategias. Puede calcular
tanto EMD efecto (`effect_mip`) como EMD causal (`cause_mip`).

---

## Estrategia 4: GeoMIP — Programación Dinámica (`GeometricSIA`)

**Archivo:** `src/controllers/strategies/geometric.py`

Utiliza una tabla de transiciones con distancias de Hamming para identificar
candidatos de bipartición sin evaluar todas las combinaciones.

**Flujo:**
```
1. Calcular estado_fin = 1 - estado_ini  (complementario)
2. Para cada nivel de distancia Hamming 1..N:
   - Generar estados vecinos de estado_ini a distancia = nivel
   - Calcular costo de transición: tx(ini, fin) = γ · |X[ini] - X[fin]|
     donde γ = 1/2^dH(ini, fin)
3. Identificar candidatos de bipartición desde la tabla
4. Evaluar EMD efecto para cada candidato
5. Retornar la bipartición de menor φ
```

**Ventaja:** Sub-exponencial. Adecuado para sistemas grandes en modo batch.
**Limitación:** Puede no encontrar el óptimo global en todos los casos.
