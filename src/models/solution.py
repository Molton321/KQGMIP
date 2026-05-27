from colorama import init, Fore, Style
from threading import Thread
from typing import Optional
import numpy as np

from src.constants.tags import PYPHI_LABEL
from src.constants.base import FLOAT_ZERO, INT_ZERO, WHITESPACE
from src.base.application import aplicacion

init()


class Solution:
    """
    Representa y visualiza la solución encontrada por una estrategia IIT.

    Contiene la distribución del subsistema, la distribución de la bipartición
    óptima, el valor φ (phi) de pérdida y, opcionalmente, anuncia la solución
    por síntesis de voz.
    """

    def __init__(
        self,
        estrategia: str,
        perdida: float,
        distribucion_subsistema: np.ndarray,
        distribucion_particion: np.ndarray,
        particion: str,
        tiempo_total: float = FLOAT_ZERO,
        quiere_hablar: bool = False,
        voz: Optional[str] = None,
    ) -> None:
        self.estrategia = estrategia
        self.perdida = perdida
        self.distribucion_subsistema = distribucion_subsistema
        self.distribucion_particion = distribucion_particion
        self.particion = particion
        self.tiempo_ejecucion = tiempo_total
        self.id_voz = voz
        self.hablar = quiere_hablar

    def _obtener_voz_espanol(self, motor) -> Optional[str]:
        voces = motor.getProperty("voices")
        prioridades = [
            ("sabina", "méxico"),
            ("helena", "españa"),
            ("spanish", None),
            ("español", None),
            ("es-", None),
        ]
        for nombre_buscado, region in prioridades:
            for voz in voces:
                nombre_voz = voz.name.lower()
                id_voz = voz.id.lower()
                if nombre_buscado in nombre_voz or nombre_buscado in id_voz:
                    if region is None or region in nombre_voz:
                        return voz.id
        return voces[INT_ZERO].id if voces else None

    def _anunciar(self) -> None:
        try:
            import pyttsx3
            motor = pyttsx3.init()
            id_voz = self.id_voz or self._obtener_voz_espanol(motor)
            if id_voz:
                motor.setProperty("voice", id_voz)
            motor.setProperty("rate", 150)
            motor.setProperty("volume", 0.9)
            mensaje = f"Solución encontrada con {self.estrategia}." + (
                f"El valor de fi es de {self.perdida:.2f}"
                if self.perdida > FLOAT_ZERO
                else "No hubo pérdida."
            )
            motor.say(mensaje)
            motor.runAndWait()
        except Exception:
            pass

    def __str__(self) -> str:
        espaciado = 64
        bilinea = "═" * espaciado
        trilinea = "≡" * espaciado

        def fmt_dist(dist: np.ndarray) -> str:
            LIMITE = espaciado
            rango = min(dist.size, LIMITE)
            excedente = dist.size - LIMITE
            suffix = f" {excedente} valores más.." if excedente > 0 else ""
            datos = WHITESPACE.join(
                f"{Fore.WHITE}{dist[i]:.4f}"
                if dist[i] > FLOAT_ZERO
                else f"{Fore.LIGHTBLACK_EX}0.    "
                for i in range(rango)
            )
            return f"[ {datos}{suffix} {Fore.WHITE}]"

        if self.hablar:
            Thread(target=self._anunciar, daemon=True).start()

        es_pyphi = self.estrategia == PYPHI_LABEL
        tipo_dist = "tensorial" if es_pyphi else "marginal"

        t_hrs = f"{self.tiempo_ejecucion / 3600:.2f}"
        t_min = f"{self.tiempo_ejecucion / 60:.1f}"
        t_seg = f"{self.tiempo_ejecucion:.4f}"

        return (
            f"{Fore.CYAN}{bilinea}\n\n"
            f"{Fore.RED}{self.estrategia} fue la estrategia de solución.\n\n"
            f"{Fore.BLUE}Distancia métrica: {Fore.WHITE}{aplicacion.distancia_metrica}\n"
            f"{Fore.BLUE}Notación indexado: {Fore.WHITE}{aplicacion.notacion_indexado}\n\n"
            f"{Fore.YELLOW}Distribución {tipo_dist} del Subsistema:\n"
            f"{Style.RESET_ALL}{fmt_dist(self.distribucion_subsistema)}\n"
            f"{Fore.YELLOW}Distribución {tipo_dist} de la Partición:\n"
            f"{Style.RESET_ALL}{fmt_dist(self.distribucion_particion)}\n\n"
            f"{Fore.YELLOW}Mejor Bi-Partición:\n"
            f"{Fore.MAGENTA}{self.particion}\n"
            f"{Fore.GREEN}Pérdida mínima ( φ ) = {self.perdida:.4f}\n\n"
            f"{Fore.BLUE}Tiempos de ejecución:\n"
            f"{Fore.WHITE}Horas: {t_hrs} = Minutos: {t_min} = Segundos: {t_seg}\n\n"
            f"{Fore.CYAN}{trilinea}{Style.RESET_ALL}"
        )

    def __repr__(self) -> str:
        return self.__str__()
