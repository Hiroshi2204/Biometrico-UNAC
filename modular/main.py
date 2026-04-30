#!/usr/bin/env python3
"""
Sistema Biométrico Modular UNAC v1.0

Punto de entrada principal para el sistema de reportes biométricos.
Este sistema proporciona una arquitectura modular y mantenible para
la generación de reportes de asistencia biométrica en la UNAC.

Uso:
    python modular/main.py <comando> [argumentos]

Comandos principales:
    reporte              - Generar reporte de asistencia (individual o masivo)
    generar-cache        - Generar archivos cache Parquet desde biométricos
    listar-escuelas      - Listar escuelas disponibles
    validar-conectividad - Validar conexión con biométricos
    verificar-config     - Verificar configuración del sistema

Para ayuda detallada:
    python modular/main.py --help
    python modular/main.py <comando> --help

Ejemplos:
    # Generar reporte para una escuela y fecha
    python modular/main.py --esc INGENIERIA_DE_SISTEMAS --date 2024-12-16
    
    # Generar reportes para todas las escuelas
    python modular/main.py --esc ALL --date 2024-12-16

    # Múltiples fechas
    python modular/main.py --esc INGENIERIA_DE_SISTEMAS --date 2024-12-16,2024-12-17,2024-12-18
    
    # Ver escuelas disponibles
    python modular/main.py --list-escuelas
"""

import sys
from pathlib import Path

# Agregar el directorio padre al path para imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

def main():
    """
    Función principal del sistema biométrico UNAC.
    
    Crea una instancia de la CLI y ejecuta el comando solicitado.
    """
    try:
        # Importar y ejecutar la CLI principal
        from modular.src.interface.cli import BiometricoCLI
        
        cli = BiometricoCLI()
        cli.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Operación cancelada por el usuario.")
        sys.exit(130)
    except ImportError as e:
        print(f"❌ Error importando módulos del sistema: {e}")
        print("🔧 Verifique que todos los archivos del sistema modular estén presentes.")
        print("📁 Estructura esperada:")
        print("   modular/")
        print("   ├── config/")
        print("   ├── src/")
        print("   │   ├── interface/")
        print("   │   └── processing/")
        print("   └── main.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error crítico del sistema: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()