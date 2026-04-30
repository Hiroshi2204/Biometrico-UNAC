"""
Procesador de asistencia del sistema biométrico UNAC.

Migra la lógica exacta del sistema original (controlid_reporte.py) al sistema modular.
Implementa el algoritmo de "pasada doble" para matching de entradas y salidas.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Any
import logging
import re
import math
from pathlib import Path
from unidecode import unidecode

from ...config import (
    PROCESAMIENTO_CONFIG,
    SISTEMA_CONFIG,
    get_escuela_config,
    get_facultad_config_for_escuela
)
from ..data import BiometricDataManager, HorarioDataManager

# Flag de comportamiento del algoritmo original
SUPRIMIR_FLAG_DETALLE_SI_BLOQUE_OK = True

# Mapeo de días
DIA2WK = {
    "LUNES": 0, "MARTES": 1, "MIERCOLES": 2, "MIÉRCOLES": 2,
    "JUEVES": 3, "VIERNES": 4, "SABADO": 5, "SÁBADO": 5, "DOMINGO": 6
}


class AsistenciaProcessor:
    """
    Procesador principal para calcular asistencias basado en datos biométricos y horarios.
    
    Migra la lógica exacta del sistema original (controlid_reporte.py) implementando:
    - Algoritmo de "pasada doble" para matching de entradas y salidas
    - Manejo de bloques de sesiones continuas
    - Cálculo de tardanzas con tolerancia
    - Detección de estados: A TIEMPO, TARDANZA, OBSERVADO, SIN MARCA
    """
    
    def __init__(self, biometric_manager: BiometricDataManager = None, 
                 horario_manager: HorarioDataManager = None):
        """
        Inicializa el procesador de asistencia.
        
        Args:
            biometric_manager: Gestor de datos biométricos (crea uno nuevo si None)
            horario_manager: Gestor de datos de horarios (crea uno nuevo si None)
        """
        self.biometric_manager = biometric_manager or BiometricDataManager()
        self.horario_manager = horario_manager or HorarioDataManager()
        self.logger = logging.getLogger(__name__)
        
        # Cargar parámetros del algoritmo desde configuración central
        self.tolerancia_minutos = PROCESAMIENTO_CONFIG["tolerancia_minutos"]
        self.ventana_entrada_antes = PROCESAMIENTO_CONFIG["ventana_entrada_antes_min"]
        self.ventana_entrada_despues = PROCESAMIENTO_CONFIG["ventana_entrada_despues_min"]
        self.ventana_salida_antes = PROCESAMIENTO_CONFIG["ventana_salida_antes_min"]
        self.ventana_salida_despues = PROCESAMIENTO_CONFIG["ventana_salida_despues_min"]
        self.adyacencia_bloques = PROCESAMIENTO_CONFIG["adyacencia_bloques_min"]
        self.formato_hora = PROCESAMIENTO_CONFIG["formato_hora"]
    
    def procesar_asistencia_escuela(
        self, 
        codigo_escuela: str,
        fecha: str,
        ruta_horarios: str,
        hoja_horarios: str = None
    ) -> Tuple[bool, pd.DataFrame, Dict, str]:
        """
        Procesa asistencia completa para una escuela usando la lógica migrada del sistema original.
        
        Implementa el algoritmo completo de "pasada doble" para matching de entradas y salidas.
        
        Args:
            codigo_escuela: Código de la escuela (ej: 'INGENIERIA_MECANICA')
            fecha: Fecha en formato 'YYYY-MM-DD'
            ruta_horarios: Ruta al archivo Excel con horarios
            hoja_horarios: Nombre de la hoja Excel (opcional)
        
        Returns:
            Tupla (exito, dataframe_procesado, estadisticas, mensaje, df_biometricos_raw)
        """
        try:
            self.logger.info(f"Iniciando procesamiento de asistencia para {codigo_escuela} - {fecha}")
            
            # 1. Cargar y validar horarios
            exito_horarios, df_horarios, msg_horarios = self.horario_manager.cargar_horarios_desde_excel(
                ruta_horarios, hoja_horarios
            )
            if not exito_horarios:
                return False, pd.DataFrame(), {}, f"Error cargando horarios: {msg_horarios}", pd.DataFrame()
            
            # 2. Filtrar horarios para la escuela
            exito_filtro, df_horarios_escuela, msg_filtro = self.horario_manager.filtrar_horarios_por_escuela(
                df_horarios, codigo_escuela
            )
            if not exito_filtro:
                return False, pd.DataFrame(), {}, f"Error filtrando horarios: {msg_filtro}", pd.DataFrame()
            
            # 3. Obtener datos biométricos desde dispositivos
            config_escuela = get_escuela_config(codigo_escuela)
            facultad_codigo = config_escuela["facultad_codigo"]
            
            exito_bio, df_biometricos, msg_bio = self.biometric_manager.obtener_registros_asistencia(
                facultad_codigo, fecha
            )
            
            if not exito_bio:
                error_msg = f"No se pudieron obtener datos biométricos: {msg_bio}"
                self.logger.error(error_msg)
                return False, pd.DataFrame(), {}, error_msg, pd.DataFrame()
            
            # 4. Procesar asistencia usando lógica migrada
            df_procesado, estadisticas = self._procesar_asistencia_doble_pasada(
                df_horarios_escuela, df_biometricos, fecha
            )
            
            mensaje_exito = f"Procesamiento completado: {len(df_procesado)} sesiones procesadas"
            self.logger.info(mensaje_exito)
            
            return True, df_procesado, estadisticas, mensaje_exito, df_biometricos
            
        except Exception as e:
            error_msg = f"Error procesando asistencia para {codigo_escuela}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, pd.DataFrame(), {}, error_msg, pd.DataFrame()
    
    def _procesar_asistencia_doble_pasada(
        self,
        df_horarios: pd.DataFrame,
        df_biometricos: pd.DataFrame,
        fecha: str
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Implementa el algoritmo de doble pasada migrado del sistema original.
        
        Pasos:
        1. Preprocesamiento y normalización de datos
        2. Expansión de horarios por fecha
        3. Marcado de bloques de sesiones continuas
        4. Pasada A: Asignación de entradas
        5. Pasada B: Asignación de salidas
        6. Cálculo de estados y estadísticas
        
        Args:
            df_horarios: DataFrame con horarios de la escuela
            df_biometricos: DataFrame con registros biométricos
            fecha: Fecha en formato YYYY-MM-DD
            
        Returns:
            Tupla (dataframe_procesado, estadisticas)
        """
        try:
            # 1. Preprocesamiento
            df_hor, df_log = self._preprocesar_datos(df_horarios, df_biometricos, fecha)
            
            if df_hor.empty:
                return pd.DataFrame(), self._estadisticas_vacias()
            
            # 2. Expandir horarios por fecha y marcar bloques
            df_ses = self._expandir_horarios_y_marcar_bloques(df_hor, fecha)
            
            if df_ses.empty:
                return pd.DataFrame(), self._estadisticas_vacias()
            
            # 3. Aplicar algoritmo de doble pasada
            evidencia_records = []
            df_detalle = self._aplicar_doble_pasada(df_ses, df_log, evidencia_records)
            
            # 4. Post-procesamiento y formateo
            df_procesado = self._postprocesar_resultados(df_detalle)
            
            # 5. Calcular estadísticas
            estadisticas = self._calcular_estadisticas(df_procesado)
            
            return df_procesado, estadisticas
            
        except Exception as e:
            self.logger.error(f"Error en procesamiento doble pasada: {e}", exc_info=True)
            return pd.DataFrame(), self._estadisticas_vacias()
    
    def _preprocesar_datos(
        self, 
        df_horarios: pd.DataFrame, 
        df_biometricos: pd.DataFrame,
        fecha: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Preprocesa y normaliza datos de horarios y biométricos.
        """
        # Procesar horarios
        df_hor = df_horarios.copy()
        
        # Validar columnas requeridas
        required_hor = ["docente", "dia_name", "h_inicio", "h_fin", "f__inicio", "f__fin"]
        missing = [c for c in required_hor if c not in df_hor.columns]
        if missing:
            raise ValueError(f"Horario no contiene columnas requeridas: {missing}")
        
        # Normalización de nombres/códigos para matching
        if "docente_codigo" in df_hor.columns and "docente_codigo" in df_biometricos.columns:
            self.logger.info("✅ Usando códigos de docente para matching preciso")
            df_hor["docente_norm"] = df_hor["docente_codigo"].astype(str).str.strip()
            df_biometricos["docente_norm"] = df_biometricos["docente_codigo"].astype(str).str.strip()
        else:
            self.logger.warning("⚠️ Campos 'docente_codigo' no encontrados. Usando nombres como fallback.")
            df_hor["docente_norm"] = df_hor["docente"].apply(self._norm_name)
            df_biometricos["docente_norm"] = df_biometricos["docente"].apply(self._norm_name)
        
        # Procesar fechas y horas en horarios
        df_hor["f__inicio"] = pd.to_datetime(df_hor["f__inicio"], errors="coerce")
        df_hor["f__fin"] = pd.to_datetime(df_hor["f__fin"], errors="coerce")
        df_hor["h_inicio"] = self._to_time_series(df_hor["h_inicio"])
        df_hor["h_fin"] = self._to_time_series(df_hor["h_fin"])
        
        # Normalizar días
        df_hor["dia_name_norm"] = df_hor["dia_name"].astype(str).str.upper().str.strip()
        df_hor["weekday"] = df_hor["dia_name_norm"].map(DIA2WK)
        
        # Procesar datos biométricos
        df_log = df_biometricos.copy()
        if not df_log.empty:
            # Asegurar columnas timestamp
            if "fecha_hora" in df_log.columns:
                df_log["ts"] = pd.to_datetime(df_log["fecha_hora"])
                df_log["fecha"] = df_log["ts"].dt.normalize()
                df_log["hora"] = df_log["ts"].dt.time
            else:
                df_log["fecha"] = pd.to_datetime(df_log.get("fecha", fecha), errors="coerce")
                df_log["hora"] = self._to_time_series(df_log.get("hora", "00:00"))
                df_log["ts"] = df_log["fecha"].dt.normalize() + pd.to_timedelta(
                    df_log["hora"].astype(str), errors="coerce"
                )
            
            # Ordenar por docente, fecha y timestamp
            df_log = df_log.sort_values(["docente_norm", "fecha", "ts"]).reset_index(drop=True)
        
        return df_hor, df_log
    
    def _norm_name(self, s: str) -> str:
        """Normaliza nombres para matching."""
        if pd.isna(s):
            return s
        s = unidecode(str(s)).upper().strip()
        s = " ".join(s.split())
        return s
    
    def _to_time_series(self, col: pd.Series) -> pd.Series:
        """Convierte serie a objetos time."""
        s = col.astype(str).str.strip()
        t = pd.to_datetime(s, format="%H:%M:%S", errors="coerce")
        m = t.isna()
        if m.any():
            t2 = pd.to_datetime(s[m], format="%H:%M", errors="coerce")
            t.loc[m] = t2
        return t.dt.time
    
    def _expandir_horarios_y_marcar_bloques(self, df_hor: pd.DataFrame, fecha: str) -> pd.DataFrame:
        """
        Expande horarios por fecha objetivo y marca bloques de sesiones continuas.
        """
        # Crear calendario con fecha objetivo
        fecha_obj = pd.to_datetime(fecha)
        cal = pd.DataFrame({"fecha": [fecha_obj]})
        cal["weekday"] = cal["fecha"].dt.dayofweek
        
        # Expandir horario por fecha
        df_ses = (
            df_hor.merge(cal, on="weekday", how="inner")
                  .query("fecha >= f__inicio and fecha <= f__fin")
                  .copy()
        )
        
        if df_ses.empty:
            return df_ses
        
        # Crear timestamps de inicio y fin
        df_ses["start_dt"] = df_ses["fecha"].dt.normalize() + pd.to_timedelta(
            df_ses["h_inicio"].astype(str), errors="coerce"
        )
        df_ses["end_dt"] = df_ses["fecha"].dt.normalize() + pd.to_timedelta(
            df_ses["h_fin"].astype(str), errors="coerce"
        )
        
        # Eliminar filas con timestamps inválidos
        df_ses = df_ses.dropna(subset=["start_dt", "end_dt"])
        df_ses = df_ses.sort_values(["docente_norm", "fecha", "start_dt", "end_dt"]).reset_index(drop=True)
        
        # Marcar bloques por docente/fecha
        df_ses = (
            df_ses.groupby(["docente_norm", "fecha"], group_keys=False)
                  .apply(self._marcar_bloques)
                  .reset_index(drop=True)
        )
        
        return df_ses
    
    def _marcar_bloques(self, g: pd.DataFrame) -> pd.DataFrame:
        """
        Marca bloques de sesiones continuas (migrado del sistema original).
        """
        g = g.sort_values(["start_dt", "end_dt"]).copy()
        
        # Calcular gap en minutos entre sesiones
        gap_min = (g["start_dt"] - g["end_dt"].shift(1)).dt.total_seconds().div(60)
        
        # Nueva sesión si no hay anterior o gap > adyacencia configurada
        nueva = (gap_min.isna()) | (gap_min > self.adyacencia_bloques)
        g["bloque_id"] = nueva.cumsum()
        
        # Calcular límites de cada bloque
        g["start_bloque_min"] = g.groupby("bloque_id")["start_dt"].transform("min")
        g["end_bloque_max"] = g.groupby("bloque_id")["end_dt"].transform("max")
        
        # Marcar posiciones en bloque
        g["es_tramo_inicial_de_bloque"] = g["start_dt"] == g["start_bloque_min"]
        g["es_tramo_final_de_bloque"] = g["end_dt"] == g["end_bloque_max"]
        
        return g
    
    def _aplicar_doble_pasada(
        self, 
        df_ses: pd.DataFrame, 
        df_log: pd.DataFrame, 
        evidencia_records: List[Dict]
    ) -> pd.DataFrame:
        """
        Aplica el algoritmo de doble pasada para matching de entradas y salidas.
        """
        def procesar_dia(grupo):
            doc, fecha = grupo.name
            g_log = df_log[(df_log["docente_norm"] == doc) & (df_log["fecha"] == fecha)][["ts"]].copy()
            g_proc, evid_no_usadas = self._asignar_marcas_por_dia(grupo, g_log)
            
            # Agregar evidencias no usadas
            for ev in evid_no_usadas:
                evidencia_records.append({
                    "FECHA": pd.to_datetime(fecha).normalize(),
                    "DOCENTE": grupo["docente"].iloc[0] if "docente" in grupo.columns else "",
                    "AULA": "",
                    **ev
                })
            
            return g_proc
        
        # Aplicar procesamiento por docente/fecha
        try:
            df_detalle = (
                df_ses.groupby(["docente_norm", "fecha"], group_keys=True)
                      .apply(procesar_dia, include_groups=False)
                      .reset_index()
            )
        except TypeError:
            # Fallback para versiones más antiguas de pandas
            df_detalle = (
                df_ses.groupby(["docente_norm", "fecha"], group_keys=True)
                      .apply(procesar_dia)
                      .reset_index()
            )
        
        return df_detalle
    
    def _asignar_marcas_por_dia(
        self, 
        g_ses: pd.DataFrame, 
        g_log: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Asigna marcas de entrada y salida para un docente en un día específico.
        
        Implementa el algoritmo de doble pasada:
        - Pasada A: asigna entradas a bloques
        - Pasada B: asigna salidas con registros restantes
        """
        g_ses = g_ses.copy()
        
        # Inicializar columnas de resultado
        g_ses[["entrada_marcada", "salida_marcada", "tardanza_min", "estado_entrada"]] = None
        g_ses["evid_salida_fuera"] = ""
        g_ses["evid_ref"] = ""
        g_ses["delta_salida_vs_fin"] = np.nan
        g_ses["motivo_evidencia"] = ""

        all_punches = sorted(g_log["ts"].tolist())
        available_punches = list(all_punches)

        if not available_punches:
            g_ses["estado_entrada"] = "SIN MARCAS EN EL DIA"
            g_ses["estado_bloque"] = "SIN_MARCA"
            return g_ses, []

        evidencias_no_usadas = []

        # Obtener bloques ordenados
        bloques = (
            g_ses.groupby("bloque_id", as_index=False)
                 .agg(start_b=("start_bloque_min", "min"),
                      end_b=("end_bloque_max", "max"))
                 .sort_values(["start_b", "end_b"], kind="stable")
                 .reset_index(drop=True)
        )

        # PASADA A: ENTRADAS
        for _, row in bloques.iterrows():
            start_b = row["start_b"]
            win_ent_ini = start_b - timedelta(minutes=self.ventana_entrada_antes)
            win_ent_fin = start_b + timedelta(minutes=self.ventana_entrada_despues)

            entrada = pd.NaT
            for p in list(available_punches):
                if win_ent_ini <= p <= win_ent_fin:
                    entrada = p
                    available_punches.remove(p)
                    break

            # Aplicar entrada al bloque
            bidx = g_ses.index[g_ses["start_bloque_min"] == row["start_b"]]
            b = g_ses.loc[bidx]
            
            if pd.notna(entrada):
                delta_min = (entrada - row["start_b"]).total_seconds() / 60.0
                tardanza_exacta = max(0, delta_min)
                tardanza_penalizable = max(0, delta_min - self.tolerancia_minutos)
                estado_ent = "A TIEMPO" if tardanza_penalizable <= 0 else "TARDANZA"

                # Asignar entrada al tramo inicial
                idx_ini = b.index[b["es_tramo_inicial_de_bloque"]]
                g_ses.loc[idx_ini, "entrada_marcada"] = entrada
                g_ses.loc[idx_ini, "tardanza_min"] = tardanza_exacta
                g_ses.loc[idx_ini, "estado_entrada"] = estado_ent

                # Asumir entrada para otros tramos del bloque
                idx_otros = b.index[~b["es_tramo_inicial_de_bloque"]]
                g_ses.loc[idx_otros, "entrada_marcada"] = g_ses.loc[idx_otros, "start_dt"]
                g_ses.loc[idx_otros, "tardanza_min"] = 0
                g_ses.loc[idx_otros, "estado_entrada"] = "EN BLOQUE (ASUMIDA)"
            else:
                g_ses.loc[b.index, "tardanza_min"] = np.nan
                g_ses.loc[b.index, "estado_entrada"] = "SIN MARCA DE ENTRADA"

        # Rastrear bloques con entrada
        tiene_entrada_por_bloque = (
            g_ses[g_ses["es_tramo_inicial_de_bloque"]]
            .assign(tiene=lambda d: d["entrada_marcada"].notna())
            .set_index("bloque_id")["tiene"]
            .to_dict()
        )

        # PASADA B: SALIDAS
        for _, row in bloques.iterrows():
            end_b = row["end_b"]
            win_sal_ini = end_b - timedelta(minutes=self.ventana_salida_antes)
            win_sal_fin = end_b + timedelta(minutes=self.ventana_salida_despues)

            candidatas = [p for p in available_punches if win_sal_ini <= p <= win_sal_fin]
            salida = pd.NaT
            if candidatas:
                salida = min(candidatas, key=lambda p: abs((p - end_b).total_seconds()))

            bidx = g_ses.index[g_ses["end_bloque_max"] == row["end_b"]]
            b = g_ses.loc[bidx]
            blk_id = int(b["bloque_id"].iloc[0]) if len(b) > 0 else None

            if pd.notna(salida):
                try:
                    available_punches.remove(salida)
                except ValueError:
                    pass
                
                # Asignar salida al tramo final
                idx_fin = b.index[b["es_tramo_final_de_bloque"]]
                g_ses.loc[idx_fin, "salida_marcada"] = salida
                
                # Solo asumir salidas para tramos intermedios si hay entrada en el bloque
                if blk_id is not None and tiene_entrada_por_bloque.get(blk_id, False):
                    idx_otros_salida = b.index[~b["es_tramo_final_de_bloque"]]
                    g_ses.loc[idx_otros_salida, "salida_marcada"] = g_ses.loc[idx_otros_salida, "end_dt"]

        # Determinar estados de bloque
        estado_bloque = {}
        for blk_id, gblk in g_ses.groupby("bloque_id"):
            tiene_entrada = gblk.loc[gblk["es_tramo_inicial_de_bloque"], "entrada_marcada"].notna().any()
            tiene_salida = gblk.loc[gblk["es_tramo_final_de_bloque"], "salida_marcada"].notna().any()
            
            if tiene_entrada and tiene_salida:
                estado = "OK"
            elif (not tiene_entrada) and tiene_salida:
                estado = "OBSERVADO"
            elif (not tiene_entrada) and (not tiene_salida):
                estado = "SIN_MARCA"
            else:
                estado = "ENTRADA_SIN_SALIDA"
            
            estado_bloque[int(blk_id)] = estado

        g_ses["estado_bloque"] = g_ses["bloque_id"].map(lambda x: estado_bloque.get(int(x), "SIN_MARCA"))

        # Procesar evidencias no usadas
        evidencias_no_usadas = self._procesar_evidencias_no_usadas(
            available_punches, g_ses, bloques, estado_bloque
        )

        return g_ses, evidencias_no_usadas
    
    def _procesar_evidencias_no_usadas(
        self,
        available_punches: List,
        g_ses: pd.DataFrame,
        bloques_det: pd.DataFrame,
        estado_bloque: Dict
    ) -> List[Dict]:
        """
        Procesa marcas biométricas no utilizadas como evidencia.
        """
        evidencias_no_usadas = []
        
        if not available_punches or g_ses.empty:
            return evidencias_no_usadas
        
        # Mapear índices de bloques
        idx_final_por_bloque = (
            g_ses[g_ses["es_tramo_final_de_bloque"]][["bloque_id"]]
            .assign(idx=lambda d: d.index)
            .set_index("bloque_id")["idx"]
            .to_dict()
        )
        idx_inicial_por_bloque = (
            g_ses[g_ses["es_tramo_inicial_de_bloque"]][["bloque_id"]]
            .assign(idx=lambda d: d.index)
            .set_index("bloque_id")["idx"]
            .to_dict()
        )

        def ref_para_bloque(blk_id, start_ts, end_ts):
            est = estado_bloque.get(int(blk_id), "SIN_MARCA")
            if est == "OBSERVADO":
                return "CLOSEST", None
            elif est == "ENTRADA_SIN_SALIDA":
                return "FIN", end_ts
            elif est == "SIN_MARCA":
                return "INICIO", start_ts
            else:
                return "FIN", end_ts

        for p in available_punches:
            deltas = []
            for i in range(len(bloques_det)):
                # bloques_det viene del groupby, tiene start_b y end_b, no las columnas originales
                if "bloque_id" in bloques_det.columns:
                    blk_id = int(bloques_det.loc[i, "bloque_id"])
                else:
                    blk_id = i  # Usar índice como fallback
                start_ts = bloques_det.loc[i, "start_b"]  # Usar start_b en lugar de start_bloque_min
                end_ts = bloques_det.loc[i, "end_b"]      # Usar end_b en lugar de end_bloque_max
                ref_name, ref_ts = ref_para_bloque(blk_id, start_ts, end_ts)
                
                if ref_name == "CLOSEST":
                    # Para bloques OBSERVADO, elegir referencia más cercana
                    dist_inicio = abs((start_ts - p).total_seconds())
                    dist_fin = abs((end_ts - p).total_seconds())
                    
                    if dist_inicio <= dist_fin:
                        ref_name, ref_ts = "INICIO", start_ts
                        d = dist_inicio
                    else:
                        ref_name, ref_ts = "FIN", end_ts
                        d = dist_fin
                else:
                    d = abs((ref_ts - p).total_seconds())
                
                deltas.append((d, blk_id, ref_name, ref_ts))
                    
            if not deltas:
                continue
                
            _, blk_id_near, ref_name_near, ref_ts_near = min(deltas, key=lambda x: x[0])
            delta_signed = int(round(((p - ref_ts_near).total_seconds()) / 60.0))

            motivo_auditoria = "IGNORADA: BLOQUE OK" if estado_bloque.get(blk_id_near) == "OK" else "FUERA DE VENTANA"
            evidencias_no_usadas.append({
                "TS_NO_USADA": p,
                "REFERENCIA": f"{ref_name_near}_BLOQUE",
                "DELTA_MIN": delta_signed,
                "TIPO": "SALIDA" if ref_name_near == "FIN" else "ENTRADA",
                "MOTIVO": motivo_auditoria,
                "OBSERVACIÓN": ""
            })

            # Actualizar evidencia en sesiones si no es bloque OK
            if SUPRIMIR_FLAG_DETALLE_SI_BLOQUE_OK and estado_bloque.get(blk_id_near) == "OK":
                continue

            if ref_name_near == "INICIO":
                idx_obj = idx_inicial_por_bloque.get(blk_id_near, None)
            else:
                idx_obj = idx_final_por_bloque.get(blk_id_near, None)

            if idx_obj is not None:
                curr = g_ses.loc[idx_obj, "delta_salida_vs_fin"]
                if pd.isna(curr) or abs(delta_signed) < abs(curr):
                    g_ses.loc[idx_obj, "evid_salida_fuera"] = pd.to_datetime(p).strftime("%H:%M")
                    g_ses.loc[idx_obj, "evid_ref"] = ref_name_near
                    g_ses.loc[idx_obj, "delta_salida_vs_fin"] = delta_signed
                    g_ses.loc[idx_obj, "motivo_evidencia"] = "FUERA DE VENTANA"

        return evidencias_no_usadas
    
    def _postprocesar_resultados(self, df_detalle: pd.DataFrame) -> pd.DataFrame:
        """
        Post-procesa resultados del algoritmo de doble pasada.
        """
        if df_detalle.empty:
            return df_detalle
        
        df_detalle = df_detalle.rename(columns={"es_tramo_final_de_bloque": "es_ultimo_del_bloque"})

        # Determinar estados de salida
        df_detalle["estado_salida"] = ""
        mask_con_salida = df_detalle["salida_marcada"].notna()
        df_detalle.loc[mask_con_salida & df_detalle["es_ultimo_del_bloque"], "estado_salida"] = "CON SALIDA"
        df_detalle.loc[mask_con_salida & ~df_detalle["es_ultimo_del_bloque"], "estado_salida"] = "EN BLOQUE (ASUMIDA)"
        mask_ultimo_sin_salida = df_detalle["salida_marcada"].isna() & df_detalle["es_ultimo_del_bloque"]
        df_detalle.loc[mask_ultimo_sin_salida, "estado_salida"] = "SIN MARCA DE SALIDA (ULTIMO BLOQUE)"

        # Formatear horarios
        def _fmt_hhmm(x):
            if pd.isna(x):
                return ""
            try:
                return pd.to_datetime(x).strftime("%H:%M")
            except Exception:
                return ""

        df_detalle["hora_entrada"] = df_detalle["start_dt"].apply(_fmt_hhmm)
        df_detalle["hora_salida"] = df_detalle["end_dt"].apply(_fmt_hhmm)
        df_detalle["entrada_marcada_str"] = df_detalle["entrada_marcada"].apply(_fmt_hhmm)
        df_detalle["salida_marcada_str"] = df_detalle["salida_marcada"].apply(_fmt_hhmm)

        # Manejar "NO MARCÓ" vs "POR DESIGNAR PROFESOR"
        if "docente" in df_detalle.columns:
            is_pordesignar = df_detalle["docente"].astype(str).str.upper().str.strip().eq("POR DESIGNAR PROFESOR")
            for col in ["entrada_marcada_str", "salida_marcada_str"]:
                vacio = df_detalle[col].astype(str).str.strip().eq("")
                df_detalle.loc[vacio & ~is_pordesignar, col] = "NO MARCÓ"

        # Manejar SALIDA "OBSERVADO"
        evid_nonempty = df_detalle.get("evid_salida_fuera", "").astype(str).str.strip().ne("")
        est_observado = df_detalle.get("estado_bloque", "").astype(str).str.upper().eq("OBSERVADO")
        cond_obs_salida = df_detalle["salida_marcada_str"].eq("NO MARCÓ") & (evid_nonempty | est_observado)
        
        if "docente" in df_detalle.columns:
            is_pordesignar = df_detalle["docente"].astype(str).str.upper().str.strip().eq("POR DESIGNAR PROFESOR")
            cond_obs_salida = cond_obs_salida & (~is_pordesignar)
        
        df_detalle.loc[cond_obs_salida, "salida_marcada_str"] = "OBSERVADO"

        # Generar texto de tardanza
        df_detalle["tardanza_txt"] = df_detalle.apply(self._tardanza_txt_row, axis=1)

        return df_detalle
    
    def _tardanza_txt_row(self, row) -> str:
        """
        Genera texto de tardanza por fila (migrado del sistema original).
        """
        est_blk = (row.get("estado_bloque") or "").upper()
        if est_blk == "OBSERVADO":
            return "OBSERVADO"
        if est_blk == "SIN_MARCA":
            return "SIN MARCA"
        
        # Para tardanza, calcular los minutos y segundos exactos después de tolerancia
        if isinstance(row.get("tardanza_min"), (int, float)) and not pd.isna(row.get("tardanza_min")):
            # tardanza_min contiene los minutos totales de retraso
            delta_min_total = float(row["tardanza_min"])
            
            # Calcular tardanza después de tolerancia
            tardanza_despues_tolerancia = max(0, delta_min_total - self.tolerancia_minutos)
            
            if tardanza_despues_tolerancia <= 0:
                return "A TIEMPO"
            else:
                # Convertir a minutos:segundos
                minutos = int(tardanza_despues_tolerancia)
                segundos = int((tardanza_despues_tolerancia - minutos) * 60)
                return f"{minutos}:{segundos:02d} min"
                
        est_ent = (row.get("estado_entrada") or "")
        if isinstance(est_ent, str) and "SIN MARCA DE ENTRADA" in est_ent.upper():
            return "SIN MARCA"
        return ""
    
    def _calcular_estadisticas(self, df_procesado: pd.DataFrame) -> Dict:
        """
        Calcula estadísticas del procesamiento.
        """
        if df_procesado.empty:
            return self._estadisticas_vacias()
        
        # Contar por estado de tardanza
        total_horarios = len(df_procesado)
        presentes = len(df_procesado[df_procesado["tardanza_txt"] == "A TIEMPO"])
        tardanzas = len(df_procesado[df_procesado["tardanza_txt"].str.contains(r"\d+:\d+\s*min", regex=True, na=False)])
        ausentes = len(df_procesado[df_procesado["tardanza_txt"] == "SIN MARCA"])
        observados = len(df_procesado[df_procesado["tardanza_txt"] == "OBSERVADO"])

        return {
            "total_horarios": total_horarios,
            "presentes": presentes + tardanzas,  # Presente incluye tardanzas
            "ausentes": ausentes,
            "tardanzas": tardanzas,
            "observados": observados,
            "errores": 0,
            "porcentaje_asistencia": round(((presentes + tardanzas) / total_horarios * 100) if total_horarios > 0 else 0, 2),
            "porcentaje_ausencia": round((ausentes / total_horarios * 100) if total_horarios > 0 else 0, 2),
            "docentes_unicos": df_procesado["docente"].nunique() if "docente" in df_procesado.columns else 0,
            "cursos_unicos": df_procesado.get("cod_cur", pd.Series()).nunique()
        }
    
    def _estadisticas_vacias(self) -> Dict:
        """
        Retorna estadísticas vacías por defecto.
        """
        return {
            "total_horarios": 0,
            "presentes": 0,
            "ausentes": 0,
            "tardanzas": 0,
            "observados": 0,
            "errores": 0,
            "porcentaje_asistencia": 0,
            "porcentaje_ausencia": 0,
            "docentes_unicos": 0,
            "cursos_unicos": 0
        }
    
    def procesar_multiple_fechas(
        self,
        codigo_escuela: str,
        fechas: List[str],
        ruta_horarios: str,
        hoja_horarios: str = None
    ) -> Dict[str, Tuple[bool, pd.DataFrame, Dict, str]]:
        """
        Procesa asistencia para múltiples fechas.
        
        Args:
            codigo_escuela: Código de la escuela
            fechas: Lista de fechas en formato 'YYYY-MM-DD'
            ruta_horarios: Ruta al archivo Excel con horarios
            hoja_horarios: Nombre de la hoja Excel (opcional)
            
        Returns:
            Dict con resultados por fecha: {fecha: (exito, dataframe_procesado, estadisticas, mensaje)}
        """
        resultados = {}
        
        for fecha in fechas:
            self.logger.info(f"Procesando fecha {fecha}")
            resultado = self.procesar_asistencia_escuela(
                codigo_escuela, fecha, ruta_horarios, hoja_horarios
            )
            resultados[fecha] = resultado
        
        return resultados
