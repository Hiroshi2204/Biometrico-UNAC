"""
Módulo principal del sistema biométrico modular UNAC.

Integra todos los componentes del sistema:
- Configuración (config)
- Manejo de datos (data)
- Procesamiento (processing)
- Interfaz (interface)
"""

from .data import BiometricDataManager, HorarioDataManager
from .processing import AsistenciaProcessor, ReporteGenerator
from .interface import BiometricoCLI

__version__ = "1.0.0"
__author__ = "UNAC - Sistema Biométrico"

__all__ = [
    "BiometricDataManager",
    "HorarioDataManager", 
    "AsistenciaProcessor",
    "ReporteGenerator",
    "BiometricoCLI"
]