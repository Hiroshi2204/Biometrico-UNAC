"""
Configuración completa del sistema biométrico modular UNAC.

Este módulo centraliza toda la configuración necesaria para el funcionamiento
del sistema de reportes biométricos.
"""

from .biometricos import (
    FACULTADES_CONFIG,
    FACULTADES_DISPONIBLES,
    FACULTADES_FUNCIONALES,
    get_facultad_config,
    validate_facultad,
    get_puerto_biometrico
)

from .escuelas import (
    ESCUELAS_CONFIG,
    ESCUELAS_DISPONIBLES,
    ESCUELAS_ACTIVAS,
    MAP_NOMBRE_A_CODIGO,
    get_escuela_config,
    get_facultad_config_for_escuela,
    validate_escuela,
    listar_escuelas_activas,
    get_escuelas_por_facultad,
    normalizar_nombre_escuela
)

# Versión de la configuración
CONFIG_VERSION = "1.0.0"

# Configuración general del sistema
SISTEMA_CONFIG = {
    "version": CONFIG_VERSION,
    "timeout_requests": 30,
    "reintentos_conexion": 3,
    "formato_fecha": "%Y-%m-%d",
    "zona_horaria": "America/Lima",
    "encoding_archivos": "utf-8",
    "extensiones_permitidas": [".xlsx", ".xls"],
    "directorio_reportes": "reportes",
    "directorio_logs": "logs",
    "prefijo_reporte": "reporte_biometrico",
    "debug_mode": False
}

# Ruta fija del Excel crudo de horarios (igual que en el sistema original)
from pathlib import Path
#HORARIO_EXCEL = Path("C:\\Users\\brayan.dev\\Documents\\UnacAnalitics\\Sistema de Biometricos\\biometricos_unac\\data\\PROGRAMACION 2025B - PREGRADO.xlsx")
# HORARIO_EXCEL = Path("C:\\Users\\Administrador\\OneDrive - unac.pe\\BALABARCA - CONTENIDO\\Imágenes\\Escritorio\\BIOMETRICOS_SISTEMA\\Biometricos_modular-main\\data\\PROGRAMACION 2025B - PREGRADO.xlsx")
HORARIO_EXCEL = Path("C:\\BIOMETRICOS_SISTEMA\\Biometricos_modular-main\\data\\PROGRAMACION SGA 2026A - PREGRADO.xlsx")

# Configuración específica para procesamiento de datos
PROCESAMIENTO_CONFIG = {
    "columnas_requeridas_horario": [
        "docente", "escuela", "dia_name", "h_inicio", "h_fin", "f__inicio", "f__fin"
    ],
    "columnas_requeridas_biometrico": [
        "user_id", "time", "location"
    ],
    "tolerancia_minutos": 5,
    "formato_hora": "%H:%M",
    "dias_semana": ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"],
    # Parámetros del algoritmo de asistencia (doble pasada)
    "ventana_entrada_antes_min": 50,  # Minutos antes del inicio para buscar entrada
    "ventana_entrada_despues_min": 50,  # Minutos después del inicio para buscar entrada  
    "ventana_salida_antes_min": 50,  # Minutos antes del fin para buscar salida
    "ventana_salida_despues_min": 50,  # Minutos después del fin para buscar salida
    "adyacencia_bloques_min": 5  # Sesiones ≤ N minutos se consideran mismo bloque
    # Nota: Los cursos compartidos se detectan automáticamente basándose en:
    # mismo docente + mismo horario + misma aula (no requiere configuración manual)
}

# Configuración de salida de reportes
REPORTE_CONFIG = {
    "formato_excel": {
        "engine": "xlsxwriter",
        "options": {
            "strings_to_numbers": True,
            "strings_to_formulas": False,
            "strings_to_urls": False
        }
    },
    "estilos": {
        "header": {
            "bold": True,
            "bg_color": "#4F81BD",
            "font_color": "white",
            "border": 1
        },
        "datos": {
            "border": 1,
            "text_wrap": True
        },
        "presente": {
            "bg_color": "#C6EFCE",
            "font_color": "#006100"
        },
        "ausente": {
            "bg_color": "#FFC7CE", 
            "font_color": "#9C0006"
        }
    },
    # Nombres reales de las hojas generadas por ReporteGenerator (hardcode en reporte.py)
    # Esta sección actúa como documentación central de los nombres canónicos.
    "hojas_excel": {
        "detalle": "Detalle_sesiones",
        "observados": "Resumen_Observados",
        "tardanzas": "Resumen_Tardanzas",
        "faltas": "Resumen_Faltas",
        "evidencia_raw": "Evidencia_Biometricos_RAW"
    }
}

# Validaciones del sistema
def validar_configuracion_completa():
    """
    Valida que toda la configuración esté correcta y consistente.
    
    Returns:
        Tuple (es_valida, lista_errores)
    """
    errores = []
    
    # Validar coherencia entre escuelas y facultades
    for codigo_escuela, config_escuela in ESCUELAS_CONFIG.items():
        facultad_codigo = config_escuela["facultad_codigo"]
        
        if facultad_codigo not in FACULTADES_CONFIG:
            errores.append(f"Escuela {codigo_escuela} referencia facultad inexistente: {facultad_codigo}")
        
        elif not FACULTADES_CONFIG[facultad_codigo]["funcional"] and config_escuela["activa"]:
            errores.append(f"Escuela {codigo_escuela} activa pero facultad {facultad_codigo} no funcional")
    
    # Validar configuración de sistema
    campos_requeridos = ["timeout_requests", "reintentos_conexion", "formato_fecha"]
    for campo in campos_requeridos:
        if campo not in SISTEMA_CONFIG:
            errores.append(f"Configuración de sistema falta campo requerido: {campo}")
    
    return len(errores) == 0, errores





def get_resumen_configuracion():
    """
    Obtiene un resumen de la configuración actual del sistema.
    
    Returns:
        Dict con estadísticas de configuración
    """
    return {
        "version": CONFIG_VERSION,
        "facultades_totales": len(FACULTADES_CONFIG),
        "facultades_funcionales": len(FACULTADES_FUNCIONALES),
        "escuelas_totales": len(ESCUELAS_CONFIG),
        "escuelas_activas": len(ESCUELAS_ACTIVAS),
        "timeout_conexion": SISTEMA_CONFIG["timeout_requests"],
        "tolerancia_asistencia": PROCESAMIENTO_CONFIG["tolerancia_minutos"]
    }


__all__ = [
    # Configuraciones principales
    "FACULTADES_CONFIG",
    "ESCUELAS_CONFIG", 
    "SISTEMA_CONFIG",
    "PROCESAMIENTO_CONFIG",
    "REPORTE_CONFIG",
    
    # Listas útiles
    "FACULTADES_DISPONIBLES",
    "FACULTADES_FUNCIONALES", 
    "ESCUELAS_DISPONIBLES",
    "ESCUELAS_ACTIVAS",
    
    # Funciones de facultades
    "get_facultad_config",
    "validate_facultad",
    "get_puerto_biometrico",
    
    # Funciones de escuelas
    "get_escuela_config",
    "get_facultad_config_for_escuela",
    "validate_escuela", 
    "listar_escuelas_activas",
    "get_escuelas_por_facultad",
    "normalizar_nombre_escuela",
    
    # Funciones de sistema
    "validar_configuracion_completa",
    "get_resumen_configuracion",
    
    # Constantes
    "CONFIG_VERSION",
    "HORARIO_EXCEL"
]