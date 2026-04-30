"""
Módulo base de datos del sistema biométrico modular UNAC.

Centraliza el manejo de todas las fuentes de datos:
- Datos biométricos de dispositivos Control iD
- Horarios académicos desde archivos Excel
- Validaciones y transformaciones de datos
"""

from .biometricos import BiometricDataManager
from .horarios import HorarioDataManager

__all__ = [
    "BiometricDataManager",
    "HorarioDataManager"
]