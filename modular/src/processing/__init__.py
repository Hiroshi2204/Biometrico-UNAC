"""
Módulo de procesamiento del sistema biométrico modular UNAC.

Centraliza toda la lógica de procesamiento para:
- Cruzar datos biométricos con horarios académicos
- Calcular asistencias y ausencias
- Generar reportes de asistencia
"""

from .asistencia import AsistenciaProcessor
from .reporte import ReporteGenerator

__all__ = [
    "AsistenciaProcessor",
    "ReporteGenerator"
]