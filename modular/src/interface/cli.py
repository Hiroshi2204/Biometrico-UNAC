"""
Interfaz de línea de comandos (CLI) para el sistema biométrico UNAC.

Reemplaza y mejora main_escuela.py proporcionando una interfaz más robusta
y funcional para el sistema modular.
"""

import argparse
import sys
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...config import (
    ESCUELAS_DISPONIBLES,
    ESCUELAS_ACTIVAS,
    CONFIG_VERSION,
    validate_escuela,
    listar_escuelas_activas,
    validar_configuracion_completa
)
from ..processing import AsistenciaProcessor, ReporteGenerator
from ..data import BiometricDataManager


class BiometricoCLI:
    """
    Interfaz de línea de comandos principal del sistema biométrico UNAC.
    
    Proporciona comandos para:
    - Generar reportes de asistencia
    - Validar conectividad con dispositivos
    - Listar escuelas disponibles
    - Verificar configuración del sistema
    """
    
    def __init__(self):
        """Inicializa la CLI y sus componentes."""
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Inicializar componentes del sistema
        self.asistencia_processor = AsistenciaProcessor()
        self.reporte_generator = ReporteGenerator()
        self.biometric_manager = BiometricDataManager()
        
        # Configurar parser de argumentos
        self.parser = self._create_argument_parser()
    
    def setup_logging(self):
        """Configura el sistema de logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('biometrico_cli.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _create_argument_parser(self) -> argparse.ArgumentParser:
        """Crea y configura el parser de argumentos (siguiendo el patrón del sistema original)."""
        parser = argparse.ArgumentParser(
            description="Sistema Biométrico Modular UNAC v1.0",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Ejemplos de uso:
  python main.py --esc INGENIERIA_DE_SISTEMAS --date 2025-09-22
  python main.py --esc ALL --date 2025-09-22  
  python main.py --list-escuelas
  
Para ver escuelas disponibles use: --list-escuelas
            """
        )
        
        # Argumentos principales (siguiendo el patrón del sistema original)
        parser.add_argument(
            "--esc", "--escuela", 
            dest="escuela",
            help="Código de escuela (ej: INGENIERIA_DE_SISTEMAS) o ALL para todas las escuelas"
        )
        parser.add_argument(
            "--date", "--fecha", 
            dest="fecha",
            help="Fecha en formato YYYY-MM-DD (separadas por comas para múltiples fechas)"
        )
        
        # Argumentos de información
        parser.add_argument(
            "--list-escuelas", 
            action="store_true",
            help="Muestra las escuelas disponibles"
        )
        parser.add_argument(
            "--verificar-config", 
            action="store_true",
            help="Verificar configuración del sistema"
        )
        parser.add_argument(
            "--validar-conectividad", 
            action="store_true",
            help="Validar conexión con dispositivos biométricos"
        )
        
        # Argumentos avanzados (opcionales)
        parser.add_argument(
            "--archivo-horarios", 
            help="Ruta personalizada del archivo de horarios"
        )
        parser.add_argument(
            "--hoja", 
            help="Nombre de la hoja Excel con horarios (opcional)"
        )
        parser.add_argument(
            "--salida", 
            help="Directorio de salida para reportes (opcional)"
        )
        parser.add_argument(
            "--nombre-archivo", 
            help="Nombre personalizado del archivo de salida (opcional)"
        )
        parser.add_argument(
            "--debug", 
            action="store_true",
            help="Genera archivos adicionales de debug"
        )



        
        return parser
    
    def run(self, args: Optional[List[str]] = None):
        """
        Ejecuta la CLI con los argumentos proporcionados (patrón del sistema original).
        
        Args:
            args: Lista de argumentos de línea de comandos (usar sys.argv si None)
        """
        try:
            parsed_args = self.parser.parse_args(args)
            
            # Mostrar información si se solicita
            if parsed_args.list_escuelas:
                self.cmd_listar_escuelas(parsed_args)
                return
            
            if parsed_args.verificar_config:
                self._print_header()
                self.cmd_verificar_config(parsed_args)
                return
            
            if parsed_args.validar_conectividad:
                self._print_header()
                self.cmd_validar_conectividad(parsed_args)
                return
            

            
            # Validar argumentos requeridos para reporte
            if not parsed_args.escuela:
                print("❌ Error: Debe especificar una escuela con --esc o ALL para todas")
                self.cmd_listar_escuelas(parsed_args)
                sys.exit(1)
            
            if not parsed_args.fecha:
                from datetime import datetime
                parsed_args.fecha = datetime.now().strftime("%Y-%m-%d")
                print(f"ℹ️  Usando fecha actual: {parsed_args.fecha}")
            
            # Mostrar cabecera
            self._print_header()
            
            # Ejecutar comando de reporte
            self.cmd_generar_reporte(parsed_args)
            
        except KeyboardInterrupt:
            print("\n🛑 Operación cancelada por el usuario.")
            sys.exit(130)
        except Exception as e:
            self.logger.error(f"Error ejecutando comando: {str(e)}")
            print(f"❌ Error: {str(e)}")
            sys.exit(1)
    
    def _print_header(self):
        """Imprime la cabecera del sistema."""
        print("=" * 60)
        print("🏛️  SISTEMA BIOMÉTRICO MODULAR UNAC v1.0")
        print("📋 Universidad Nacional del Callao")
        print("=" * 60)
        print()
    
    def cmd_generar_reporte(self, args):
        """Ejecuta el comando de generar reporte."""
        # Determinar archivo de horarios (igual que en el sistema original)
        from ...config import HORARIO_EXCEL
        from pathlib import Path
        
        archivo_horarios = Path(getattr(args, 'archivo_horarios', None)) if getattr(args, 'archivo_horarios', None) else HORARIO_EXCEL
        
        # Validar que el archivo existe
        if not archivo_horarios.exists():
            print(f"❌ Error: Archivo de horarios no encontrado: {archivo_horarios}")
            return
        
        # Procesar fechas
        fechas = [fecha.strip() for fecha in args.fecha.split(',')]
        
        # Validar formato de fechas
        fechas_validas = []
        for fecha in fechas:
            try:
                datetime.strptime(fecha, "%Y-%m-%d")
                fechas_validas.append(fecha)
            except ValueError:
                print(f"❌ Error: Formato de fecha inválido: {fecha}. Use YYYY-MM-DD")
                return
        
        # Verificar si es procesamiento masivo
        if args.escuela.upper() == "ALL":
            self._procesar_todas_las_escuelas(fechas_validas, archivo_horarios, args)
        else:
            # Procesamiento individual
            print(f"🏫 Generando reporte para escuela: {args.escuela}")
            print(f"📅 Fecha(s): {args.fecha}")
            print(f"📊 Archivo de horarios: {archivo_horarios}")
            print()
            
            # Validar escuela
            es_valida, msg_validacion = validate_escuela(args.escuela)
            if not es_valida:
                print(f"❌ Error: {msg_validacion}")
                return
            
            self._procesar_escuela_individual(args.escuela, fechas_validas, archivo_horarios, args)
        
    
    def _procesar_escuela_individual(self, codigo_escuela: str, fechas: List[str], archivo_horarios: Path, args):
        """Procesa una escuela individual."""
        # Configurar generador de reportes si se especifica directorio
        if args.salida:
            self.reporte_generator = ReporteGenerator(args.salida)
        
        # Procesar según número de fechas
        if len(fechas) == 1:
            self._procesar_fecha_unica(codigo_escuela, fechas[0], str(archivo_horarios), args.hoja, args.nombre_archivo)
        else:
            self._procesar_multiples_fechas(codigo_escuela, fechas, str(archivo_horarios), args.hoja, args.nombre_archivo)
    
    def _procesar_todas_las_escuelas(self, fechas: List[str], archivo_horarios: Path, args):
        """Procesa todas las escuelas disponibles (igual que en el sistema original)."""
        from ...config import ESCUELAS_ACTIVAS
        from datetime import datetime
        
        print("🚀 PROCESAMIENTO MASIVO DE TODAS LAS ESCUELAS")
        print(f"📅 Fecha(s): {', '.join(fechas)}")
        print(f"📊 Escuelas disponibles: {len(ESCUELAS_ACTIVAS)}")
        print(f"📁 Archivo horarios: {archivo_horarios}")
        print("=" * 60)
        print()
        
        # Configurar generador de reportes si se especifica directorio
        if args.salida:
            self.reporte_generator = ReporteGenerator(args.salida)
        
        resultados = {
            'exitosos': [],
            'fallidos': [],
            'warnings': [],
            'total_procesados': 0,
            'fechas': fechas,
            'inicio': datetime.now()
        }
        
        total_escuelas = len(ESCUELAS_ACTIVAS)
        
        for i, codigo_escuela in enumerate(ESCUELAS_ACTIVAS, 1):
            print(f"📋 ESCUELA {i}/{total_escuelas}: {codigo_escuela}")
            print("-" * 40)
            
            # Validar escuela antes de procesar
            es_valida, mensaje_validacion = validate_escuela(codigo_escuela)
            if not es_valida:
                print(f"⚠️  Saltando {codigo_escuela}: {mensaje_validacion}")
                resultados['warnings'].append({
                    'escuela': codigo_escuela,
                    'razon': mensaje_validacion
                })
                print()
                continue
            
            # Procesar todas las fechas para esta escuela
            escuela_exitosa = True
            escuela_reportes = []
            
            for fecha in fechas:
                print(f"🔄 Procesando {codigo_escuela} - {fecha}...")
                
                try:
                    exito, df_asistencia, estadisticas, mensaje, df_biometricos_raw = self.asistencia_processor.procesar_asistencia_escuela(
                        codigo_escuela, fecha, str(archivo_horarios), args.hoja
                    )
                    
                    if not exito:
                        print(f"❌ Error procesando asistencia: {mensaje}")
                        escuela_exitosa = False
                        break
                    
                    # Generar reporte (sin especificar nombre_archivo para usar el formato automático)
                    exito_reporte, ruta_reporte, msg_reporte = self.reporte_generator.generar_reporte_completo(
                        df_asistencia, estadisticas, codigo_escuela, fecha, df_biometricos_raw, None
                    )
                    
                    if exito_reporte:
                        escuela_reportes.append(ruta_reporte)
                        print(f"✅ Reporte generado: {ruta_reporte}")
                    else:
                        print(f"❌ Error generando reporte: {msg_reporte}")
                        escuela_exitosa = False
                        break
                        
                except Exception as e:
                    print(f"❌ Error procesando {codigo_escuela} - {fecha}: {str(e)}")
                    escuela_exitosa = False
                    break
            
            resultados['total_procesados'] += 1
            
            if escuela_exitosa:
                resultados['exitosos'].append({
                    'escuela': codigo_escuela,
                    'reportes': escuela_reportes
                })
                print(f"✅ {codigo_escuela} - COMPLETADO")
            else:
                resultados['fallidos'].append({
                    'escuela': codigo_escuela,
                    'error': 'Error en procesamiento'
                })
                print(f"❌ {codigo_escuela} - FALLIDO")
            
            print()
        
        # Resumen final
        resultados['fin'] = datetime.now()
        resultados['duracion'] = resultados['fin'] - resultados['inicio']
        
        print("=" * 60)
        print("📊 RESUMEN DEL PROCESAMIENTO MASIVO")
        print("=" * 60)
        print(f"📅 Fecha(s) procesadas: {', '.join(fechas)}")
        print(f"⏱️  Duración total: {resultados['duracion']}")
        print(f"✅ Exitosos: {len(resultados['exitosos'])}")
        print(f"❌ Fallidos: {len(resultados['fallidos'])}")
        print(f"⚠️  Advertencias: {len(resultados['warnings'])}")
        print(f"📊 Total procesados: {resultados['total_procesados']}")
        
        if resultados['exitosos']:
            print("\n✅ ESCUELAS PROCESADAS EXITOSAMENTE:")
            for resultado in resultados['exitosos']:
                print(f"   📂 {resultado['escuela']} - {len(resultado['reportes'])} reporte(s)")
        
        if resultados['fallidos']:
            print("\n❌ ESCUELAS CON ERRORES:")
            for resultado in resultados['fallidos']:
                print(f"   🚫 {resultado['escuela']} - {resultado['error']}")
        
        if resultados['warnings']:
            print("\n⚠️  ESCUELAS SALTADAS:")
            for resultado in resultados['warnings']:
                print(f"   ⚠️  {resultado['escuela']} - {resultado['razon']}")
        
        print("=" * 60)
    
    def _procesar_fecha_unica(self, codigo_escuela: str, fecha: str, archivo_horarios: str, hoja: Optional[str], nombre_archivo: Optional[str]):
        """Procesa reporte para una fecha única."""
        print(f"🔄 Procesando asistencia para {fecha}...")
        
        # Mostrar fuente de datos
        print(f"📊 Fuente de datos: Dispositivos biométricos en vivo")
        
        # Procesar asistencia
        exito, df_asistencia, estadisticas, mensaje, df_biometricos_raw = self.asistencia_processor.procesar_asistencia_escuela(
            codigo_escuela, fecha, archivo_horarios, hoja
        )
        
        if not exito:
            print(f"❌ Error procesando asistencia: {mensaje}")
            return
        
        print(f"✅ {mensaje}")
        
        # Mostrar estadísticas
        self._mostrar_estadisticas(estadisticas)
        
        # Generar reporte
        print("📝 Generando reporte Excel...")
        exito_reporte, ruta_reporte, msg_reporte = self.reporte_generator.generar_reporte_completo(
            df_asistencia, estadisticas, codigo_escuela, fecha, df_biometricos_raw, nombre_archivo
        )
        
        if exito_reporte:
            print(f"✅ {msg_reporte}")
            print(f"📄 Archivo: {ruta_reporte}")
        else:
            print(f"❌ Error generando reporte: {msg_reporte}")
    
    def _procesar_multiples_fechas(self, codigo_escuela: str, fechas: List[str], archivo_horarios: str, hoja: Optional[str], nombre_archivo: Optional[str]):
        """Procesa reporte para múltiples fechas."""
        print(f"🔄 Procesando asistencia para {len(fechas)} fechas...")
        
        resultados = []
        for fecha in fechas:
            print(f"\n📅 Procesando {fecha}...")
            exito, df_asistencia, estadisticas, mensaje, df_biometricos_raw = self.asistencia_processor.procesar_asistencia_escuela(
                codigo_escuela, fecha, archivo_horarios, hoja
            )
            
            if exito:
                print(f"✅ {mensaje}")
                # Generar reporte individual
                # Usar formato automático de nombre
                exito_reporte, ruta_reporte, msg_reporte = self.reporte_generator.generar_reporte_completo(
                    df_asistencia, estadisticas, codigo_escuela, fecha, df_biometricos_raw, None
                )
                if exito_reporte:
                    print(f"📄 Reporte: {ruta_reporte}")
                    resultados.append((fecha, True, ruta_reporte, estadisticas))
                else:
                    print(f"❌ Error en reporte: {msg_reporte}")
                    resultados.append((fecha, False, "", {}))
            else:
                print(f"❌ Error: {mensaje}")
                resultados.append((fecha, False, "", {}))
        
        # Mostrar resumen final
        print("\n📊 RESUMEN FINAL:")
        exitosos = sum(1 for _, exito, _, _ in resultados if exito)
        print(f"✅ Reportes exitosos: {exitosos}/{len(fechas)}")
        
        total_horarios = sum(stats.get('total_horarios', 0) for _, exito, _, stats in resultados if exito)
        total_presentes = sum(stats.get('presentes', 0) for _, exito, _, stats in resultados if exito)
        total_ausentes = sum(stats.get('ausentes', 0) for _, exito, _, stats in resultados if exito)
        
        print(f"📈 Total horarios procesados: {total_horarios}")
        print(f"✅ Total presentes: {total_presentes}")
        print(f"❌ Total ausentes: {total_ausentes}")
        
        if total_horarios > 0:
            porcentaje = round((total_presentes / total_horarios) * 100, 1)
            print(f"📊 Porcentaje asistencia global: {porcentaje}%")
    
    def _mostrar_estadisticas(self, estadisticas: dict):
        """Muestra estadísticas de asistencia en formato legible."""
        print("\n📊 Estadísticas de asistencia:")
        print(f"  📚 Total horarios programados: {estadisticas.get('total_horarios', 0)}")
        print(f"  ✅ Docentes presentes: {estadisticas.get('presentes', 0)}")
        print(f"  🚫 Docentes ausentes: {estadisticas.get('ausentes', 0)}")
        print(f"  ⏰ Tardanzas: {estadisticas.get('tardanzas', 0)}")
        print(f"  ❌ Errores: {estadisticas.get('errores', 0)}")
        print(f"  📈 Porcentaje asistencia: {estadisticas.get('porcentaje_asistencia', 0)}%")
        print(f"  📉 Porcentaje ausencia: {estadisticas.get('porcentaje_ausencia', 0)}%")
        print(f"  👨‍🏫 Docentes únicos: {estadisticas.get('docentes_unicos', 0)}")
        print(f"  📖 Cursos únicos: {estadisticas.get('cursos_unicos', 0)}")
    
    def cmd_listar_escuelas(self, args):
        """Ejecuta el comando de listar escuelas."""
        print("🏫 Escuelas disponibles:")
        print()
        
        from ...config import ESCUELAS_CONFIG
        escuelas = ESCUELAS_CONFIG
        print("📋 Mostrando todas las escuelas configuradas:")
        
        print()
        
        for codigo, config in escuelas.items():
            status = "🟢" if config.get("activa", False) else "🔴"
            print(f"  {status} {codigo}")
            print(f"     📝 Nombre: {config['nombre']}")
            print(f"     🏛️  Facultad: {config['facultad_codigo']}")
            print(f"     📍 Estado: {'Activa' if config.get('activa', False) else 'Inactiva'}")
            if config.get("observacion"):
                print(f"     💭 Observación: {config['observacion']}")
            print()
        
        print(f"📊 Total escuelas: {len(escuelas)}")
        activas = sum(1 for config in escuelas.values() if config.get("activa", False))
        print(f"✅ Escuelas activas: {activas}")
    
    def cmd_validar_conectividad(self, args):
        """Ejecuta el comando de validar conectividad."""
        print("🔌 Validando conectividad con dispositivos biométricos...")
        print()
        
        # Validar configuración primero
        es_valida, problemas = validar_configuracion_completa()
        
        if not es_valida:
            print("❌ Problemas de configuración encontrados:")
            for problema in problemas:
                print(f"  • {problema}")
            print()
        
        # Probar conectividad con cada facultad
        from ...config import FACULTADES_CONFIG
        
        total_dispositivos = len(FACULTADES_CONFIG)
        dispositivos_ok = 0
        
        for codigo, config in FACULTADES_CONFIG.items():
            print(f"🔍 Probando {codigo} ({config['ip']}:{config['puerto']})...")
            
            try:
                # Usar el BiometricDataManager para probar conectividad
                exito, msg = self.biometric_manager.validar_conectividad_facultad(codigo)
                
                if exito:
                    print(f"  ✅ {msg}")
                    dispositivos_ok += 1
                    
                    if args.detallado:
                        print(f"     📡 IP: {config['ip']}")
                        print(f"     🔌 Puerto: {config['puerto']}")
                        print(f"     🏛️  Nombre: {config['nombre']}")
                else:
                    print(f"  ❌ {msg}")
                    
            except Exception as e:
                print(f"  ❌ Error de conexión: {str(e)}")
            
            print()
        
        # Resumen final
        print("=" * 50)
        print(f"📊 Resumen de conectividad:")
        print(f"  🔌 Total dispositivos: {total_dispositivos}")
        print(f"  ✅ Dispositivos OK: {dispositivos_ok}")
        print(f"  ❌ Dispositivos con problemas: {total_dispositivos - dispositivos_ok}")
        print(f"  📈 Porcentaje funcional: {round((dispositivos_ok/total_dispositivos)*100, 1)}%")
    
    def cmd_verificar_config(self, args):
        """Ejecuta el comando de verificar configuración."""
        print("⚙️  Verificando configuración del sistema...")
        print()
        
        # Validar configuración completa
        es_valida, problemas = validar_configuracion_completa()
        
        if es_valida:
            print("✅ Configuración del sistema: VÁLIDA")
        else:
            print("❌ Configuración del sistema: PROBLEMAS ENCONTRADOS")
            print("\n🔍 Problemas detectados:")
            for problema in problemas:
                print(f"  • {problema}")
        
        print()
        
        # Mostrar resumen de configuración
        from ...config import get_resumen_configuracion, HORARIO_EXCEL
        resumen = get_resumen_configuracion()
        
        print("📋 Resumen de configuración:")
        print(f"  🔢 Versión: {resumen['version']}")
        print(f"  🏛️  Facultades totales: {resumen['facultades_totales']}")
        print(f"  ✅ Facultades funcionales: {resumen['facultades_funcionales']}")
        print(f"  🏫 Escuelas totales: {resumen['escuelas_totales']}")
        print(f"  🟢 Escuelas activas: {resumen['escuelas_activas']}")
        print(f"  ⏱️  Timeout conexión: {resumen['timeout_conexion']}s")
        print(f"  🕐 Tolerancia asistencia: {resumen['tolerancia_asistencia']} min")
        
        print("\n📁 Directorios del sistema:")
        print(f"  📊 Reportes: N/A")
        print(f"  📄 Logs: N/A")
        print(f"  💾 Datos: N/A")
        
        print("\n📄 Archivo de horarios:")
        if HORARIO_EXCEL.exists():
            print(f"  ✅ Encontrado: {HORARIO_EXCEL}")
        else:
            print(f"  ❌ No encontrado: {HORARIO_EXCEL}")




# Funciones auxiliares para compatibilidad
def main():
    """Función principal para ejecutar la CLI."""
    cli = BiometricoCLI()
    cli.run()


if __name__ == "__main__":
    main()