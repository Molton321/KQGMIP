import time
from typing import Dict, List

import numpy as np

from src.base.application import aplicacion
from src.base.sia import SIA
from src.constants.base import ACTUAL, COLS_IDX, EFECTO, NET_LABEL, TYPE_TAG
from src.strategies.geometric.tags import GEOMETRIC_ANALYSIS_TAG, GEOMETRIC_LABEL, GEOMETRIC_STRATEGY_TAG
from src.funcs.emd import emd_efecto
from src.funcs.format import fmt_biparticion_q
from src.funcs.labels import ABECEDARY
from src.io.logger import SafeLogger
from src.io.profiler import gestor_perfilado, profile
from src.models.solution import Solution


class GeometricSIA(SIA):
    """
    Estrategia GeoMIP - Método 2 (Programación Dinámica).

    Construye una tabla de transiciones usando distancias de Hamming entre
    estados para identificar candidatos de bipartición óptima sin evaluar
    exhaustivamente todas las combinaciones.
    """

    def __init__(self, tpm: np.ndarray, estado_inicial: str):
        super().__init__(tpm, estado_inicial)
        gestor_perfilado.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{aplicacion.pagina_red_muestra}"
        )
        self.etiquetas = [tuple(s.lower() for s in ABECEDARY), ABECEDARY]
        self.logger = SafeLogger(GEOMETRIC_STRATEGY_TAG)
        self.tabla_transiciones: dict = {}
        self.vertices: set[tuple]
        self.memoria_particiones: dict[tuple, tuple[float, np.ndarray]] = {}

    @profile(context={TYPE_TAG: GEOMETRIC_ANALYSIS_TAG})
    def aplicar_estrategia(
        self, condicion: str, alcance: str, mecanismo: str
    ) -> Solution:
        self.sia_preparar_subsistema(condicion, alcance, mecanismo)

        futuro = tuple((EFECTO, idx) for idx in self.sia_subsistema.indices_ncubos)
        presente = tuple((ACTUAL, idx) for idx in self.sia_subsistema.dims_ncubos)

        self._flat_data = [ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos]

        self.vertices = set(presente + futuro)
        dims = self.sia_subsistema.dims_ncubos
        self.estado_ini = self.sia_subsistema.estado_inicial[dims]
        self.estado_fin = 1 - self.estado_ini

        mip = self.find_mip()
        fmt_mip = fmt_biparticion_q(list(mip), self.nodes_complement(mip))

        return Solution(
            estrategia=GEOMETRIC_LABEL,
            perdida=self.memoria_particiones[mip][0],
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=self.memoria_particiones[mip][1],
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )

    def nodes_complement(self, nodes) -> list:
        return list(set(self.vertices) - set(nodes))

    def find_mip(self) -> tuple:
        """Encuentra la bipartición de menor pérdida usando la tabla de transiciones."""
        self.sia_logger.critic("Iniciando búsqueda geométrica.")
        n_vars = len(self.sia_subsistema.indices_ncubos)
        self.idx_ncubos = list(range(n_vars))
        self.caminos: Dict[int, List[List[int]]] = {0: [self.estado_ini.tolist()]}
        self.tabla_transiciones[
            (tuple(self.caminos[0][0]), tuple(self.caminos[0][0]))
        ] = [0.0] * n_vars

        for nivel in range(1, len(self.estado_ini) + 1):
            self._calcular_nivel(self.estado_fin, nivel)

        candidatos = self._identificar_candidatos()
        for presentes, futuros in candidatos:
            pres = self.sia_subsistema.dims_ncubos[presentes]
            futs = self.sia_subsistema.indices_ncubos[futuros]
            dist = self.sia_subsistema.bipartir(futs, pres).distribucion_marginal()
            emd = emd_efecto(dist, self.sia_dists_marginales)
            key = [(ACTUAL, n) for n in pres] + [(EFECTO, n) for n in futs]
            self.memoria_particiones[tuple(key)] = (emd, dist)

        return min(self.memoria_particiones, key=lambda k: self.memoria_particiones[k][0])

    def _calcular_nivel(self, estado_final: np.ndarray, nivel: int) -> None:
        visitados: set[tuple] = set()
        self.caminos[nivel] = []
        for estado_prev in self.caminos[nivel - 1]:
            actual = np.array(estado_prev)
            for i in range(len(actual)):
                if actual[i] != estado_final[i]:
                    nuevo = actual.copy()
                    nuevo[i] = estado_final[i]
                    t = tuple(nuevo)
                    if t not in visitados:
                        self.caminos[nivel].append(nuevo.tolist())
                        self._calcular_costo(self.caminos[0][0], nuevo.tolist())
                        visitados.add(t)

    def _calcular_costo(self, estado_ini: list, estado_fin: list) -> None:
        key = tuple(estado_ini), tuple(estado_fin)
        if key not in self.tabla_transiciones:
            self.tabla_transiciones[key] = [None] * len(self.idx_ncubos)

        dh = self._hamming(estado_ini, estado_fin)
        factor = 1 / (2 ** dh)

        ini_int = int("".join(map(str, estado_ini[::-1])), 2)
        fin_int = int("".join(map(str, estado_fin[::-1])), 2)
        diffs = np.abs(
            np.array([f[ini_int] for f in self._flat_data])
            - np.array([f[fin_int] for f in self._flat_data])
        )
        self.tabla_transiciones[key] = diffs.tolist()

        if dh > 1:
            for i in range(len(estado_ini)):
                if estado_ini[i] != estado_fin[i]:
                    vecino = list(estado_fin)
                    vecino[i] = estado_ini[i]
                    temp_key = tuple(estado_ini), tuple(vecino)
                    self.tabla_transiciones[key] = [
                        self.tabla_transiciones[key][n] + self.tabla_transiciones[temp_key][n]
                        for n in self.idx_ncubos
                    ]

        self.tabla_transiciones[key] = [factor * v for v in self.tabla_transiciones[key]]

    def _identificar_candidatos(self) -> list:
        key = tuple(self.caminos[0][0]), tuple(self.estado_fin)
        costos = self.tabla_transiciones[key]
        n_vars = len(costos)

        candidatos = [
            [[i for i in range(len(self.estado_fin))], [i for i in range(n_vars) if i != idx]]
            for idx in range(n_vars)
        ]

        mitad = (len(self.caminos) // 2) + (1 if len(self.caminos) % 2 else 0)
        for nivel in range(1, mitad):
            mejor_costo = 1e5
            pres_nivel, futs_nivel = [], []
            for estado in self.caminos[nivel]:
                costo = 0
                pres, futs = [], []
                actual = self.tabla_transiciones.get((tuple(self.caminos[0][0]), tuple(estado)))
                complementario_estado = (1 - np.array(estado)).tolist()
                comp = self.tabla_transiciones.get(
                    (tuple(self.caminos[0][0]), tuple(complementario_estado))
                )
                for idx, bit in enumerate(estado):
                    if bit == self.caminos[0][0][idx]:
                        pres.append(idx)
                for idx in self.idx_ncubos:
                    if actual[idx] <= comp[idx]:
                        futs.append(idx)
                        costo += actual[idx]
                    else:
                        costo += comp[idx]
                if costo < mejor_costo:
                    mejor_costo = costo
                    pres_nivel = pres
                    futs_nivel = futs
            candidatos.append([pres_nivel, futs_nivel])

        return candidatos

    def _hamming(self, a: list, b: list) -> int:
        return sum(x != y for x, y in zip(a, b))
