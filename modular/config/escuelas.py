"""
Configuración de escuelas y mapeo a facultades biométricas.

Basado en el archivo original escuela_reporte/config_escuelas.py pero refactorizado
para la nueva arquitectura modular.
"""

from typing import Dict, List, Tuple, Optional
from .biometricos import FACULTADES_CONFIG


# Mapeo completo: Escuela -> Información de configuración
ESCUELAS_CONFIG = {
    "ENFERMERIA": {
        "nombre": "Enfermería",
        "nombre_completo": "Escuela Profesional de Enfermería",
        "facultad_codigo": "FCS",
        "codigo_normalizado": "ENFERMERIA",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "ADMINISTRACION": {
        "nombre": "Administración",
        "nombre_completo": "Escuela Profesional de Administración",
        "facultad_codigo": "FCA", 
        "codigo_normalizado": "ADMINISTRACION",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "CONTABILIDAD": {
        "nombre": "Contabilidad",
        "nombre_completo": "Escuela Profesional de Contabilidad",
        "facultad_codigo": "FCC",
        "codigo_normalizado": "CONTABILIDAD", 
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "ECONOMIA": {
        "nombre": "Economía",
        "nombre_completo": "Escuela Profesional de Economía",
        "facultad_codigo": "FCE",
        "codigo_normalizado": "ECONOMIA",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "INGENIERIA_ELECTRICA": {
        "nombre": "Ingeniería Eléctrica",
        "nombre_completo": "Escuela Profesional de Ingeniería Eléctrica",
        "facultad_codigo": "FIEE",
        "codigo_normalizado": "INGENIERIA_ELECTRICA",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "INGENIERIA_ELECTRONICA": {
        "nombre": "Ingeniería Electrónica", 
        "nombre_completo": "Escuela Profesional de Ingeniería Electrónica",
        "facultad_codigo": "FIEE",
        "codigo_normalizado": "INGENIERIA_ELECTRONICA",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "INGENIERIA_DE_SISTEMAS": {
        "nombre": "Ingeniería de Sistemas",
        "nombre_completo": "Escuela Profesional de Ingeniería de Sistemas",
        "facultad_codigo": "FIIS",
        "codigo_normalizado": "INGENIERIA_DE_SISTEMAS",
        "activa": True,
        "observacion": "Escuela funcional - Biométrico FIIS disponible"
    },
    "INGENIERIA_INDUSTRIAL": {
        "nombre": "Ingeniería Industrial",
        "nombre_completo": "Escuela Profesional de Ingeniería Industrial", 
        "facultad_codigo": "FIIS",
        "codigo_normalizado": "INGENIERIA_INDUSTRIAL",
        "activa": True,
        "observacion": "Escuela funcional - Biométrico FIIS disponible"
    },
    "INGENIERIA_MECANICA": {
        "nombre": "Ingeniería Mecánica",
        "nombre_completo": "Escuela Profesional de Ingeniería Mecánica",
        "facultad_codigo": "FIME",
        "codigo_normalizado": "INGENIERIA_MECANICA",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "INGENIERIA_EN_ENERGIA": {
        "nombre": "Ingeniería en Energía",
        "nombre_completo": "Escuela Profesional de Ingeniería en Energía",
        "facultad_codigo": "FIME",
        "codigo_normalizado": "INGENIERIA_EN_ENERGIA", 
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "INGENIERIA_PESQUERA": {
        "nombre": "Ingeniería Pesquera",
        "nombre_completo": "Escuela Profesional de Ingeniería Pesquera",
        "facultad_codigo": "FIPA",
        "codigo_normalizado": "INGENIERIA_PESQUERA",
        "activa": True,
        "observacion": "Biométrico pendiente de instalación"
    },
    "INGENIERIA_DE_ALIMENTOS": {
        "nombre": "Ingeniería de Alimentos", 
        "nombre_completo": "Escuela Profesional de Ingeniería de Alimentos",
        "facultad_codigo": "FIPA",
        "codigo_normalizado": "INGENIERIA_DE_ALIMENTOS",
        "activa": True,
        "observacion": "Biométrico pendiente de instalación"
    },
    "INGENIERIA_QUIMICA": {
        "nombre": "Ingeniería Química",
        "nombre_completo": "Escuela Profesional de Ingeniería Química",
        "facultad_codigo": "FIQ",
        "codigo_normalizado": "INGENIERIA_QUIMICA",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "MATEMATICA": {
        "nombre": "Matemática",
        "nombre_completo": "Escuela Profesional de Matemática", 
        "facultad_codigo": "FCNM",
        "codigo_normalizado": "MATEMATICA",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "FISICA": {
        "nombre": "Física",
        "nombre_completo": "Escuela Profesional de Física",
        "facultad_codigo": "FCNM",
        "codigo_normalizado": "FISICA",
        "activa": True,
        "observacion": "Escuela funcional"
    },
    "INGENIERIA_AMBIENTAL": {
        "nombre": "Ingeniería Ambiental y de RR.NN.",
        "nombre_completo": "Escuela Profesional de Ingeniería Ambiental y de Recursos Naturales",
        "facultad_codigo": "FIARN",
        "codigo_normalizado": "INGENIERIA_AMBIENTAL",
        "activa": True,
        "observacion": "Escuela funcional"
    }
}

# Lista de escuelas disponibles para validación
ESCUELAS_DISPONIBLES = list(ESCUELAS_CONFIG.keys())

# Escuelas activas (con biométrico disponible)
ESCUELAS_ACTIVAS = [
    esc for esc, config in ESCUELAS_CONFIG.items() 
    if config["activa"] and config["facultad_codigo"] in FACULTADES_CONFIG
    and FACULTADES_CONFIG[config["facultad_codigo"]]["funcional"]
]

# Mapeo inverso: Nombre de escuela original -> Código normalizado
MAP_NOMBRE_A_CODIGO = {
    "ENFERMERÍA": "ENFERMERIA",
    "ADMINISTRACIÓN": "ADMINISTRACION", 
    "CONTABILIDAD": "CONTABILIDAD",
    "ECONOMÍA": "ECONOMIA",
    "INGENIERÍA ELÉCTRICA": "INGENIERIA_ELECTRICA",
    "INGENIERÍA ELECTRÓNICA": "INGENIERIA_ELECTRONICA",
    "INGENIERÍA DE SISTEMAS": "INGENIERIA_DE_SISTEMAS",
    "INGENIERÍA INDUSTRIAL": "INGENIERIA_INDUSTRIAL",
    "INGENIERÍA MECÁNICA": "INGENIERIA_MECANICA",
    "INGENIERÍA EN ENERGÍA": "INGENIERIA_EN_ENERGIA",
    "INGENIERÍA PESQUERA": "INGENIERIA_PESQUERA",
    "INGENIERÍA DE ALIMENTOS": "INGENIERIA_DE_ALIMENTOS",
    "INGENIERÍA QUÍMICA": "INGENIERIA_QUIMICA",
    "MATEMÁTICA": "MATEMATICA",
    "FÍSICA": "FISICA",
    "INGENIERÍA AMBIENTAL Y DE RR.NN.": "INGENIERIA_AMBIENTAL",
}


def get_escuela_config(codigo_escuela: str) -> Optional[Dict]:
    """
    Obtiene la configuración de una escuela por su código.
    
    Args:
        codigo_escuela: Código de la escuela (ej: 'INGENIERIA_MECANICA')
    
    Returns:
        Configuración de la escuela o None si no existe
    """
    return ESCUELAS_CONFIG.get(codigo_escuela.upper().replace(" ", "_"))


def get_facultad_config_for_escuela(codigo_escuela: str) -> Optional[Dict]:
    """
    Obtiene la configuración del biométrico (facultad) para una escuela específica.
    
    Args:
        codigo_escuela: Código de la escuela
    
    Returns:
        Configuración de la facultad (biométrico) o None si no existe
    """
    escuela_config = get_escuela_config(codigo_escuela)
    if not escuela_config:
        return None
    
    facultad_codigo = escuela_config["facultad_codigo"]
    return FACULTADES_CONFIG.get(facultad_codigo)


def validate_escuela(codigo_escuela: str) -> Tuple[bool, str]:
    """
    Valida si una escuela existe y está activa.
    
    Args:
        codigo_escuela: Código de la escuela
    
    Returns:
        Tupla (es_valida, mensaje)
    """
    codigo = codigo_escuela.upper().replace(" ", "_")
    
    if codigo not in ESCUELAS_CONFIG:
        return False, f"Escuela '{codigo}' no encontrada. Disponibles: {', '.join(ESCUELAS_DISPONIBLES)}"
    
    escuela_config = ESCUELAS_CONFIG[codigo]
    
    if not escuela_config["activa"]:
        return False, f"Escuela '{codigo}' no activa: {escuela_config['observacion']}"
    
    # Verificar que la facultad asociada esté funcional
    facultad_config = FACULTADES_CONFIG.get(escuela_config["facultad_codigo"])
    if not facultad_config or not facultad_config["funcional"]:
        return False, f"Escuela '{codigo}' sin biométrico funcional (facultad {escuela_config['facultad_codigo']})"
    
    return True, f"Escuela '{codigo}' - {escuela_config['nombre']} lista para procesamiento"


def listar_escuelas_activas() -> List[Tuple[str, str, str, str]]:
    """
    Lista todas las escuelas activas con sus datos básicos.
    
    Returns:
        Lista de tuplas (codigo_escuela, nombre, facultad_codigo, ip_biometrico)
    """
    activas = []
    for codigo, config in ESCUELAS_CONFIG.items():
        if config["activa"] and config["facultad_codigo"] in FACULTADES_CONFIG:
            facultad_config = FACULTADES_CONFIG[config["facultad_codigo"]]
            if facultad_config["funcional"]:
                activas.append((
                    codigo, 
                    config["nombre"], 
                    config["facultad_codigo"],
                    facultad_config["ip"]
                ))
    return activas


def get_escuelas_por_facultad(codigo_facultad: str) -> List[str]:
    """
    Obtiene todas las escuelas que pertenecen a una facultad específica.
    
    Args:
        codigo_facultad: Código de la facultad (ej: 'FIME', 'FIEE')
    
    Returns:
        Lista de códigos de escuela que pertenecen a la facultad
    """
    escuelas = []
    for codigo, config in ESCUELAS_CONFIG.items():
        if config["facultad_codigo"] == codigo_facultad.upper() and config["activa"]:
            escuelas.append(codigo)
    return escuelas


def normalizar_nombre_escuela(nombre_original: str) -> Optional[str]:
    """
    Convierte un nombre de escuela del Excel a su código normalizado.
    
    Args:
        nombre_original: Nombre original de la escuela del Excel
    
    Returns:
        Código normalizado de la escuela o None si no se encuentra
    """
    # Normalizar el nombre de entrada
    nombre_norm = nombre_original.upper().strip()
    
    # Buscar coincidencia directa en el mapeo
    return MAP_NOMBRE_A_CODIGO.get(nombre_norm)