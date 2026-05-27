from src.constants.base import ACTIVE
from src.models.enums.distance import MetricDistance
from src.models.enums.notation import Notation
from src.models.enums.temporal_emd import TimeEMD


class Application:
    """
    Singleton de configuración global del framework IIT.

    Atributos configurables:
    - `semilla_numpy`: semilla determinista para generación de redes aleatorias.
    - `pagina_red_muestra`: sufijo de la red a cargar (A, B, C...) de data/samples/.
    - `distancia_metrica`: métrica de suelo para EMD causal (Hamming por defecto).
    - `notacion_indexado`: notación binaria para indexar los n-cubos (LIL_ENDIAN por defecto).
    - `tiempo_emd`: variante temporal de la EMD a utilizar (efecto por defecto).
    - `modo_estados`: True = estados activos, False = inactivos.
    - `profiler_habilitado`: guarda perfiles HTML en review/profiling/ si True.
    """

    def __init__(self) -> None:
        self.semilla_numpy: int = 73
        self.pagina_red_muestra: str = "A"
        self.distancia_metrica: str = MetricDistance.HAMMING.value
        self.notacion_indexado: str = Notation.LIL_ENDIAN.value
        self.tiempo_emd: str = TimeEMD.EMD_EFECTO.value
        self.modo_estados: bool = ACTIVE
        self.profiler_habilitado: bool = True

    def set_pagina_red_muestra(self, pagina: str) -> None:
        self.pagina_red_muestra = pagina

    def set_notacion(self, tipo: Notation) -> None:
        self.notacion_indexado = tipo.value if isinstance(tipo, Notation) else str(tipo)

    def set_distancia(self, tipo: MetricDistance) -> None:
        self.distancia_metrica = tipo.value if isinstance(tipo, MetricDistance) else str(tipo)

    def set_tiempo_emd(self, tipo: TimeEMD) -> None:
        self.tiempo_emd = tipo.value if isinstance(tipo, TimeEMD) else str(tipo)

    def set_estados_activos(self) -> None:
        self.modo_estados = True

    def set_estados_inactivos(self) -> None:
        self.modo_estados = False

    def activar_profiling(self) -> None:
        self.profiler_habilitado = True

    def desactivar_profiling(self) -> None:
        self.profiler_habilitado = False


aplicacion = Application()
