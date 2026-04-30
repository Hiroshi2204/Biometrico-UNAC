"""
Gestor de datos de horarios académicos del sistema UNAC.

Maneja la lectura y procesamiento de archivos Excel con horarios académicos.
Reemplaza y mejora funcionalidades dispersas en el sistema original.
"""

import pandas as pd
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple, Any, Set
import logging
from pathlib import Path

from ...config import (
    ESCUELAS_CONFIG,
    PROCESAMIENTO_CONFIG,
    SISTEMA_CONFIG,
    get_escuela_config,
    normalizar_nombre_escuela,
    validate_escuela
)


class HorarioDataManager:
    """
    Gestor principal para datos de horarios académicos.
    
    Responsabilidades:
    - Lectura de archivos Excel con horarios
    - Validación y normalización de datos de horarios
    - Filtrado por escuela específica
    - Manejo de cursos compartidos entre escuelas
    """
    
    def __init__(self):
        """Inicializa el gestor de datos de horarios."""
        self.logger = logging.getLogger(__name__)
        self.horarios_cache = {}  # Cache para evitar releer archivos
        self.columnas_requeridas = PROCESAMIENTO_CONFIG["columnas_requeridas_horario"]
    
    def cargar_horarios_desde_excel(
        self, 
        ruta_archivo: str,
        hoja: str = None,
        forzar_recarga: bool = False
    ) -> Tuple[bool, pd.DataFrame, str]:
        """
        Carga horarios desde un archivo Excel.
        
        Args:
            ruta_archivo: Ruta al archivo Excel
            hoja: Nombre de la hoja (usa la primera si no se especifica)
            forzar_recarga: Si True, ignora cache y recarga archivo
        
        Returns:
            Tupla (exito, dataframe_horarios, mensaje)
        """
        ruta_archivo = str(Path(ruta_archivo).resolve())
        cache_key = f"{ruta_archivo}:{hoja or 'default'}"
        
        # Verificar cache
        if not forzar_recarga and cache_key in self.horarios_cache:
            df_cache = self.horarios_cache[cache_key]
            self.logger.info(f"Horarios cargados desde cache: {len(df_cache)} registros")
            return True, df_cache.copy(), f"Cargados {len(df_cache)} horarios desde cache"
        
        try:
            # Verificar que el archivo existe
            if not Path(ruta_archivo).exists():
                return False, pd.DataFrame(), f"Archivo no encontrado: {ruta_archivo}"
            
            # Verificar extensión
            extensiones_validas = SISTEMA_CONFIG["extensiones_permitidas"]
            if not any(ruta_archivo.lower().endswith(ext) for ext in extensiones_validas):
                return False, pd.DataFrame(), f"Extensión no válida. Permitidas: {extensiones_validas}"
            
            # Leer archivo Excel EXACTO como en el sistema original
            if hoja:
                df = pd.read_excel(ruta_archivo, sheet_name=hoja, dtype={"COD_DOC": str}, engine="openpyxl")
            else:
                df = pd.read_excel(ruta_archivo, dtype={"COD_DOC": str}, engine="openpyxl")
            
            if df.empty:
                return False, pd.DataFrame(), "El archivo está vacío"
            
            # Normalizar datos
            df_normalizado = self._normalizar_datos_horarios(df)
            
            # Validar estructura
            es_valido, mensaje_validacion = self._validar_estructura_horarios(df_normalizado)
            if not es_valido:
                return False, pd.DataFrame(), f"Error en estructura: {mensaje_validacion}"
            
            # Guardar en cache
            self.horarios_cache[cache_key] = df_normalizado.copy()
            
            self.logger.info(f"Horarios cargados exitosamente: {len(df_normalizado)} registros")
            return True, df_normalizado, f"Cargados {len(df_normalizado)} horarios exitosamente"
            
        except Exception as e:
            error_msg = f"Error cargando horarios desde {ruta_archivo}: {str(e)}"
            self.logger.error(error_msg)
            return False, pd.DataFrame(), error_msg
    
    def filtrar_horarios_por_escuela(
        self, 
        df_horarios: pd.DataFrame, 
        codigo_escuela: str,
        incluir_compartidos: bool = True
    ) -> Tuple[bool, pd.DataFrame, str]:
        """
        Filtra horarios para una escuela específica.
        
        Args:
            df_horarios: DataFrame con todos los horarios
            codigo_escuela: Código de la escuela a filtrar
            incluir_compartidos: Si incluir cursos compartidos con otras escuelas
        
        Returns:
            Tupla (exito, dataframe_filtrado, mensaje)
        """
        # Validar escuela
        es_valida, mensaje = validate_escuela(codigo_escuela)
        if not es_valida:
            return False, pd.DataFrame(), mensaje
        
        try:
            if df_horarios.empty:
                return False, pd.DataFrame(), "DataFrame de horarios está vacío"
            
            # Obtener configuración de escuela
            config_escuela = get_escuela_config(codigo_escuela)
            nombre_escuela = config_escuela["nombre"]
            
            # Filtrar por escuela específica
            df_filtrado = df_horarios[
                df_horarios["ESCUELA_NORMALIZADA"] == codigo_escuela
            ].copy()
            
            registros_directos = len(df_filtrado)
            
            # Agregar cursos compartidos si está habilitado
            if incluir_compartidos:
                df_compartidos = self._obtener_cursos_compartidos(df_horarios, codigo_escuela)
                if not df_compartidos.empty:
                    df_filtrado = pd.concat([df_filtrado, df_compartidos], ignore_index=True)
            
            registros_totales = len(df_filtrado)
            registros_compartidos = registros_totales - registros_directos
            
            if df_filtrado.empty:
                return False, pd.DataFrame(), f"No se encontraron horarios para {nombre_escuela}"
            
            # Ordenar por día y hora
            df_filtrado = self._ordenar_horarios(df_filtrado)
            
            mensaje = f"Filtrados {registros_totales} horarios para {nombre_escuela}"
            if registros_compartidos > 0:
                mensaje += f" ({registros_directos} directos + {registros_compartidos} compartidos)"
            
            return True, df_filtrado, mensaje
            
        except Exception as e:
            error_msg = f"Error filtrando horarios para {codigo_escuela}: {str(e)}"
            self.logger.error(error_msg)
            return False, pd.DataFrame(), error_msg
    
    def obtener_horarios_por_dia(
        self, 
        df_horarios: pd.DataFrame, 
        dia: str
    ) -> pd.DataFrame:
        """
        Filtra horarios por día específico.
        
        Args:
            df_horarios: DataFrame con horarios
            dia: Día de la semana (LUNES, MARTES, etc.)
        
        Returns:
            DataFrame filtrado por día
        """
        dia_normalizado = dia.upper().strip()
        
        if dia_normalizado not in PROCESAMIENTO_CONFIG["dias_semana"]:
            self.logger.warning(f"Día no válido: {dia}. Válidos: {PROCESAMIENTO_CONFIG['dias_semana']}")
            return pd.DataFrame()
        
        return df_horarios[df_horarios["dia_name"] == dia_normalizado].copy()
    
    def obtener_docentes_por_escuela(self, df_horarios: pd.DataFrame) -> Dict[str, Set[str]]:
        """
        Obtiene lista de docentes por escuela.
        
        Args:
            df_horarios: DataFrame con horarios
        
        Returns:
            Dict con escuela -> set de docentes
        """
        docentes_por_escuela = {}
        
        for escuela in df_horarios["ESCUELA_NORMALIZADA"].unique():
            docentes = set(df_horarios[
                df_horarios["ESCUELA_NORMALIZADA"] == escuela
            ]["docente"].unique())
            docentes_por_escuela[escuela] = docentes
        
        return docentes_por_escuela
    
    def obtener_cursos_por_escuela(self, df_horarios: pd.DataFrame) -> Dict[str, Set[str]]:
        """
        Obtiene lista de cursos por escuela.
        
        Args:
            df_horarios: DataFrame con horarios
        
        Returns:
            Dict con escuela -> set de cursos
        """
        cursos_por_escuela = {}
        
        for escuela in df_horarios["ESCUELA_NORMALIZADA"].unique():
            cursos = set(df_horarios[
                df_horarios["ESCUELA_NORMALIZADA"] == escuela
            ]["curso"].unique())
            cursos_por_escuela[escuela] = cursos
        
        return cursos_por_escuela
    
    def validar_horarios_fecha(
        self, 
        df_horarios: pd.DataFrame, 
        fecha_objetivo: str
    ) -> Tuple[bool, str]:
        """
        Valida si los horarios son aplicables para una fecha específica.
        
        Args:
            df_horarios: DataFrame con horarios
            fecha_objetivo: Fecha en formato 'YYYY-MM-DD'
        
        Returns:
            Tupla (es_aplicable, mensaje)
        """
        try:
            fecha_obj = datetime.strptime(fecha_objetivo, "%Y-%m-%d")
            dia_semana = fecha_obj.strftime("%A").upper()
            
            # Mapeo de días en inglés a español
            mapeo_dias = {
                "MONDAY": "LUNES",
                "TUESDAY": "MARTES", 
                "WEDNESDAY": "MIERCOLES",
                "THURSDAY": "JUEVES",
                "FRIDAY": "VIERNES",
                "SATURDAY": "SABADO",
                "SUNDAY": "DOMINGO"
            }
            
            dia_es = mapeo_dias.get(dia_semana, dia_semana)
            
            if dia_es not in PROCESAMIENTO_CONFIG["dias_semana"]:
                return False, f"La fecha {fecha_objetivo} ({dia_es}) no corresponde a un día académico"
            
            # Verificar si hay horarios para ese día
            horarios_dia = df_horarios[df_horarios["dia_name"] == dia_es]
            if horarios_dia.empty:
                return False, f"No hay horarios programados para {dia_es}"
            
            return True, f"Horarios válidos para {dia_es} ({fecha_objetivo})"
            
        except ValueError:
            return False, f"Formato de fecha inválido: {fecha_objetivo}. Use YYYY-MM-DD"
    
    def _normalizar_datos_horarios(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza los datos de horarios leídos del Excel.
        Migra la lógica de normalización del sistema original.
        
        Args:
            df: DataFrame crudo desde Excel
        
        Returns:
            DataFrame normalizado
        """
        df = df.copy()
        
        # Limpiar nombres de columnas (mantener mayúsculas)
        df.columns = df.columns.str.strip().str.upper()
        
        # Eliminar filas completamente vacías
        df = df.dropna(how='all')
        
        # PASO 1: Aplicar normalización completa EXACTA del sistema original
        df = self._aplicar_normalizacion_columnas_original(df)
        df = self._aplicar_normalizacion_valores_original(df)
        
        # PASO 2: Crear columna de escuela normalizada para filtrado
        if "escuela" in df.columns:
            df["ESCUELA_NORMALIZADA"] = df["escuela"].apply(
                lambda x: normalizar_nombre_escuela(x) or x
            )
        
        # PASO 3: Eliminar registros con datos críticos faltantes (usar nombres normalizados)
        columnas_criticas = []
        for col in ["escuela", "docente", "dia_name", "h_inicio", "h_fin"]:
            if col in df.columns:
                columnas_criticas.append(col)
        
        if columnas_criticas:
            df = df.dropna(subset=columnas_criticas)
        
        return df
    
    def _normalizar_hora(self, serie_hora: pd.Series) -> pd.Series:
        """
        Normaliza una serie de horas a formato HH:MM.
        
        Args:
            serie_hora: Serie de pandas con horas en diversos formatos
        
        Returns:
            Serie normalizada a formato HH:MM
        """
        def procesar_hora(valor_hora):
            if pd.isna(valor_hora):
                return None
            
            try:
                # Si ya es un objeto time
                if isinstance(valor_hora, time):
                    return valor_hora.strftime("%H:%M")
                
                # Si es string
                if isinstance(valor_hora, str):
                    valor_hora = valor_hora.strip()
                    
                    # Formato HH:MM
                    if ":" in valor_hora:
                        return valor_hora
                    
                    # Formato HHMM (4 dígitos)
                    if len(valor_hora) == 4 and valor_hora.isdigit():
                        return f"{valor_hora[:2]}:{valor_hora[2:]}"
                    
                    # Otros formatos de tiempo
                    hora_obj = pd.to_datetime(valor_hora, errors='coerce').time()
                    if hora_obj:
                        return hora_obj.strftime("%H:%M")
                
                # Si es numérico (Excel a veces convierte horas a decimal)
                if isinstance(valor_hora, (int, float)):
                    # Convertir decimal a tiempo (ej: 0.5 = 12:00)
                    if 0 <= valor_hora <= 1:
                        segundos_totales = int(valor_hora * 24 * 60 * 60)
                        horas = segundos_totales // 3600
                        minutos = (segundos_totales % 3600) // 60
                        return f"{horas:02d}:{minutos:02d}"
                
                return None
                
            except Exception:
                return None
        
        return serie_hora.apply(procesar_hora)
    
    def _validar_estructura_horarios(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Valida que el DataFrame tenga la estructura requerida.
        Compatible con la lógica del sistema original.
        
        Args:
            df: DataFrame a validar
        
        Returns:
            Tupla (es_valido, mensaje)
        """
        # Verificar columnas requeridas (solo las esenciales)
        columnas_faltantes = []
        for col in self.columnas_requeridas:
            if col not in df.columns:
                columnas_faltantes.append(col)
        
        if columnas_faltantes:
            return False, f"Columnas faltantes: {', '.join(columnas_faltantes)}"
        
        # Verificar que hay datos
        if df.empty:
            return False, "DataFrame no contiene datos"
        
        # Verificar que las horas tienen formato válido (solo si existen)
        for col in ["h_inicio", "h_fin"]:
            if col in df.columns:
                # Contar valores nulos o vacíos, pero permitir algunos
                valores_invalidos = df[df[col].isna() | (df[col] == "")]
                porcentaje_invalido = len(valores_invalidos) / len(df) * 100
                
                # Si más del 50% de las horas son inválidas, es un error
                if porcentaje_invalido > 50:
                    return False, f"Demasiadas horas inválidas en columna {col} ({porcentaje_invalido:.1f}%)"
        
        return True, "Estructura válida"
    
    def _obtener_cursos_compartidos(
        self, 
        df_horarios: pd.DataFrame, 
        codigo_escuela: str
    ) -> pd.DataFrame:
        """
        Detecta automáticamente cursos compartidos basándose en:
        - Mismo docente
        - Mismo horario (día, hora inicio, hora fin)
        - Misma aula
        
        Args:
            df_horarios: DataFrame completo de horarios
            codigo_escuela: Código de la escuela solicitante
        
        Returns:
            DataFrame con cursos compartidos detectados automáticamente
        """
        if df_horarios.empty:
            return pd.DataFrame()
        
        cursos_compartidos_detectados = []
        
        # Agrupar por criterios de curso compartido: docente + horario + aula
        criterios_agrupacion = ['docente_codigo', 'dia_name', 'h_inicio', 'h_fin', 'aula']
        
        # Verificar que las columnas necesarias existan
        columnas_faltantes = [col for col in criterios_agrupacion if col not in df_horarios.columns]
        if columnas_faltantes:
            self.logger.warning(f"No se pueden detectar cursos compartidos. Columnas faltantes: {columnas_faltantes}")
            return pd.DataFrame()
        
        # Agrupar por los criterios definidos
        grupos = df_horarios.groupby(criterios_agrupacion, dropna=False)
        
        for grupo_key, grupo_df in grupos:
            # Obtener escuelas únicas en este grupo
            escuelas_en_grupo = grupo_df['ESCUELA_NORMALIZADA'].unique()
            escuelas_en_grupo = [esc for esc in escuelas_en_grupo if pd.notna(esc)]
            
            # Si hay múltiples escuelas para el mismo docente+horario+aula
            if len(escuelas_en_grupo) > 1:
                # Verificar si la escuela solicitante está en este grupo
                if codigo_escuela in escuelas_en_grupo:
                    # Es un curso compartido - incluir TODAS las sesiones de este grupo
                    curso_compartido = grupo_df.copy()
                    curso_compartido["ES_COMPARTIDO"] = True
                    curso_compartido["ESCUELA_SOLICITANTE"] = codigo_escuela
                    curso_compartido["ESCUELAS_PARTICIPANTES"] = ", ".join(sorted(escuelas_en_grupo))
                    
                    self.logger.debug(
                        f"Curso compartido detectado: {grupo_key[0]} - {grupo_key[1]} {grupo_key[2]}-{grupo_key[3]} "
                        f"en {grupo_key[4]} (Escuelas: {', '.join(escuelas_en_grupo)})"
                    )
                    
                    cursos_compartidos_detectados.append(curso_compartido)
        
        if cursos_compartidos_detectados:
            resultado = pd.concat(cursos_compartidos_detectados, ignore_index=True)
            # Eliminar duplicados que puedan haberse generado
            resultado = resultado.drop_duplicates(
                subset=['docente_codigo', 'dia_name', 'h_inicio', 'h_fin', 'aula', 'ESCUELA_NORMALIZADA'],
                keep='first'
            )
            self.logger.info(
                f"Detectados {len(resultado)} registros de cursos compartidos para {codigo_escuela} "
                f"(basado en mismo docente + horario + aula)"
            )
            return resultado
        else:
            self.logger.debug(f"No se detectaron cursos compartidos para {codigo_escuela}")
            return pd.DataFrame()
    
    def _ordenar_horarios(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ordena horarios por día y hora de inicio.
        
        Args:
            df: DataFrame con horarios
        
        Returns:
            DataFrame ordenado
        """
        # Mapeo de días para ordenamiento
        orden_dias = {dia: i for i, dia in enumerate(PROCESAMIENTO_CONFIG["dias_semana"])}
        
        df = df.copy()
        df["ORDEN_DIA"] = df["dia_name"].map(orden_dias)
        
        # Ordenar por día y hora
        df = df.sort_values(["ORDEN_DIA", "h_inicio"]).drop("ORDEN_DIA", axis=1)
        
        return df.reset_index(drop=True)
    
    def _aplicar_normalizacion_columnas_original(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        COPIA EXACTA de _normalize_columns del sistema original.
        """
        import re
        from unidecode import unidecode
        
        def _canon(s: str) -> str:
            s = unidecode((s or "")).lower().strip()
            s = s.replace("(", "").replace(")", "").replace(".", "_")
            s = re.sub(r"\s+", "_", s)
            return s

        df = df.copy()
        df.columns = [_canon(c) for c in df.columns]
        ren = {}

        # Fechas de vigencia
        for cand in ["f_inicio", "f__inicio", "fecha_inicio"]:
            if cand in df.columns: ren[cand] = "f__inicio"
        for cand in ["f_fin", "f__fin", "fecha_fin"]:
            if cand in df.columns: ren[cand] = "f__fin"

        # Horas
        for cand in ["h_inicio", "h__inicio", "hora_inicio", "hora_de_inicio"]:
            if cand in df.columns: ren[cand] = "h_inicio"
        for cand in ["h_fin", "h__fin", "hora_fin", "hora_de_fin"]:
            if cand in df.columns: ren[cand] = "h_fin"

        # Docente y códigos
        for cand in ["docente", "nombre_docente", "profesor"]:
            if cand in df.columns: ren[cand] = "docente"
        for cand in ["cod_doc", "codigo_docente", "codigo_profesor"]:
            if cand in df.columns: ren[cand] = "cod_doc"

        # Curso y metadatos
        for cand in ["cod_cur", "codigo_curso", "cod_curso"]:
            if cand in df.columns: ren[cand] = "cod_cur"
        for cand in ["curso", "asignatura"]:
            if cand in df.columns: ren[cand] = "curso"
        for cand in ["ciclo", "semestre"]:
            if cand in df.columns: ren[cand] = "ciclo"
        for cand in ["aula", "salon", "sala"]:
            if cand in df.columns: ren[cand] = "aula"
        for cand in ["escuela", "escuela_profesional", "ep"]:
            if cand in df.columns: ren[cand] = "escuela"

        # ¡OJO! Aquí **NO** renombramos "facultad" a "esc".
        # 'esc' en tu Excel es el código numérico (1, 2, …).
        if "esc" not in df.columns and "esc" in [ _canon("ESC") ]:
            pass  # ya quedará como 'esc' por el _canon de 'ESC'

        # Día
        for cand in ["dia", "dia_name", "dia_semana_nombre"]:
            if cand in df.columns: ren[cand] = "dia_name"
        for cand in ["dia_semana", "dia_num"]:
            if cand in df.columns: ren[cand] = "dia_semana"

        df = df.rename(columns=ren)
        return df
    
    def _aplicar_normalizacion_valores_original(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        COPIA EXACTA de _normalize_values del sistema original.
        """
        from unidecode import unidecode
        
        # Necesitamos las constantes del sistema original
        MAP_ESCUELA_FACULTAD = {
            "ENFERMERÍA": "FCS",
            "ADMINISTRACIÓN": "FCA", 
            "CONTABILIDAD": "FCC",
            "ECONOMÍA": "FCE",
            "INGENIERÍA ELÉCTRICA": "FIEE",
            "INGENIERÍA ELECTRÓNICA": "FIEE",
            "INGENIERÍA DE SISTEMAS": "FIIS",
            "INGENIERÍA INDUSTRIAL": "FIIS",
            "INGENIERÍA MECÁNICA": "FIME",
            "INGENIERÍA EN ENERGÍA": "FIME",
            "INGENIERÍA PESQUERA": "FIPA",
            "INGENIERÍA DE ALIMENTOS": "FIPA",
            "INGENIERÍA QUÍMICA": "FIQ",
            "MATEMÁTICA": "FCNM",
            "FÍSICA": "FCNM",
            "INGENIERÍA AMBIENTAL Y DE RR.NN.": "FIARN",
            "EDUCACIÓN FÍSICA": "FCED",
        }
        
        NORM_MAP_ESCUELA_FACULTAD = {
            unidecode(k).upper().strip(): v for k, v in MAP_ESCUELA_FACULTAD.items()
        }
        
        MAP_DIAS_NUM_A_NOMBRE = {
            1: "Domingo", 2: "Lunes", 3: "Martes", 4: "Miércoles",
            5: "Jueves", 6: "Viernes", 7: "Sábado",
        }
        
        ABBR2FULL = {
            "LUN": "Lunes", "MAR": "Martes", "MIE": "Miércoles", "MIE.": "Miércoles", "MIÉ": "Miércoles",
            "JUE": "Jueves", "VIE": "Viernes", "SAB": "Sábado", "SÁB": "Sábado", "DOM": "Domingo",
        }
        
        df = df.copy()

        # MANTENER: Normalizar nombres de docente para mostrar en reportes
        if "docente" in df.columns:
            df["docente"] = (
                df["docente"].astype(str).str.strip().str.upper()
                .apply(unidecode).str.replace(r"\s+", " ", regex=True)
            )
        
        # NUEVO: Código de docente para matching interno
        if "cod_doc" in df.columns:
            # Normalizar códigos de docente (padding con ceros, últimos 4 dígitos)
            def normalizar_cod_docente(cod):
                if pd.isna(cod) or str(cod).strip() == "":
                    return "0000"
                cod_str = str(cod).strip()
                # Si el código tiene 6+ dígitos, tomar los últimos 4
                if len(cod_str) >= 4:
                    return cod_str[-4:]
                else:
                    # Padding con ceros a la izquierda para códigos cortos
                    return cod_str.zfill(4)
            
            df["cod_doc_norm"] = df["cod_doc"].apply(normalizar_cod_docente)
            # Campo para matching interno
            df["docente_codigo"] = df["cod_doc_norm"]
        else:
            print("⚠️  Advertencia: No se encontró 'cod_doc'. Usando nombres como fallback para matching.")
            df["docente_codigo"] = df["docente"] if "docente" in df.columns else "0000"

        # Escuela
        if "escuela" in df.columns:
            df["escuela"] = df["escuela"].astype(str).str.strip()

        # FACULTAD (código) desde ESCUELA
        def _fac_from_escuela(x):
            key = unidecode(str(x)).upper().strip()
            return NORM_MAP_ESCUELA_FACULTAD.get(key, None)

        df["facultad"] = df.get("escuela", pd.Series([None]*len(df))).map(_fac_from_escuela)

        # Día completo
        if "dia_name" in df.columns and df["dia_name"].notna().any():
            # Si viene abreviado (Lun, Mar, Mié...), expandir
            def _full_day(v):
                if pd.isna(v): return None
                s = unidecode(str(v)).upper().strip()[:3]
                return ABBR2FULL.get(s, v)
            df["dia_name"] = df["dia_name"].map(_full_day)
        elif "dia_semana" in df.columns:
            # Si viene numérico 1..7
            def _num_to_day(v):
                try:
                    return MAP_DIAS_NUM_A_NOMBRE.get(int(v), None)
                except Exception:
                    return None
            df["dia_name"] = df["dia_semana"].map(_num_to_day)

        # Fechas vigencia
        if "f__inicio" in df.columns:
            df["f__inicio"] = pd.to_datetime(df["f__inicio"], dayfirst=True, errors="coerce")
        if "f__fin" in df.columns:
            df["f__fin"] = pd.to_datetime(df["f__fin"], dayfirst=True, errors="coerce")

        # Horas (string hh:mm)
        if "h_inicio" in df.columns:
            df["h_inicio"] = df["h_inicio"].astype(str).str.strip()
        if "h_fin" in df.columns:
            df["h_fin"] = df["h_fin"].astype(str).str.strip()

        # Ciclo como texto sin ceros a la izquierda (opcional)
        if "ciclo" in df.columns:
            df["ciclo"] = df["ciclo"].astype(str).str.strip().str.lstrip("0").replace({"": "0"})

        # cod_doc como texto (conservar "0000" si existe)
        if "cod_doc" in df.columns:
            df["cod_doc"] = df["cod_doc"].astype(str).str.strip()

        # cod_cur como texto
        if "cod_cur" in df.columns:
            df["cod_cur"] = df["cod_cur"].astype(str).str.strip()

        return df
    
    def obtener_estadisticas_horarios(self, df_horarios: pd.DataFrame) -> Dict:
        """
        Obtiene estadísticas de los horarios cargados.
        
        Args:
            df_horarios: DataFrame con horarios
        
        Returns:
            Dict con estadísticas
        """
        if df_horarios.empty:
            return {"total_registros": 0}
        
        return {
            "total_registros": len(df_horarios),
            "escuelas_unicas": df_horarios["ESCUELA_NORMALIZADA"].nunique(),
            "docentes_unicos": df_horarios["docente"].nunique(),
            "cursos_unicos": df_horarios["curso"].nunique(),
            "dias_con_clases": df_horarios["dia_name"].nunique(),
            "escuelas_disponibles": sorted(df_horarios["ESCUELA_NORMALIZADA"].unique()),
            "dias_disponibles": sorted(df_horarios["dia_name"].unique())
        }
    
    def limpiar_cache(self):
        """Limpia el cache de horarios cargados."""
        self.horarios_cache.clear()
        self.logger.info("Cache de horarios limpiado")