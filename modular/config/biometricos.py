"""
Configuración de dispositivos biométricos por facultad.

Basado en el archivo original config_facultades.py pero refactorizado
para la nueva arquitectura modular.
"""

from typing import Dict, List, Tuple, Optional


FACULTADES_CONFIG = {
    "FIME": {
        "nombre": "Facultad de Ingeniería Mecánica y Energia",
        "ip": "172.16.1.54",
        "url": "http://172.16.1.54:4772/",
        "usuario": "admin",
        "password": "admin",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FIARN": {
        "nombre": "Facultad de Ingeniería Ambiental y Recursos Naturales",
        "ip": "172.16.1.244",
        "url": "http://172.16.1.244:4772/",
        "usuario": "admin",
        "password": "fiarn20otic25",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FCA": {
        "nombre": "Facultad de Ciencias Administrativas",
        "ip": "172.16.1.220",
        "url": "http://172.16.1.220:4772/",
        "usuario": "Admin",
        "password": "departamento100pre2025",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FIIS": {
        "nombre": "Facultad de Ingeniería Industrial y de Sistemas",
        "ip": "172.16.1.51",
        "url": "http://172.16.1.51:4772/",
        "usuario": "deca",
        "password": "ar071983",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FIQ": {
        "nombre": "Facultad de Ingeniería Química",
        "ip": "172.16.1.23",
        "url": "http://172.16.1.23:4772/",
        "usuario": "admin",
        "password": "#Fiq.otic1#",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FIEE": {
        "nombre": "Facultad de Ingeniería Eléctrica y Electrónica",
        "ip": "172.16.1.46",
        "url": "http://172.16.1.46:4772/",
        "usuario": "admin",
        "password": "admin1",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FCNM": {
        "nombre": "Facultad de Ciencias Naturales y Matemáticas",
        "ip": "172.16.1.15",
        "url": "http://172.16.1.15:4772/",
        "usuario": "admin",
        "password": "admin",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FCS": {
        "nombre": "Facultad de Ciencias de la Salud",
        "ip": "172.16.1.17",
        "url": "http://172.16.1.17:4772/",
        "usuario": "admin",
        "password": "JDCMjdcm",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FIPA": {
        "nombre": "Facultad de Ingeniería Pesquera y de Alimentos",
        "ip": "172.16.5.151",
        "url": "http://172.16.5.151:4772/",
        "usuario": "admin",
        "password": "admin",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    },
    "FCE": {
        "nombre": "Facultad de Ciencias Económicas",
        "ip": "10.8.0.4",
        "url": "http://10.8.0.4/",
        "usuario": "admin",
        "password": "admin",
        "puerto": 80,  # Puerto especial
        "funcional": True,
        "observacion": "Funcional - Puerto 80"
    },
    "FCC": {
        "nombre": "Facultad de Ciencias Contables",
        "ip": "172.16.1.42",
        "url": "http://172.16.1.42:4772/",
        "usuario": "admin",
        "password": "admin",
        "puerto": 4772,
        "funcional": True,
        "observacion": "Funcional"
    }
}

# Lista de facultades disponibles para validación
FACULTADES_DISPONIBLES = list(FACULTADES_CONFIG.keys())

# Facultades funcionales (con acceso disponible)
FACULTADES_FUNCIONALES = [
    fac for fac, config in FACULTADES_CONFIG.items() 
    if config["funcional"] and config["ip"]
]


def get_facultad_config(codigo_facultad: str) -> Optional[Dict]:
    """
    Obtiene la configuración de una facultad por su código.
    
    Args:
        codigo_facultad: Código de la facultad (ej: 'FIME', 'FCA')
    
    Returns:
        Configuración de la facultad o None si no existe
    """
    return FACULTADES_CONFIG.get(codigo_facultad.upper())


def validate_facultad(codigo_facultad: str) -> Tuple[bool, str]:
    """
    Valida si una facultad existe y está funcional.
    
    Args:
        codigo_facultad: Código de la facultad
    
    Returns:
        Tupla (es_valida, mensaje)
    """
    codigo = codigo_facultad.upper()
    
    if codigo not in FACULTADES_CONFIG:
        return False, f"Facultad '{codigo}' no encontrada. Disponibles: {', '.join(FACULTADES_DISPONIBLES)}"
    
    config = FACULTADES_CONFIG[codigo]
    
    if not config["funcional"]:
        return False, f"Facultad '{codigo}' no funcional: {config['observacion']}"
    
    if not config["ip"] or not config["usuario"]:
        return False, f"Facultad '{codigo}' sin credenciales de acceso configuradas"
    
    return True, f"Facultad '{codigo}' - {config['nombre']} lista para procesamiento"


def listar_facultades_funcionales() -> List[Tuple[str, str, str]]:
    """
    Lista todas las facultades funcionales con sus datos básicos.
    
    Returns:
        Lista de tuplas (codigo, nombre, ip)
    """
    funcionales = []
    for codigo, config in FACULTADES_CONFIG.items():
        if config["funcional"] and config["ip"]:
            funcionales.append((codigo, config["nombre"], config["ip"]))
    return funcionales


def extraer_puerto_de_url(url: str) -> int:
    """
    Extrae el puerto de una URL. Si no hay puerto especificado, devuelve 4772 por defecto.
    
    Args:
        url: URL del dispositivo (ej: 'http://172.16.1.54:4772/')
    
    Returns:
        Puerto extraído o 4772 por defecto
    """
    if not url:
        return 4772
    
    # Remover protocolo si existe
    if url.startswith('http://'):
        url = url[7:]
    elif url.startswith('https://'):
        url = url[8:]
    
    # Separar por '/' y tomar la primera parte (host:puerto)
    host_puerto = url.split('/')[0]
    
    # Si hay puerto especificado
    if ':' in host_puerto:
        try:
            puerto = int(host_puerto.split(':')[1])
            return puerto
        except (ValueError, IndexError):
            return 4772
    else:
        # Si no hay puerto especificado, usar 80 para HTTP básico si no es el estándar
        return 80 if not url.endswith(':4772/') else 4772


def get_puerto_biometrico(facultad_codigo):
    """
    Obtiene el puerto del sistema biométrico para una facultad específica.
    
    Args:
        facultad_codigo (str): Código de la facultad
        
    Returns:
        int: Puerto del sistema biométrico (por defecto 4772)
        
    Raises:
        ValueError: Si la facultad no existe
    """
    config = get_facultad_config(facultad_codigo)
    if config is None:
        raise ValueError(f"Facultad '{facultad_codigo}' no encontrada")
    return config.get("puerto", 4772)