"""
Módulo de interfaz del sistema biométrico modular UNAC.

Proporciona interfaces para interactuar con el sistema:
- CLI (Command Line Interface) 
- API para integraciones futuras
"""

from .cli import BiometricoCLI

__all__ = [
    "BiometricoCLI"
]