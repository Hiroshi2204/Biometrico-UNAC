"""
Sistema Biométrico Modular UNAC

Paquete principal del sistema biométrico modular de la Universidad Nacional del Callao.

Este paquete implementa una arquitectura modular y escalable para:
- Conexión con dispositivos biométricos Control iD
- Procesamiento de datos de asistencia
- Generación de reportes Excel profesionales
- Interfaz de línea de comandos intuitiva

Estructura del paquete:
    config/      - Configuración centralizada del sistema
    src/         - Código fuente principal
      data/      - Gestores de datos (biométricos y horarios)
      processing/ - Procesadores de asistencia y reportes
      interface/  - Interfaces de usuario (CLI)
    tests/       - Pruebas unitarias
    docs/        - Documentación
    reportes/    - Archivos de salida
"""

__version__ = "1.0.0"
__author__ = "UNAC - Sistema Biométrico"
__description__ = "Sistema modular de reportes biométricos para UNAC"

# Importaciones principales para uso externo
from .config import (
    CONFIG_VERSION,
    ESCUELAS_DISPONIBLES,
    ESCUELAS_ACTIVAS,
    FACULTADES_DISPONIBLES,
    FACULTADES_FUNCIONALES
)

from .src import (
    BiometricDataManager,
    HorarioDataManager,
    AsistenciaProcessor,
    ReporteGenerator,
    BiometricoCLI
)

__all__ = [
    # Información del paquete
    "__version__",
    "__author__", 
    "__description__",
    
    # Configuración
    "CONFIG_VERSION",
    "ESCUELAS_DISPONIBLES",
    "ESCUELAS_ACTIVAS", 
    "FACULTADES_DISPONIBLES",
    "FACULTADES_FUNCIONALES",
    
    # Componentes principales
    "BiometricDataManager",
    "HorarioDataManager",
    "AsistenciaProcessor", 
    "ReporteGenerator",
    "BiometricoCLI"
]