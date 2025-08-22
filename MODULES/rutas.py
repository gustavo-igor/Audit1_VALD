import os

def get_script_directory() -> str:
    """Obtiene la ruta del directorio donde está este script (modules)."""
    return os.path.dirname(os.path.abspath(__file__))


def convert_rutas() -> dict:

    base_dir = os.path.dirname(get_script_directory())

    rutas = {
        "ruta_panel": os.path.dirname(os.path.dirname(base_dir)),
        "ruta_script_python": base_dir,
        "ruta_guardado_BBDD": os.path.join(base_dir, "FILES\\BBDD"),
        "ruta_guardado_OT": os.path.join(base_dir, "FILES\\BBDD\\OT"),
        "ruta_guardado_MLL": os.path.join(base_dir, "MLL"),
    }

    # Crear directorios si no existen
    for clave, ruta in rutas.items():
        if not os.path.exists(ruta):
            os.makedirs(ruta, exist_ok=True)

    rutas["export"] = os.path.join(
        rutas["ruta_guardado_BBDD"],
        'export.xlsx'
    )

    return rutas
