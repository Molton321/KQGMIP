ERROR_INCOMPATIBLE_SIZES: str = (
    "Todos los parámetros (initial_state, condition, purview, mechanism) "
    "deben tener la misma longitud."
)


def ERROR_INCOMPATIBLE_SPACES(space: int) -> str:
    return f"Estado inicial debe tener longitud {space}"
