"""
Generador de reportes del sistema biométrico UNAC.

Migra la lógica completa de generación de reportes del sistema original (controlid_reporte.py)
al sistema modular, manteniendo la funcionalidad exacta y el formato profesional.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging
import re
from pathlib import Path
from xlsxwriter.utility import xl_range, xl_col_to_name

from ...config import (
    REPORTE_CONFIG,
    SISTEMA_CONFIG,
    get_escuela_config,
    get_resumen_configuracion
)


class ReporteGenerator:
    """
    Generador principal de reportes de asistencia.
    
    Migra la lógica completa del sistema original (controlid_reporte.py) incluyendo:
    - Generación de 5 hojas Excel: Detalle_sesiones, Resumen_Observados, Resumen_Tardanzas, 
      Resumen_Faltas, Evidencia_Biometricos_RAW
    - Formato profesional con colores, bordes y anchos automáticos
    - Colapso de sesiones compartidas
    - Análisis de faltas por bloques continuos
    - Colores condicionales (rojo para faltas, amarillo para observados)
    """
    
    def __init__(self, directorio_salida: str = None):
        """
        Inicializa el generador de reportes.
        
        Args:
            directorio_salida: Directorio donde guardar reportes (usa config por defecto)
        """
        self.logger = logging.getLogger(__name__)
        self.directorio_salida = Path(directorio_salida or SISTEMA_CONFIG["directorio_reportes"])
        self.directorio_salida.mkdir(exist_ok=True, parents=True)
    
    def validar_reporte_existente(self, ruta_reporte: str) -> Tuple[bool, Dict, str]:
        """
        Valida y extrae información de un reporte Excel existente.
        
        Args:
            ruta_reporte: Ruta al archivo Excel del reporte
            
        Returns:
            Tupla (es_valido, estadisticas, mensaje)
        """
        try:
            ruta = Path(ruta_reporte)
            if not ruta.exists():
                return False, {}, f"Archivo no existe: {ruta_reporte}"
            
            # Leer hojas del Excel para validar estructura
            hojas_disponibles = pd.ExcelFile(ruta).sheet_names
            
            # Validar hojas esperadas usando configuración
            hojas_esperadas = list(REPORTE_CONFIG["hojas_excel"].values())[:4]  # Primeras 4 hojas principales
            hojas_faltantes = [h for h in hojas_esperadas if h not in hojas_disponibles]
            
            if hojas_faltantes:
                return False, {}, f"Reporte incompleto. Faltan hojas: {hojas_faltantes}"
            
            # Extraer estadísticas del reporte
            estadisticas = self._extraer_estadisticas_del_reporte(ruta)
            
            mensaje = f"Reporte válido con {estadisticas.get('total_horarios', 0)} registros"
            return True, estadisticas, mensaje
            
        except Exception as e:
            return False, {}, f"Error validando reporte: {str(e)}"
    
    def _extraer_estadisticas_del_reporte(self, ruta_excel: Path) -> Dict:
        """
        Extrae estadísticas de un reporte Excel generado por el sistema original.
        
        Args:
            ruta_excel: Path al archivo Excel
            
        Returns:
            Dict con estadísticas extraídas
        """
        try:
            # Leer la hoja de detalle principal
            df_detalle = pd.read_excel(ruta_excel, sheet_name="Detalle_sesiones")
            
            if df_detalle.empty:
                return self._estadisticas_vacias()
            
            # Analizar columna tardanza_txt para determinar estados (sistema original)
            total_horarios = len(df_detalle)
            
            # Usar el nombre de columna interno correcto
            col_tardanza = "tardanza_txt" if "tardanza_txt" in df_detalle.columns else None
            if col_tardanza is None:
                return self._estadisticas_vacias()
            
            # Contar estados según la lógica del sistema original
            a_tiempo = len(df_detalle[df_detalle[col_tardanza] == "A TIEMPO"])
            con_tardanza = len(df_detalle[df_detalle[col_tardanza].str.contains(r"\d+:\d+\s*min", na=False, regex=True)])
            sin_marca = len(df_detalle[df_detalle[col_tardanza] == "SIN MARCA"])
            observados = len(df_detalle[df_detalle[col_tardanza] == "OBSERVADO"])
            
            presentes_total = a_tiempo + con_tardanza
            
            return {
                "total_horarios": total_horarios,
                "presentes": presentes_total,
                "ausentes": sin_marca,
                "tardanzas": con_tardanza,
                "observados": observados,
                "a_tiempo": a_tiempo,
                "errores": 0,
                "porcentaje_asistencia": round((presentes_total / total_horarios * 100) if total_horarios > 0 else 0, 2),
                "porcentaje_ausencia": round((sin_marca / total_horarios * 100) if total_horarios > 0 else 0, 2),
                "docentes_unicos": df_detalle["docente"].nunique() if "docente" in df_detalle.columns else 0,
                "cursos_unicos": df_detalle["COD CUR"].nunique() if "COD CUR" in df_detalle.columns else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error extrayendo estadísticas del reporte: {e}")
            return self._estadisticas_vacias()
    
    def _estadisticas_vacias(self) -> Dict:
        """Retorna estructura de estadísticas vacía."""
        return {
            "total_horarios": 0,
            "presentes": 0,
            "ausentes": 0,
            "tardanzas": 0,
            "observados": 0,
            "a_tiempo": 0,
            "errores": 0,
            "porcentaje_asistencia": 0,
            "porcentaje_ausencia": 0,
            "docentes_unicos": 0,
            "cursos_unicos": 0
        }

    
    def generar_reporte_completo(
        self,
        df_procesado: pd.DataFrame,
        estadisticas: Dict,
        codigo_escuela: str,
        fecha: str,
        df_biometricos_raw: pd.DataFrame = None,
        nombre_archivo: str = None
    ) -> Tuple[bool, str, str]:
        """
        Genera reporte Excel completo con lógica migrada del sistema original.
        
        Implementa exactamente la misma funcionalidad de controlid_reporte.py:
        - 5 hojas Excel con formato profesional
        - Colapso de sesiones compartidas
        - Análisis de bloques de faltas
        - Colores condicionales y formato automático
        
        Args:
            df_procesado: DataFrame con datos procesados por AsistenciaProcessor
            estadisticas: Estadísticas calculadas
            codigo_escuela: Código de la escuela
            fecha: Fecha del reporte
            df_biometricos_raw: DataFrame con datos biométricos RAW (opcional)
            nombre_archivo: Nombre personalizado del archivo (opcional)
        
        Returns:
            Tupla (exito, ruta_archivo, mensaje)
        """
        try:
            # Crear carpeta por fecha
            carpeta_fecha = self.directorio_salida / fecha
            carpeta_fecha.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre de archivo si no se proporciona
            if not nombre_archivo:
                config_escuela = get_escuela_config(codigo_escuela)
                nombre_escuela = config_escuela["nombre"]
                nombre_archivo = f"{fecha}-reporte de asistencia-{nombre_escuela}.xlsx"
            
            ruta_reporte = carpeta_fecha / nombre_archivo
            
            # === PASO 1: Preparar DataFrame de detalle base ===
            df_rep_base = self._preparar_dataframe_base(df_procesado)
            
            # === PASO 2: Colapso de sesiones compartidas (lógica original) ===
            df_rep_base = self._colapsar_sesiones_compartidas(df_rep_base)
            
            # === PASO 3: Aplicar blanqueo visual para cursos corridos ===
            df_reporte_detallado = self._aplicar_blancos_mismo_curso(df_rep_base)
            
            # === PASO 4: Generar resúmenes especializados ===
            df_resumen_observados = self._generar_resumen_observados(df_reporte_detallado)
            df_resumen_tardanzas = self._generar_resumen_tardanzas(df_reporte_detallado)
            df_resumen_faltas = self._generar_resumen_faltas(df_reporte_detallado)
            
            # === PASO 5: Preparar datos biométricos RAW ===
            df_evidencia_raw = df_biometricos_raw.copy() if df_biometricos_raw is not None else pd.DataFrame()
            
            # === PASO 6: Generar Excel con formato profesional exacto ===
            self._generar_excel_formato_original(
                ruta_reporte,
                df_reporte_detallado,
                df_resumen_observados,
                df_resumen_tardanzas,
                df_resumen_faltas,
                df_evidencia_raw
            )
            
            mensaje = f"Reporte Excel generado exitosamente: {ruta_reporte.name}"
            self.logger.info(mensaje)
            return True, str(ruta_reporte), mensaje
            
        except Exception as e:
            error_msg = f"Error generando reporte Excel: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, "", error_msg

    def _preparar_dataframe_base(self, df_procesado: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara el DataFrame base con todas las columnas necesarias (migrado del original).
        """
        if df_procesado.empty:
            return pd.DataFrame()
        
        df_base = df_procesado.copy()
        
        # Asegurar columnas requeridas
        columnas_requeridas = [
            "esc", "escuela", "cod_cur", "cod_doc", "docente", "aula",
            "hora_entrada", "hora_salida", "entrada_marcada_str", "salida_marcada_str",
            "tardanza_txt", "evid_salida_fuera", "evid_ref", "delta_salida_vs_fin",
            "fecha", "start_dt", "end_dt", "bloque_id"
        ]
        
        for col in columnas_requeridas:
            if col not in df_base.columns:
                df_base[col] = ""
        
        return df_base

    def _colapsar_sesiones_compartidas(self, df_rep_base: pd.DataFrame) -> pd.DataFrame:
        """
        Colapsa sesiones compartidas usando la lógica exacta del sistema original.
        """
        if df_rep_base.empty:
            return df_rep_base
        
        # Convertir esc a numérico para ordenamiento
        df_rep_base["esc_num"] = pd.to_numeric(df_rep_base.get("esc", pd.Series(index=df_rep_base.index)), errors="coerce")
        
        # Claves de agrupación para detectar sesiones compartidas
        gkeys = ["fecha", "docente", "aula", "start_dt", "end_dt"]
        for k in gkeys:
            if k not in df_rep_base.columns:
                df_rep_base[k] = None

        idx_keep = []
        compartido_flag = pd.Series(False, index=df_rep_base.index)
        merged_schools = {}
        merged_codes   = {}

        # Agrupar y procesar sesiones compartidas
        for key, g in df_rep_base.groupby(gkeys, dropna=False):
            is_shared = (len(g) > 1) and (g["escuela"].nunique(dropna=False) > 1 or g["cod_cur"].nunique(dropna=False) > 1)
            
            if is_shared:
                # Ordenar por esc_num y tomar el último
                g_ord = g.sort_values(["esc_num"], na_position="first")
                keep = g_ord.index[-1]
                compartido_flag.loc[keep] = True
            else:
                keep = g.index[0]
            
            idx_keep.append(keep)

            # Mergear escuelas y códigos
            escuelas = sorted(set(g["escuela"].astype(str).str.strip()))
            cods     = sorted(set(g["cod_cur"].astype(str).str.strip()))
            merged_schools[key] = "\n".join([e for e in escuelas if e])
            merged_codes[key]   = " - ".join([c for c in cods if c])

        # Aplicar colapso
        df_rep_base = df_rep_base.loc[idx_keep].copy()
        df_rep_base["compartido"] = compartido_flag.loc[idx_keep].values

        def _key_row(r):
            return (r.get("fecha"), r.get("docente"), r.get("aula"), r.get("start_dt"), r.get("end_dt"))

        df_rep_base["__key"] = df_rep_base.apply(_key_row, axis=1)
        df_rep_base["escuela_out"] = df_rep_base["__key"].map(merged_schools).fillna(df_rep_base["escuela"])
        df_rep_base["cod_cur_out"] = df_rep_base["__key"].map(merged_codes).fillna(df_rep_base["cod_cur"])
        df_rep_base.drop(columns=["__key"], inplace=True)

        return df_rep_base

    def _aplicar_blancos_mismo_curso(self, df_rep_base: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica blanqueo visual para cursos corridos usando lógica del sistema original.
        """
        if df_rep_base.empty:
            return df_rep_base
        
        # Mapear columnas finales del detalle
        detalle_cols = [
            ("esc", "ESC"),
            ("escuela_out", "ESCUELA"),
            ("cod_cur_out", "COD CUR"),
            ("cod_doc", "COD DOC"),
            ("docente", "DOCENTE"),
            ("aula", "AULA"),
            ("hora_entrada", "HORA ENTRADA"),
            ("hora_salida", "HORA SALIDA"),
            ("entrada_marcada_str", "REGISTRO ENTRADA"),
            ("salida_marcada_str", "REGISTRO SALIDA"),
            ("tardanza_txt", "TARDANZA"),
            ("evid_salida_fuera", "EVIDENCIA"),
            ("evid_ref", "REF EVIDENCIA"),
            ("delta_salida_vs_fin", "Δ VS REFERENCIA (MIN)"),
        ]
        
        df_reporte_detallado = pd.DataFrame({new: df_rep_base[old] if old in df_rep_base.columns else pd.Series([""] * len(df_rep_base)) for old, new in detalle_cols})
        
        
        # Ordenar por escuela, docente, hora
        df_reporte_detallado = (
            df_reporte_detallado
            .sort_values(["ESCUELA", "DOCENTE", "HORA ENTRADA"], kind="stable")
            .reset_index(drop=True)
        )
        
        # Aplicar blanqueo para cursos corridos contiguos
        df_reporte_detallado = self._aplicar_blanqueo_cursos_contiguos(df_reporte_detallado)
        
        return df_reporte_detallado
    
    def _aplicar_blanqueo_cursos_contiguos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica blanqueo visual para cursos del mismo código y aula que son contiguos.
        """
        df = df.copy()
        
        # Reconstruir timestamps para comparar contigüidad
        st = pd.to_datetime(df["HORA ENTRADA"], format="%H:%M", errors="coerce")
        en = pd.to_datetime(df["HORA SALIDA"], format="%H:%M", errors="coerce")
        df["__st"] = st
        df["__en"] = en

        # Procesar por combinación de docente/aula/curso
        for _, g in df.groupby(["DOCENTE", "AULA", "COD CUR"], dropna=False):
            if len(g) <= 1:
                continue
                
            g = g.sort_values(["__st", "__en", "HORA ENTRADA", "HORA SALIDA"])
            idxs = list(g.index)

            # Detectar contiguidad: inicio == fin anterior
            for i in range(1, len(idxs)):
                i_prev, i_curr = idxs[i-1], idxs[i]
                
                # Verificar si son contiguos
                if (pd.notna(df.loc[i_prev, "__en"]) and 
                    pd.notna(df.loc[i_curr, "__st"]) and 
                    df.loc[i_prev, "__en"] == df.loc[i_curr, "__st"]):
                    
                    # Blanquear salida del primero y entrada del segundo
                    df.loc[i_prev, "REGISTRO SALIDA"] = ""
                    df.loc[i_curr, "REGISTRO ENTRADA"] = ""

            # Para secuencias de 3 o más, blanquear intermedios completamente
            if len(idxs) >= 3:
                mids = idxs[1:-1]
                df.loc[mids, "REGISTRO ENTRADA"] = ""
                df.loc[mids, "REGISTRO SALIDA"] = ""
                df.loc[mids, "TARDANZA"] = ""

        df.drop(columns=["__st", "__en"], inplace=True)
        return df

    def _generar_resumen_observados(self, df_detalle: pd.DataFrame) -> pd.DataFrame:
        """
        Genera resumen de observados usando lógica del sistema original.
        """
        # Filtrar registros con observaciones
        col_tardanza = "TARDANZA"
        col_salida = "salida_marcada_str" if "salida_marcada_str" in df_detalle.columns else "REGISTRO SALIDA"
        
        tiene_observacion = (
            (df_detalle[col_tardanza].astype(str).str.upper() == 'OBSERVADO') |
            (df_detalle[col_salida].astype(str).str.upper() == 'OBSERVADO')
        )
        
        df_observados = df_detalle[tiene_observacion].copy()
        
        if df_observados.empty:
            return pd.DataFrame(columns=[
                "DOCENTE", "OBSERVACIONES", "CURSOS", "AULAS", "HORARIOS", "TIPOS DE OBSERVACION"
            ])
        
        # Determinar tipo de observación
        df_observados['TIPO_OBSERVACION'] = df_observados.apply(lambda row:
            'SIN ENTRADA' if row[col_tardanza] == 'OBSERVADO' else 'SIN SALIDA', axis=1)

        # Agrupar por docente
        df_resumen_observados = df_observados.groupby('DOCENTE').agg(
            observaciones=('DOCENTE', 'size'),
            cursos=('COD CUR', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))),
            aulas=('AULA', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))),
            horarios=('HORA ENTRADA', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))),
            tipos_observacion=('TIPO_OBSERVACION', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))))
        ).reset_index().rename(columns={
            'observaciones': 'OBSERVACIONES',
            'cursos': 'CURSOS',
            'aulas': 'AULAS',
            'horarios': 'HORARIOS',
            'tipos_observacion': 'TIPOS DE OBSERVACION'
        })
        
        return df_resumen_observados

    def _generar_resumen_tardanzas(self, df_detalle: pd.DataFrame) -> pd.DataFrame:
        """
        Genera resumen de tardanzas usando lógica del sistema original.
        """
        # Filtrar tardanzas (excluye observados)
        tiene_observacion = (
            (df_detalle['TARDANZA'].astype(str).str.upper() == 'OBSERVADO') |
            (df_detalle['REGISTRO SALIDA'].astype(str).str.upper() == 'OBSERVADO')
        )
        
        es_tardanza = (
            df_detalle['TARDANZA'].astype(str).str.contains(r'\d+:\d+\s*min', regex=True, na=False) &
            ~tiene_observacion
        )
        
        df_tardanzas_data = df_detalle[es_tardanza].copy()
        
        if df_tardanzas_data.empty:
            return pd.DataFrame(columns=[
                "DOCENTE", "TOTAL TARDANZAS", "MINUTOS TOTALES", "CURSOS", "AULAS", "HORARIOS"
            ])
        
        # Convertir MM:SS min a minutos decimales
        def convertir_mmss_a_minutos(tardanza_str):
            if pd.isna(tardanza_str):
                return 0
            match = re.search(r'(\d+):(\d+)\s*min', str(tardanza_str))
            if match:
                minutos = int(match.group(1))
                segundos = int(match.group(2))
                return minutos + segundos / 60.0
            return 0
        
        df_tardanzas_data['minutos'] = df_tardanzas_data['TARDANZA'].apply(convertir_mmss_a_minutos)

        df_resumen_tardanzas = df_tardanzas_data.groupby('DOCENTE').agg(
            total_tardanzas=('DOCENTE', 'size'),
            minutos_tardanza=('minutos', 'sum'),
            cursos=('COD CUR', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))),
            aulas=('AULA', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))),
            horarios=('HORA ENTRADA', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))))
        ).reset_index()

        # Convertir los minutos totales de vuelta a formato MM:SS
        def minutos_a_mmss(minutos_decimales):
            if pd.isna(minutos_decimales) or minutos_decimales == 0:
                return "0:00"
            total_mins = int(minutos_decimales)
            segundos = int((minutos_decimales - total_mins) * 60)
            return f"{total_mins}:{segundos:02d}"
        
        df_resumen_tardanzas['minutos_tardanza_formatted'] = df_resumen_tardanzas['minutos_tardanza'].apply(minutos_a_mmss)
        
        df_resumen_tardanzas = df_resumen_tardanzas.rename(columns={
            'total_tardanzas': 'TOTAL TARDANZAS',
            'minutos_tardanza_formatted': 'MINUTOS TOTALES',
            'cursos': 'CURSOS',
            'aulas': 'AULAS',
            'horarios': 'HORARIOS'
        })
        
        # Eliminar columnas temporales
        df_resumen_tardanzas = df_resumen_tardanzas.drop(columns=['minutos_tardanza'], errors='ignore')
        
        return df_resumen_tardanzas

    def _generar_resumen_faltas(self, df_detalle: pd.DataFrame) -> pd.DataFrame:
        """
        Genera resumen de faltas con análisis de bloques usando lógica del sistema original.
        """
        # Filtrar faltas (SIN MARCA)
        es_sin_marca = df_detalle['TARDANZA'].astype(str).str.upper() == 'SIN MARCA'
        df_faltas_raw = df_detalle[es_sin_marca].copy()

        if df_faltas_raw.empty:
            return pd.DataFrame(columns=[
                'DOCENTE', 'FALTAS', 'SESIONES PERDIDAS', 'CURSOS', 'AULAS', 'DETALLE DE FALTAS'
            ])

        # Analizar bloques de faltas continuas
        df_faltas_raw['HORA_ENTRADA_DT'] = pd.to_datetime(df_faltas_raw['HORA ENTRADA'], format='%H:%M', errors='coerce')
        df_faltas_raw['HORA_SALIDA_DT'] = pd.to_datetime(df_faltas_raw['HORA SALIDA'], format='%H:%M', errors='coerce')

        df_faltas_raw = df_faltas_raw.sort_values(['DOCENTE', 'COD CUR', 'HORA_ENTRADA_DT'])

        # Detectar continuidad
        df_faltas_raw['prev_docente'] = df_faltas_raw['DOCENTE'].shift(1)
        df_faltas_raw['prev_curso'] = df_faltas_raw['COD CUR'].shift(1)
        df_faltas_raw['prev_salida'] = df_faltas_raw['HORA_SALIDA_DT'].shift(1)

        df_faltas_raw['es_continuacion'] = (
            (df_faltas_raw['DOCENTE'] == df_faltas_raw['prev_docente']) &
            (df_faltas_raw['COD CUR'] == df_faltas_raw['prev_curso']) &
            (df_faltas_raw['HORA_ENTRADA_DT'] == df_faltas_raw['prev_salida'])
        )

        df_faltas_raw['nuevo_bloque'] = ~df_faltas_raw['es_continuacion']
        df_faltas_raw['bloque_falta_id'] = df_faltas_raw['nuevo_bloque'].cumsum()

        # Resumir bloques
        bloques_info = df_faltas_raw.groupby(['DOCENTE', 'bloque_falta_id']).agg(
            curso=('COD CUR', 'first'),
            aula=('AULA', 'first'),
            hora_inicio=('HORA ENTRADA', 'first'),
            hora_fin=('HORA SALIDA', 'last'),
            sesiones_perdidas=('DOCENTE', 'size')
        ).reset_index()

        bloques_info['DESCRIPCION_BLOQUE'] = (
            bloques_info['curso'] + ' (' +
            bloques_info['hora_inicio'] + '-' + bloques_info['hora_fin'] +
            ') ' + bloques_info['aula'] +
            ' [' + bloques_info['sesiones_perdidas'].astype(str) + ' sesiones]'
        )

        df_resumen_faltas = bloques_info.groupby('DOCENTE').agg(
            total_faltas=('bloque_falta_id', 'nunique'),
            total_sesiones_perdidas=('sesiones_perdidas', 'sum'),
            cursos=('curso', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))),
            aulas=('aula', lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))),
            bloques_detalle=('DESCRIPCION_BLOQUE', lambda x: ' | '.join(str(v) for v in x if pd.notna(v)))
        ).reset_index().rename(columns={
            'total_faltas': 'FALTAS',
            'total_sesiones_perdidas': 'SESIONES PERDIDAS',
            'cursos': 'CURSOS',
            'aulas': 'AULAS',
            'bloques_detalle': 'DETALLE DE FALTAS'
        })
        
        return df_resumen_faltas

    def _generar_excel_formato_original(
        self,
        ruta_archivo: Path,
        df_reporte_detallado: pd.DataFrame,
        df_resumen_observados: pd.DataFrame,
        df_resumen_tardanzas: pd.DataFrame,
        df_resumen_faltas: pd.DataFrame,
        df_evidencia_raw: pd.DataFrame
    ):
        """
        Genera Excel con formato profesional exacto del sistema original.
        """
        with pd.ExcelWriter(ruta_archivo, engine="xlsxwriter", datetime_format="dd/mm/yyyy") as xw:
            
            # Escribir todas las hojas usando nombres configurados
            nombres_hojas = REPORTE_CONFIG["hojas_excel"]
            df_reporte_detallado.to_excel(xw, index=False, sheet_name=nombres_hojas["detalle"])
            df_resumen_observados.to_excel(xw, index=False, sheet_name=nombres_hojas["observados"])
            df_resumen_tardanzas.to_excel(xw, index=False, sheet_name=nombres_hojas["tardanzas"])
            df_resumen_faltas.to_excel(xw, index=False, sheet_name=nombres_hojas["faltas"])
            df_evidencia_raw.to_excel(xw, index=False, sheet_name=nombres_hojas["evidencia_raw"])

            wb = xw.book
            
            # === FORMATEO EXACTO DEL SISTEMA ORIGINAL ===
            
            # Ajuste automático de columnas para "Detalle_sesiones"
            ws_detalle = wb.get_worksheet_by_name("Detalle_sesiones")
            if ws_detalle and not df_reporte_detallado.empty:
                for col_num, column in enumerate(df_reporte_detallado.columns):
                    header_width = len(str(column)) + 2
                    if not df_reporte_detallado[column].empty:
                        max_content = df_reporte_detallado[column].astype(str).str.len().max()
                        content_width = max_content + 2 if not pd.isna(max_content) else header_width
                    else:
                        content_width = header_width
                    optimal_width = min(max(header_width, content_width), 50)
                    ws_detalle.set_column(col_num, col_num, optimal_width)

            # Colores y formatos del sistema original
            blue_soft = "#D9E8FB"
            red_faltas = "#FFE6E6"
            yellow_observado = "#FFFACD"
            
            header_fmt = wb.add_format({
                "bold": True, "align": "center", "valign": "vcenter",
                "bg_color": blue_soft, "border": 1
            })
            center_fmt = wb.add_format({"align": "center", "valign": "vcenter"})
            border_all_fmt = wb.add_format({"border": 1})
            wrap_fmt = wb.add_format({"text_wrap": True, "valign": "vcenter"})
            wrap_center_fmt = wb.add_format({"text_wrap": True, "align": "center", "valign": "vcenter"})
            
            # Formatos para colores específicos
            faltas_fmt = wb.add_format({"bg_color": red_faltas, "border": 1})
            observado_fmt = wb.add_format({"bg_color": yellow_observado, "border": 1})

            # ===== FORMATEO HOJA PRINCIPAL DE DETALLE =====
            ws = xw.sheets[nombres_hojas["detalle"]]
            n_rows = len(df_reporte_detallado)
            n_cols = df_reporte_detallado.shape[1]

            # Headers con formato
            for ci, colname in enumerate(df_reporte_detallado.columns):
                ws.write(0, ci, colname, header_fmt)

            # Formateo específico por columnas
            if "ESCUELA" in df_reporte_detallado.columns:
                ci_escuela = df_reporte_detallado.columns.get_loc("ESCUELA")
                escuela_width = self._col_width_from_multiline(
                    df_reporte_detallado["ESCUELA"], min_w=18, max_w=45, padding=2
                )
                ws.set_column(ci_escuela, ci_escuela, escuela_width, wrap_fmt)

            if "COD CUR" in df_reporte_detallado.columns:
                ci_cod = df_reporte_detallado.columns.get_loc("COD CUR")
                cod_width = min(30, max(12, int(df_reporte_detallado["COD CUR"].astype(str).str.len().max() or 0) + 2))
                ws.set_column(ci_cod, ci_cod, cod_width, wrap_center_fmt)

            # Columnas de horarios y registros
            for col in ["HORA ENTRADA", "HORA SALIDA", "REGISTRO ENTRADA", "REGISTRO SALIDA", 
                       "TARDANZA", "EVIDENCIA", "REF EVIDENCIA", "Δ VS REFERENCIA (MIN)"]:
                if col in df_reporte_detallado.columns:
                    ci = df_reporte_detallado.columns.get_loc(col)
                    ancho = 22 if col == "EVIDENCIA" else (18 if col == "REF EVIDENCIA" else 14)
                    ws.set_column(ci, ci, ancho, center_fmt)

            # Bordes para todo el rango
            if n_rows > 0:
                full_range = xl_range(0, 0, n_rows, n_cols - 1)
                ws.conditional_format(full_range, {"type": "no_blanks", "format": border_all_fmt})
                ws.conditional_format(full_range, {"type": "blanks", "format": border_all_fmt})

            # === COLORES CONDICIONALES ===
            if n_rows > 0:
                # Color rojo para faltas (SIN MARCA)
                if 'TARDANZA' in df_reporte_detallado.columns:
                    tardanza_col = df_reporte_detallado.columns.get_loc('TARDANZA')
                    for row_idx, tardanza_val in enumerate(df_reporte_detallado['TARDANZA']):
                        if str(tardanza_val).upper() == 'SIN MARCA':
                            excel_row = row_idx + 1
                            row_range = xl_range(excel_row, 0, excel_row, n_cols - 1)
                            ws.conditional_format(row_range, {"type": "no_blanks", "format": faltas_fmt})
                            ws.conditional_format(row_range, {"type": "blanks", "format": faltas_fmt})
                
                # Color amarillo para observados
                for col in ['TARDANZA', 'REGISTRO SALIDA', 'REGISTRO ENTRADA']:
                    if col in df_reporte_detallado.columns:
                        col_idx = df_reporte_detallado.columns.get_loc(col)
                        for row_idx, cell_val in enumerate(df_reporte_detallado[col]):
                            if str(cell_val).upper() == 'OBSERVADO':
                                excel_row = row_idx + 1
                                cell_range = xl_range(excel_row, col_idx, excel_row, col_idx)
                                ws.conditional_format(cell_range, {"type": "no_blanks", "format": observado_fmt})

            # Ajustar columnas protegidas
            protected = {"ESCUELA", "COD CUR", "HORA ENTRADA", "HORA SALIDA",
                        "REGISTRO ENTRADA", "REGISTRO SALIDA", "TARDANZA",
                        "EVIDENCIA", "REF EVIDENCIA", "Δ VS REFERENCIA (MIN)"}
            for ci, col in enumerate(df_reporte_detallado.columns):
                if col in protected:
                    continue
                header_len = len(str(col))
                data_len = int(
                    df_reporte_detallado.iloc[:, ci]
                    .astype(str)
                    .str.len()
                    .clip(upper=35)
                    .max()
                    or 0
                )
                width = max(10, min(35, max(header_len, data_len) + 2))
                ws.set_column(ci, ci, width)

            # === FORMATEO PARA HOJAS DE RESUMEN ===
            def format_sheet(ws, df):
                if df.empty:
                    return
                n_rows, n_cols = df.shape
                for ci, colname in enumerate(df.columns):
                    ws.write(0, ci, colname, header_fmt)
                    max_len = max(
                        df[colname].astype(str).map(len).max(),
                        len(colname)
                    ) + 2
                    ws.set_column(ci, ci, max_len)

                if n_rows > 0:
                    full_range = xl_range(0, 0, n_rows, n_cols - 1)
                    ws.conditional_format(full_range, {"type": "no_blanks", "format": border_all_fmt})
                    ws.conditional_format(full_range, {"type": "blanks", "format": border_all_fmt})

            # Aplicar formato a todas las hojas de resumen
            format_sheet(xw.sheets[nombres_hojas["observados"]], df_resumen_observados)
            format_sheet(xw.sheets[nombres_hojas["tardanzas"]], df_resumen_tardanzas)
            format_sheet(xw.sheets[nombres_hojas["faltas"]], df_resumen_faltas)
            format_sheet(xw.sheets[nombres_hojas["evidencia_raw"]], df_evidencia_raw)

    def _col_width_from_multiline(self, series: pd.Series, min_w=18, max_w=45, padding=2) -> int:
        """
        Calcula ancho óptimo de columna para texto multilínea (del sistema original).
        """
        def max_line_len(s: str) -> int:
            if not isinstance(s, str):
                return 0
            lines = [ln for ln in s.splitlines() if ln]
            return max((len(ln) for ln in lines), default=0)
        
        max_chars = int(series.astype(str).map(max_line_len).max() or 0)
        width = max_chars + padding
        return max(min_w, min(max_w, width))

    def consolidar_reportes_multiples_fechas(
        self,
        rutas_reportes: List[str],
        codigo_escuela: str,
        nombre_archivo: str = None
    ) -> Tuple[bool, str, str]:
        """
        Consolida múltiples reportes de diferentes fechas en uno solo.
        
        Args:
            rutas_reportes: Lista de rutas a reportes Excel existentes
            codigo_escuela: Código de la escuela
            nombre_archivo: Nombre del archivo consolidado (opcional)
        
        Returns:
            Tupla (exito, ruta_archivo, mensaje)
        """
        try:
            # Para múltiples fechas, mantenemos los reportes separados
            # y creamos un resumen consolidado
            reportes_validos = []
            stats_consolidadas = self._estadisticas_vacias()
            
            for ruta in rutas_reportes:
                es_valido, stats, msg = self.validar_reporte_existente(ruta)
                if es_valido:
                    reportes_validos.append((ruta, stats))
                    # Sumar estadísticas
                    for key in ["total_horarios", "presentes", "ausentes", "tardanzas", "observados"]:
                        stats_consolidadas[key] += stats.get(key, 0)
            
            # Calcular porcentajes consolidados
            total = stats_consolidadas["total_horarios"]
            if total > 0:
                stats_consolidadas["porcentaje_asistencia"] = round(
                    (stats_consolidadas["presentes"] / total) * 100, 2
                )
                stats_consolidadas["porcentaje_ausencia"] = round(
                    (stats_consolidadas["ausentes"] / total) * 100, 2
                )
            
            mensaje = f"Consolidación exitosa de {len(reportes_validos)} reportes con {total} registros totales"
            self.logger.info(mensaje)
            
            # Para simplificar, retornamos las estadísticas consolidadas
            # Los reportes individuales permanecen separados
            return True, str(self.directorio_salida), mensaje
            
        except Exception as e:
            error_msg = f"Error consolidando reportes múltiples: {str(e)}"
            self.logger.error(error_msg)
            return False, "", error_msg
    
    def obtener_rutas_reportes_generados(self) -> List[str]:
        """
        Obtiene lista de reportes generados en el directorio de salida.
        
        Returns:
            Lista de rutas de archivos de reporte
        """
        patron = f"{SISTEMA_CONFIG['prefijo_reporte']}*.xlsx"
        return [str(archivo) for archivo in self.directorio_salida.glob(patron)]
    
    def limpiar_reportes_antiguos(self, dias_antiguedad: int = 30) -> int:
        """
        Limpia reportes antiguos del directorio de salida.
        
        Args:
            dias_antiguedad: Días de antigüedad para considerar archivos viejos
        
        Returns:
            Número de archivos eliminados
        """
        from datetime import timedelta
        
        limite_fecha = datetime.now() - timedelta(days=dias_antiguedad)
        archivos_eliminados = 0
        
        for archivo in self.obtener_rutas_reportes_generados():
            archivo_path = Path(archivo)
            if archivo_path.stat().st_mtime < limite_fecha.timestamp():
                try:
                    archivo_path.unlink()
                    archivos_eliminados += 1
                    self.logger.info(f"Archivo eliminado: {archivo}")
                except Exception as e:
                    self.logger.warning(f"No se pudo eliminar {archivo}: {str(e)}")
        
        return archivos_eliminados