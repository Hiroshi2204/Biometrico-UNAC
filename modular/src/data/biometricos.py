"""
Gestor de datos biométricos del sistema UNAC.

Maneja la conexión y obtención de datos de los dispositivos biométricos Control iD.
Reemplaza y mejora la funcionalidad de controlid_pipeline.py y controlid_horarios.py.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from urllib.parse import urljoin
import re
import io
from unidecode import unidecode

from ...config import (
    FACULTADES_CONFIG, 
    SISTEMA_CONFIG,
    get_facultad_config,
    validate_facultad
)


class BiometricDataManager:
    """
    Gestor principal para datos biométricos de dispositivos Control iD.
    
    Responsabilidades:
    - Conexión a dispositivos biométricos
    - Obtención de registros de asistencia
    - Validación y normalización de datos
    - Manejo de errores de conexión
    """
    
    def __init__(self, timeout: int = None, reintentos: int = None):
        """
        Inicializa el gestor de datos biométricos.
        
        Args:
            timeout: Tiempo límite para conexiones (usa config por defecto)
            reintentos: Número de reintentos en caso de fallo
        """
        self.timeout = timeout or SISTEMA_CONFIG["timeout_requests"]
        self.reintentos = reintentos or SISTEMA_CONFIG["reintentos_conexion"]
        self.logger = logging.getLogger(__name__)
        
        # Session para reutilizar conexiones
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'UNAC-BiometricSystem/1.0'
        })
    
    def conectar_dispositivo(self, facultad_codigo: str) -> Tuple[bool, str]:
        """
        Establece conexión con un dispositivo biométrico específico.
        
        Args:
            facultad_codigo: Código de la facultad (ej: 'FIME', 'FIEE')
        
        Returns:
            Tupla (conexion_exitosa, mensaje)
        """
        # Validar facultad
        es_valida, mensaje = validate_facultad(facultad_codigo)
        if not es_valida:
            return False, mensaje
        
        config = get_facultad_config(facultad_codigo)
        
        try:
            # Probar conexión básica
            url = f"http://{config['ip']}:{config['puerto']}/login.fcgi"
            
            payload = {
                "login": config["usuario"],
                "password": config["password"]
            }
            
            response = self.session.post(
                url, 
                json=payload, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("session"):
                    self.logger.info(f"Conexión exitosa a {facultad_codigo} ({config['ip']})")
                    return True, f"Conectado exitosamente a {config['nombre']}"
                else:
                    return False, f"Error de autenticación en {facultad_codigo}"
            else:
                return False, f"Error HTTP {response.status_code} en {facultad_codigo}"
                
        except requests.exceptions.Timeout:
            return False, f"Timeout al conectar con {facultad_codigo} ({config['ip']})"
        except requests.exceptions.ConnectionError:
            return False, f"No se puede conectar con {facultad_codigo} ({config['ip']})"
        except Exception as e:
            return False, f"Error inesperado en {facultad_codigo}: {str(e)}"
    




    def obtener_registros_asistencia(
        self, 
        facultad_codigo: str, 
        fecha_inicio: str, 
        fecha_fin: str = None
    ) -> Tuple[bool, pd.DataFrame, str]:
        """
        Obtiene registros de asistencia de un dispositivo biométrico.
        
        Args:
            facultad_codigo: Código de la facultad
            fecha_inicio: Fecha inicio en formato 'YYYY-MM-DD'
            fecha_fin: Fecha fin (opcional, usa fecha_inicio si no se especifica)
        
        Returns:
            Tupla (exito, dataframe_registros, mensaje)
        """
        if not fecha_fin:
            fecha_fin = fecha_inicio
        
        # Validar facultad
        es_valida, mensaje = validate_facultad(facultad_codigo)
        if not es_valida:
            return False, pd.DataFrame(), mensaje
        
        config = get_facultad_config(facultad_codigo)
        
        # Intentar conexión primero
        conectado, msg_conexion = self.conectar_dispositivo(facultad_codigo)
        if not conectado:
            return False, pd.DataFrame(), msg_conexion
        
        try:
            # Obtener session token primero
            session_token = self._obtener_session_token(config)
            if not session_token:
                return False, pd.DataFrame(), f"No se pudo obtener token de sesión para {facultad_codigo}"
            
            # Usar la misma API que el sistema original (report_generate.fcgi)
            from datetime import datetime
            import time
            
            # Convertir fechas a timestamps Unix
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            ts_start = int(fecha_inicio_dt.timestamp())
            ts_end = int(fecha_fin_dt.timestamp())
            
            # Construir URL para generar reporte (igual que sistema original)
            base_url = f"http://{config['ip']}:{config['puerto']}"
            url_registros = urljoin(base_url, "/report_generate.fcgi")
            
            # Payload idéntico al sistema original
            payload = {
                "order": ["descending", "time"],
                "where": {
                    "access_logs": {"time": {">=": ts_start, "<=": ts_end}},
                    "users": {}, "groups": {}, "time_zones": {}, "portals": {}
                },
                "object": "access_logs", 
                "delimiter": ";", 
                "line_break": "\\r\\n",
                "header": ";Fecha y Hora (Registros de acceso);Autorización (Registros de acceso);Identificación;Id (Usuario);Nombre (Usuario);Registro (Usuario);Nombre (Portal);Nombre (Zona horaria)",
                "file_name": "", 
                "join": "LEFT",
                "columns": [
                    {"type": "object_field", "object": "access_logs", "field": "id"},
                    {"type": "object_field", "object": "access_logs", "field": "time", "format": {"adjustment": 0, "width": 0, "fill": "0", "format": "%d/%m/%Y %H:%M:%S"}},
                    {"type": "object_field", "object": "access_logs", "field": "event", "format": {"adjustment": 2, "width": 2, "fill": "0", "format": ""}},
                    {"type": "object_field", "object": "access_logs", "field": "identifier_id", "format": {"adjustment": 1, "width": 1, "fill": " ", "format": ""}},
                    {"type": "object_field", "object": "users", "field": "id", "format": {"adjustment": 2, "width": 15, "fill": "0", "format": ""}},
                    {"type": "object_field", "object": "users", "field": "name", "format": {"adjustment": 1, "width": 50, "fill": " ", "format": ""}},
                    {"type": "object_field", "object": "users", "field": "registration", "format": {"adjustment": 1, "width": 50, "fill": " ", "format": ""}},
                    {"type": "object_field", "object": "portals", "field": "name", "format": {"adjustment": 1, "width": 50, "fill": " ", "format": ""}},
                    {"type": "object_field", "object": "time_zones", "field": "name", "format": {"adjustment": 1, "width": 50, "fill": " ", "format": ""}}
                ]
            }
            
            # Usar session como parámetro URL (igual que sistema original)
            response = self.session.post(
                url_registros,
                params={"session": session_token},
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                # El response es texto CSV, no JSON
                csv_text = response.text
                
                if csv_text and len(csv_text.strip()) > 0:
                    # Convertir CSV a DataFrame usando las mismas funciones del sistema original
                    df = self._csv_text_to_df(csv_text, sep=";")
                    if not df.empty:
                        # Normalizar columnas primero
                        df = self._normalize_columns_csv(df)
                        if not df.empty:
                            df = self._normalizar_datos_biometricos(df, facultad_codigo)
                        
                        self.logger.info(f"Obtenidos {len(df)} registros de {facultad_codigo}")
                        return True, df, f"Obtenidos {len(df)} registros exitosamente"
                    else:
                        return True, pd.DataFrame(), f"No hay registros válidos en {facultad_codigo} para el período solicitado"
                else:
                    return True, pd.DataFrame(), f"No hay registros en {facultad_codigo} para el período solicitado"
            else:
                return False, pd.DataFrame(), f"Error HTTP {response.status_code} al obtener registros"
                
        except Exception as e:
            self.logger.error(f"Error obteniendo registros de {facultad_codigo}: {str(e)}")
            return False, pd.DataFrame(), f"Error al obtener registros: {str(e)}"
    
    def obtener_registros_multiples_facultades(
        self, 
        facultades: List[str], 
        fecha: str
    ) -> Dict[str, Tuple[bool, pd.DataFrame, str]]:
        """
        Obtiene registros de múltiples facultades en paralelo.
        
        Args:
            facultades: Lista de códigos de facultad
            fecha: Fecha en formato 'YYYY-MM-DD'
        
        Returns:
            Dict con resultados por facultad
        """
        resultados = {}
        
        for facultad in facultades:
            self.logger.info(f"Procesando facultad: {facultad}")
            resultado = self.obtener_registros_asistencia(facultad, fecha)
            resultados[facultad] = resultado
            
            # Pequeña pausa entre conexiones para no saturar
            import time
            time.sleep(0.5)
        
        return resultados
    
    def _obtener_session_token(self, config: Dict) -> Optional[str]:
        """
        Obtiene token de sesión de un dispositivo específico.
        
        Args:
            config: Configuración del dispositivo
        
        Returns:
            Token de sesión o None si falla
        """
        try:
            url = f"http://{config['ip']}:{config['puerto']}/login.fcgi"
            payload = {
                "login": config["usuario"],
                "password": config["password"]
            }
            
            response = self.session.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("session")
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo token: {str(e)}")
            return None
    
    def _csv_text_to_df(self, csv_text: str, sep: str = ";") -> pd.DataFrame:
        """
        Convierte texto CSV a DataFrame (copiado del sistema original).
        """
        import io
        return pd.read_csv(io.StringIO(csv_text), sep=sep, dtype=str, engine="python")
    
    def _normalize_columns_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza nombres de columnas del CSV (copiado del sistema original).
        """
        def canon(s: str) -> str:
            s = unidecode((s or "")).lower().strip()
            s = s.replace("(", "").replace(")", "")
            s = re.sub(r"\s+", " ", s)
            return s

        norm = {c: canon(c) for c in df.columns}
        mapping = {}
        for orig, nc in norm.items():
            if "fecha y hora" in nc and ("acceso" in nc or nc == "fecha y hora"): 
                mapping[orig] = "fecha_hora"
            elif nc.startswith("autorizacion"): 
                mapping[orig] = "autorizacion"
            elif nc.startswith("identificacion"): 
                mapping[orig] = "identificacion"
            elif nc.startswith("id ") and "usuario" in nc: 
                mapping[orig] = "id_usuario"
            elif "nombre" in nc and "usuario" in nc: 
                mapping[orig] = "nombre_usuario"
            elif "registro" in nc and "usuario" in nc: 
                mapping[orig] = "registro_usuario"
            elif "portal" in nc: 
                mapping[orig] = "portal"
            elif "zona horaria" in nc or "zonahoraria" in nc: 
                mapping[orig] = "zona_horaria"
            else: 
                mapping[orig] = canon(orig).replace(" ", "_")

        df = df.rename(columns=mapping)
        required = {"fecha_hora", "id_usuario", "nombre_usuario"}
        if not required.issubset(df.columns):
            faltan = required - set(df.columns)
            self.logger.warning(f"Faltan columnas requeridas {faltan}. Columnas: {df.columns.tolist()}")
            return pd.DataFrame()  # Retornar DataFrame vacío si faltan columnas
        return df

    def _normalizar_datos_biometricos(self, df: pd.DataFrame, facultad_codigo: str) -> pd.DataFrame:
        """
        Normaliza y limpia los datos biométricos obtenidos.
        Migra la lógica completa del sistema original (controlid_pipeline.py).
        
        Args:
            df: DataFrame con datos crudos
            facultad_codigo: Código de la facultad de origen
        
        Returns:
            DataFrame normalizado y limpio
        """
        if df.empty:
            return df
        
        # PASO 1: Normalizar columnas (como en el sistema original)
        df = self._normalizar_columnas_biometricos(df)
        
        # PASO 2: Limpiar registros vacíos
        df = df.dropna(subset=["nombre_usuario"])
        df = df[df["nombre_usuario"].str.strip() != ""]
        
        # PASO 3: Parse fecha/hora (como en _parse_fecha_hora)
        df = self._parse_fecha_hora_biometricos(df)
        
        # PASO 4: Agregar día en español (como en _add_dia_es)
        df = self._add_dia_espanol(df)
        
        # PASO 5: Eliminar duplicados exactos (como en _drop_exact_dupes)
        df = self._eliminar_duplicados_exactos(df)
        
        # PASO 6: Aplicar filtro de ventana temporal (como en _window_filter)
        df = self._aplicar_filtro_ventana_temporal(df)
        
        # PASO 7: Normalizar códigos de docente (como en _normalizar_docente)
        df = self._normalizar_codigos_docente(df)
        
        # PASO 8: Agregar información de facultad
        df['facultad_codigo'] = facultad_codigo
        df['facultad_nombre'] = get_facultad_config(facultad_codigo)['nombre']
        
        # PASO 9: Seleccionar columnas finales (como en el sistema original)
        columnas_finales = ["fecha", "hora", "id_usuario", "dia", "docente", "docente_codigo", "facultad_codigo"]
        columnas_disponibles = [col for col in columnas_finales if col in df.columns]
        df = df[columnas_disponibles]
        
        return df
    
    def validar_conectividad_todas_facultades(self) -> Dict[str, Tuple[bool, str]]:
        """
        Valida la conectividad con todas las facultades funcionales.
        
        Returns:
            Dict con resultados de conectividad por facultad
        """
        resultados = {}
        
        facultades_funcionales = [
            codigo for codigo, config in FACULTADES_CONFIG.items() 
            if config["funcional"]
        ]
        
        for facultad in facultades_funcionales:
            conectado, mensaje = self.conectar_dispositivo(facultad)
            resultados[facultad] = (conectado, mensaje)
        
        return resultados
    
    def obtener_estadisticas_conexion(self, resultados_conectividad: Dict) -> Dict:
        """
        Obtiene estadísticas de los resultados de conectividad.
        
        Args:
            resultados_conectividad: Resultados del método validar_conectividad_todas_facultades
        
        Returns:
            Dict con estadísticas
        """
        total = len(resultados_conectividad)
        exitosas = sum(1 for conectado, _ in resultados_conectividad.values() if conectado)
        fallidas = total - exitosas
        
        return {
            "total_facultades": total,
            "conexiones_exitosas": exitosas,
            "conexiones_fallidas": fallidas,
            "porcentaje_exito": (exitosas / total * 100) if total > 0 else 0,
            "facultades_disponibles": [
                fac for fac, (conectado, _) in resultados_conectividad.items() 
                if conectado
            ],
            "facultades_no_disponibles": [
                fac for fac, (conectado, _) in resultados_conectividad.items() 
                if not conectado
            ]
        }
    
    def cerrar_conexiones(self):
        """Cierra todas las conexiones activas."""
        if hasattr(self, 'session'):
            self.session.close()
            self.logger.info("Conexiones biométricas cerradas")
    
    # =============================================================================
    # MÉTODOS AUXILIARES DE NORMALIZACIÓN (MIGRADOS DEL SISTEMA ORIGINAL)
    # =============================================================================
    
    def _normalizar_columnas_biometricos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza nombres de columnas biométricas.
        Migrado de _normalize_columns del sistema original.
        """
        import re
        from unidecode import unidecode
        
        def limpiar_nombre_columna(s: str) -> str:
            s = unidecode((s or "")).lower().strip()
            s = s.replace("(", "").replace(")", "").replace(".", "_")
            s = re.sub(r"\s+", "_", s)
            return s
        
        df = df.copy()
        df.columns = [limpiar_nombre_columna(c) for c in df.columns]
        
        # Mapeo de columnas comunes en biométricos
        mapeo = {}
        for col in df.columns:
            if col in ["usuario", "user_id", "id_usuario", "id_user"]:
                mapeo[col] = "id_usuario"
            elif col in ["nome_usuario", "nome", "name", "usuario_nome"]:
                mapeo[col] = "nombre_usuario"
            elif col in ["time", "timestamp", "fecha_hora", "datetime"]:
                mapeo[col] = "fecha_hora"
            elif col in ["location", "local", "ubicacion", "portal"]:
                mapeo[col] = "ubicacion"
        
        df = df.rename(columns=mapeo)
        
        # Validar que tenemos columnas mínimas requeridas
        required = {"id_usuario", "nombre_usuario", "fecha_hora"}
        if not required.issubset(df.columns):
            faltan = required - set(df.columns)
            self.logger.warning(f"Faltan columnas biométricas: {faltan}. Disponibles: {df.columns.tolist()}")
        
        return df
    
    def _parse_fecha_hora_biometricos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Procesa columna fecha_hora y crea campos fecha y hora separados.
        Migrado de _parse_fecha_hora del sistema original.
        """
        df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], dayfirst=True, errors="coerce")
        df["fecha"] = df["fecha_hora"].dt.date
        df["hora"] = df["fecha_hora"].dt.time
        return df
    
    def _add_dia_espanol(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Agrega columna 'dia' con día de semana en español.
        Migrado de _add_dia_es del sistema original.
        """
        mapeo_dias = {
            0: "Lunes", 1: "Martes", 2: "Miércoles", 
            3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"
        }
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["dia"] = df["fecha"].dt.dayofweek.map(mapeo_dias)
        df["fecha"] = df["fecha"].dt.date
        return df
    
    def _eliminar_duplicados_exactos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Elimina registros duplicados exactos por fecha, hora, id_usuario y nombre.
        Migrado de _drop_exact_dupes del sistema original.
        """
        df = df.drop_duplicates(
            subset=["fecha", "hora", "id_usuario", "nombre_usuario"], 
            keep="first"
        ).reset_index(drop=True)
        return df
    
    def _aplicar_filtro_ventana_temporal(self, df: pd.DataFrame, ventana_min: int = 45) -> pd.DataFrame:
        """
        Aplica filtro de ventana temporal para eliminar registros muy cercanos.
        Migrado de _window_filter del sistema original.
        
        Args:
            df: DataFrame con registros
            ventana_min: Minutos mínimos entre registros del mismo usuario
        """
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["ts"] = pd.to_datetime(df["fecha"].astype(str) + " " + df["hora"].astype(str))

        def filtrar_ventana(grupo):
            # Ordenar por timestamp antes de filtrar
            grupo = grupo.sort_values("ts")
            keep, ultima = [], None
            for ts in grupo["ts"]:
                if ultima is None or ts > ultima + timedelta(minutes=ventana_min):
                    keep.append(True)
                    ultima = ts
                else:
                    keep.append(False)
            return pd.Series(keep, index=grupo.index)

        mask = df.groupby(["id_usuario", "fecha"]).apply(filtrar_ventana).reset_index(level=[0,1], drop=True)
        df = df[mask].reset_index(drop=True)
        df = df.drop(columns=["ts"])
        df["fecha"] = df["fecha"].dt.date
        df = df.sort_values(["fecha", "id_usuario", "hora"]).reset_index(drop=True)
        return df
    
    def _normalizar_codigo_docente(self, codigo_id: str) -> str:
        """
        Normaliza código de docente individual.
        Migrado de _normalizar_codigo_docente del sistema original.
        """
        if pd.isna(codigo_id) or str(codigo_id).strip() == "":
            return "0000"
        
        codigo_str = str(codigo_id).strip()
        
        # Si es formato largo (más de 6 dígitos), tomar los últimos 4
        if len(codigo_str) > 6:
            codigo_normalizado = codigo_str[-4:]
        elif len(codigo_str) >= 4:
            # Si ya tiene 4-6 dígitos, usar tal como está (truncar a 4)
            codigo_normalizado = codigo_str[-4:]
        else:
            # Si tiene menos de 4 dígitos, hacer padding con ceros a la izquierda
            codigo_normalizado = codigo_str.zfill(4)
        
        return codigo_normalizado
    
    def _normalizar_codigos_docente(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Crea campos necesarios para matching por código y visualización por nombre.
        Migrado de _normalizar_docente del sistema original.
        """
        from unidecode import unidecode
        
        # MANTENER: Nombre del docente para mostrar en reportes
        df["docente"] = (
            df["nombre_usuario"].astype(str)
            .str.strip()
            .str.upper()
            .apply(unidecode)
            .str.replace(r"\s+", " ", regex=True)
        )
        
        # NUEVO: Código de docente para matching interno
        if "id_usuario" in df.columns:
            df["cod_docente"] = df["id_usuario"].apply(self._normalizar_codigo_docente)
            # Campo para matching interno (usado en procesamiento)
            df["docente_codigo"] = df["cod_docente"]
            self.logger.debug(f"Códigos generados: {df['docente_codigo'].head(3).tolist()}")
        else:
            self.logger.warning("Campo 'id_usuario' no encontrado. Usando nombres como fallback")
            df["docente_codigo"] = df["docente"]  # Fallback al nombre
        
        return df