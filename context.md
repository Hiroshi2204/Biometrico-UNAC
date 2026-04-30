# Contexto del Sistema Biométrico Modular UNAC (context.md)

Fecha de generación: 2025-10-01
Versión de código: 1.0.x (según `__init__.py` y configuración)| Constante | Valor | Uso |
|-----------|-------|----||
| `tolerancia_minutos` | 5 | ✅ **UNIFICADO**: Algoritmo usa configuración central. |
| `ventana_entrada_antes/despues_min` | 50 | ✅ **CONFIGURADO**: Ventanas de matching parametrizadas. |
| `ventana_salida_antes/despues_min` | 50 | ✅ **CONFIGURADO**: Ventanas de matching parametrizadas. |
| `adyacencia_bloques_min` | 5 | ✅ **CONFIGURADO**: Agrupación de sesiones en bloques. |
| Filtro ventana biométricos | 45 min | Elimina marcas demasiado cercanas por usuario. |
| Cache horarios | Diccionario interno | Evita releer Excel. |
## 1. Propósito General del Sistema
El **Sistema Biométrico Modular UNAC** permite:
- Conectarse a dispositivos biométricos (Control iD) distribuidos por facultades.
- Obtener registros crudos de acceso de docentes.
- Cruzar esos registros con la programación académica (horarios oficiales en Excel).
- Determinar asistencia, tardanzas, ausencias, observados y evidencia.
- Generar reportes Excel profesionales por escuela y fecha, o de manera masiva.

El diseño es **modular**, separando claramente: configuración, captura de datos, normalización, procesamiento algorítmico (doble pasada), generación de reportes y CLI.

---
## 2. Arquitectura Alta (Capas)
| Capa | Directorio / Componente | Rol Principal |
|------|--------------------------|---------------|
| Configuración | `modular/config/` | Define escuelas, facultades, rutas y parámetros de procesamiento. |
| Datos (Input) | `modular/src/data/` | Gestión de biométricos y horarios (extracción + normalización). |
| Procesamiento | `modular/src/processing/` | Algoritmo de asistencia (doble pasada) y generación de reportes Excel. |
| Interfaz (CLI) | `modular/src/interface/cli.py` | Orquesta comandos, parsea parámetros y produce salida textual. |
| Entrada principal | `modular/main.py` | Punto de entrada estándar del sistema. |
| Reportes | `reportes/<fecha>/` | Artefactos Excel generados por escuela y fecha. |
| Datos fuente | `data/` | Archivo maestro de horarios (`PROGRAMACION 2025B - PREGRADO.xlsx`). |
| Tests / Utilitarios | `modular/test_cache.py` | Script provisional de prueba (incompleto). |

---
## 3. Flujo de Ejecución (Resumen End-to-End)
1. Usuario ejecuta: `python modular/main.py --esc INGENIERIA_DE_SISTEMAS --date 2025-09-30`
2. CLI valida parámetros y configura componentes (`BiometricDataManager`, `HorarioDataManager`, `AsistenciaProcessor`, `ReporteGenerator`).
3. Carga y normaliza horarios (Excel) → Filtra por escuela (y cursos compartidos si aplica).
4. Identifica la facultad asociada a la escuela → Conecta a su biométrico.
5. Solicita registros vía endpoint `report_generate.fcgi` (HTTP POST) y obtiene CSV.
6. Normaliza CSV (column mapping, limpieza, deduplicación, ventana temporal, códigos docentes).
7. Algoritmo de **doble pasada** sobre horarios del día:
   - Pasada A: asigna marcas de entrada dentro de ventanas flexibles por bloque.
   - Pasada B: asigna marcas de salida optimizando cercanía al final del bloque.
   - Clasifica estado de bloque (OK / OBSERVADO / SIN_MARCA / ENTRADA_SIN_SALIDA).
   - Deriva tardanza efectiva (considerando tolerancia), observaciones y evidencias no usadas.
8. Postprocesa resultados (formato de horas, estados, etiquetas, compresión de sesiones compartidas, blanqueo visual para bloques contiguos).
9. Calcula estadísticas globales (presentes, tardanzas, ausentes, observados, porcentajes).
10. Genera Excel con 5 hojas: `Detalle_sesiones`, `Resumen_Observados`, `Resumen_Tardanzas`, `Resumen_Faltas`, `Evidencia_Biometricos_RAW` (formato profesional con colores y bordes).
11. Imprime resumen final en consola.

---
## 4. Componentes Clave y Responsabilidades
### 4.1 Configuración (`modular/config/__init__.py`)
- `SISTEMA_CONFIG`: timeouts, reintentos, rutas, prefijos y formatos.
- `PROCESAMIENTO_CONFIG`: columnas requeridas, tolerancia, días válidos y cursos compartidos.
- `REPORTE_CONFIG`: estilos y nombres lógicos (en parte heredado, aunque la implementación de reporte usa su propio formato más detallado en `reporte.py`).
- Validadores: `validar_configuracion_completa()`, `get_resumen_configuracion()`.
- Ruta fija al Excel de horarios: `HORARIO_EXCEL` (hardcode Windows path).

### 4.2 Escuelas y Facultades
- `escuelas.py`: define `ESCUELAS_CONFIG` (estado, asociación a facultad, observaciones) y funciones de validación/mapeo.
- `biometricos.py`: define `FACULTADES_CONFIG` con credenciales de dispositivos y puertos; ofrece validación y extracción de puerto.

### 4.3 Capa Datos
#### BiometricDataManager (`src/data/biometricos.py`)
- Login (`/login.fcgi`) para obtener token de sesión.
- Solicitud de reporte (`/report_generate.fcgi`) con payload estructurado (columnas, filtros de tiempo, delimitadores) → CSV plano.
- Parsing & Normalización:
  - Mapeo dinámico de encabezados → `fecha_hora`, `id_usuario`, `nombre_usuario`, etc.
  - `fecha_hora` → separa `fecha` y `hora`, agrega `dia` en español.
  - Deduplicación exacta + filtro de ventana de 45 min entre marcas por usuario.
  - Normalización de códigos docentes (extrae/ajusta últimos 4 dígitos) → `docente_codigo`.
  - Enriquecimiento con facultad origen.
- Métodos para múltiples facultades y estadísticas de conectividad.
- NOTA: El script `test_cache.py` hace referencia a `generar_cache_biometricos`, pero no existe tal método actualmente (brecha funcional / deuda técnica).

#### HorarioDataManager (`src/data/horarios.py`)
- Lee Excel (engine `openpyxl`) con soporte de cache en memoria.
- Normaliza columnas y valores (copias exactas de rutinas del sistema original).
- Genera campo `ESCUELA_NORMALIZADA` y conserva códigos docentes normalizados.
- Filtrado por escuela + **detección automática de cursos compartidos** (mismo docente + horario + aula).
- Validación de estructura mínima y consistencia de horas.
- Utilidades: listar docentes, cursos, días, estadísticas, limpieza de cache.

### 4.4 Procesamiento de Asistencia (`src/processing/asistencia.py`)
- Implementa algoritmo de "doble pasada" replicando lógica original:
  - Expansión de horarios del día objetivo con marcas de bloque (sesiones adyacentes ≤ 5 min → mismo bloque).
  - Ventanas de matching (constantes):
    - Entrada: ±50 minutos (before/after) alrededor de inicio bloque.
    - Salida: ±50 minutos alrededor de fin bloque.
  - Tolerancia tardanza: ✅ **Configurada dinámicamente** desde `PROCESAMIENTO_CONFIG['tolerancia_minutos']`.
  - Estados derivados por bloque y por sesión.
  - Evidencias de marcas “no usadas” para auditoría (e.g. fuera de ventana, bloque OK suprime evidencia detallada si flag activo).
  - Construcción de métricas: presentes (incluye tardanzas), ausentes (SIN MARCA), observados, tardanzas, porcentajes.
- Postprocesamiento: formato de horas, etiquetas "NO MARCÓ", compresión de tardanza en formato `MM:SS min`.

### 4.5 Generación de Reportes (`src/processing/reporte.py`)
- Pipeline:
  1. Preparar DataFrame base asegurando columnas clave.
  2. Colapsar sesiones compartidas (mismo docente + aula + intervalo) consolidando escuelas/códigos.
  3. "Blanqueo" visual de cursos contiguos (limpia registros entrada/salida intermedios para legibilidad).
  4. Generar resúmenes:
     - Observados (SIN ENTRADA / SIN SALIDA diferenciados).
     - Tardanzas (acumuladas en minutos → revertidas a MM:SS).
     - Faltas (agrupación por bloques continuos de ausencia para sumar sesiones perdidas).
  5. Evidencia RAW de biométricos (si se provee DataFrame crudo).
  6. Excel final con formato (ancho dinámico, colores: azul encabezado, rojo faltas, amarillo observados, bordes globales, auto-ajuste de columna, estilo condicional fila completa para faltas).
- Métodos auxiliares para validación de reportes existentes y consolidación multi-fecha (estadísticas agregadas sin fusión de hojas detalladas).

### 4.6 CLI (`src/interface/cli.py`)
Comandos soportados (mediante flags — el README muestra otra sintaxis que aún no coincide totalmente):
- `--list-escuelas`
- `--verificar-config`
- `--validar-conectividad`
- Reportes: `--esc <CÓDIGO|ALL> --date YYYY-MM-DD(,YYYY-MM-DD,...)` con opciones:
  - `--archivo-horarios` (ruta alternativa)
  - `--hoja` (nombre de hoja Excel)
  - `--salida` (directorio de reportes)
  - `--nombre-archivo` (override del nombre Excel)
  - `--debug` (placeholder; no se observan rutas de debug adicionales escritas aún)

Flujos específicos:
- Reporte individual vs masivo (ALL recorre `ESCUELAS_ACTIVAS`).
- Manejo de resultados masivos con resumen (éxitos, fallos, warnings, duración total).
- Impresión de estadísticas de asistencia en consola.
- Validación de conectividad recorre `FACULTADES_CONFIG` reportando estado HTTP / autenticación.

---
## 5. Algoritmo de Doble Pasada (Detalle)
1. Agrupación de sesiones por docente y fecha; detección de bloques continuos usando diferencia entre fin de sesión anterior e inicio actual (`ADYACENCIA_MIN=5`).
2. Pasada A (Entradas):
   - Para cada bloque, escanea marcas disponibles en ventana `[start - 50, start + 50]` minutos.
   - Asigna primera marca válida como entrada del bloque (tramo inicial) y replica entrada asumida para tramos subsiguientes.
   - Calcula tardanza real vs inicio; aplica tolerancia (5 min) y clasifica `A TIEMPO` / `TARDANZA`.
3. Pasada B (Salidas):
   - Busca marca más cercana dentro de ventana `[end - 50, end + 50]`.
   - Asigna a tramo final; replica salida asumida para tramos previos dentro del mismo bloque si hubo entrada.
4. Estado de bloque:
   - `OK`: entrada y salida válidas.
   - `OBSERVADO`: solo salida válida.
   - `SIN_MARCA`: ninguna.
   - `ENTRADA_SIN_SALIDA`: solo entrada.
5. Marcas no usadas → evaluadas contra referencias (INICIO / FIN / CLOSEST) para evidencias adicionales.
6. Etiquetado final por sesión: convierte faltas a `SIN MARCA`, evidencia de observados ajusta SALIDA a `OBSERVADO` si corresponde.

---
## 6. Modelos de Datos (Principales Columnas)
### Horarios Normalizados:
- `docente`, `docente_codigo` (normalizado), `escuela`, `ESCUELA_NORMALIZADA`, `dia_name`, `f__inicio`, `f__fin`, `h_inicio`, `h_fin`, `cod_doc`, `cod_cur`, `curso`, `aula`, `facultad`.

### Registros Biométricos Normalizados:
- `fecha`, `hora`, `id_usuario`, `docente`, `docente_codigo`, `facultad_codigo` (+ nombre interno no persistido siempre), `dia`.

### Resultado Procesado (antes de reporte):
- Horarios +: `entrada_marcada`, `salida_marcada`, `tardanza_min`, `estado_entrada`, `estado_bloque`, `estado_salida`, `tardanza_txt`, evidencias (`evid_salida_fuera`, `evid_ref`, `delta_salida_vs_fin`, `motivo_evidencia`), `bloque_id`.

### Reporte (Detalle_sesiones):
- `ESC`, `ESCUELA`, `COD CUR`, `COD DOC`, `DOCENTE`, `AULA`, `HORA ENTRADA`, `HORA SALIDA`, `REGISTRO ENTRADA`, `REGISTRO SALIDA`, `TARDANZA`, `EVIDENCIA`, `REF EVIDENCIA`, `Δ VS REFERENCIA (MIN)`.

---
## 7. Parámetros y Constantes Importantes
| Constante | Valor | Uso |
|-----------|-------|-----|
| `TOLERANCIA_MIN` | 5 | Algoritmo de asistencia (asistencia.py). |
| `PROCESAMIENTO_CONFIG['tolerancia_minutos']` | 10 | Config declarada (no usada en algoritmo actual). |
| Ventanas Entrada / Salida | ±50 min | Matching de marcas. |
| `ADYACENCIA_MIN` | 5 | Agrupación de sesiones en bloques. |
| Filtro ventana biométricos | 45 min | Elimina marcas demasiado cercanas por usuario. |
| Cache horarios | Diccionario interno | Evita releer Excel. |

---
## 8. Manejo de Errores y Logs
- Logging configurado vía `logging.basicConfig` en la CLI (file: `biometrico_cli.log` + stdout).
- Capturas específicas:
  - Conectividad: Timeout, ConnectionError → mensajes explícitos.
  - Validaciones: Faltan columnas, archivo inexistente, escuela inválida.
  - Procesamiento: Cualquier excepción retorna estructuras vacías y mensajes de error.
- Código de salida CLI: `130` (KeyboardInterrupt), `1` (errores generales).

---
## 9. Seguridad y Credenciales
- Credenciales de dispositivos biométricos están en texto plano en `config/biometricos.py` (riesgo). Recomendable externalizar a variables de entorno o archivo `.env` + no versionar.
- No hay cifrado ni rotación gestionada.

---
## 10. Diferencias vs README / Inconsistencias Detectadas
| Elemento | Observado en Código | Declarado / Esperado | Nota |
|----------|---------------------|----------------------|------|
| CLI sintaxis | Flags estilo `--esc`, `--date` | README muestra subcomandos (`reporte`, `listar-escuelas`) | README desactualizado respecto a parser actual. |
| Tolerancia tardanza | 5 min (constante local) | Configuración centralizada | ✅ **CORREGIDO**: AsistenciaProcessor usa `PROCESAMIENTO_CONFIG["tolerancia_minutos"]`. |
| Ventanas de matching | Constantes hardcode (±50 min) | Configuración parametrizada | ✅ **CORREGIDO**: Ventanas configurables en `PROCESAMIENTO_CONFIG`. |
| Adyacencia de bloques | Constante `ADYACENCIA_MIN = 5` | Configuración parametrizada | ✅ **CORREGIDO**: `adyacencia_bloques_min` en configuración. |
| Nombres de hojas Excel | Hardcode en `reporte.py` | Uso de `REPORTE_CONFIG["hojas_excel"]` | ✅ **CORREGIDO**: ReporteGenerator usa nombres configurados. |
| Validación de reportes | Lista hardcode de hojas esperadas | Validación dinámica desde config | ✅ **CORREGIDO**: Usa `REPORTE_CONFIG["hojas_excel"].values()`. |
| Generación cache biométricos | Referenciada en `test_cache.py` (`generar_cache_biometricos`) | Método inexistente | ✅ **RESUELTO**: Archivo `test_cache.py` eliminado. |
| Multiples fechas consolidación | Genera múltiples archivos por fecha | README sugiere quizá consolidación | Consolidación parcial implementada (estadísticas) pero no merge de detalle. |
| REPORTE_CONFIG vs ReporteGenerator | `REPORTE_CONFIG` tenía nombres genéricos ("resumen", "detalle") | Código usa nombres concretos y estilos hardcode (`Detalle_sesiones`, `Resumen_Tardanzas`, etc.) | ✅ **CORREGIDO**: `REPORTE_CONFIG` actualizada con nombres reales. |
| Cursos compartidos hardcodeados | Diccionario fijo con cursos específicos en `PROCESAMIENTO_CONFIG` | Sistema flexible que detecte automáticamente por docente+horario+aula | ✅ **CORREGIDO**: Implementada detección automática basada en mismo docente, horario y aula. |

---
## 11. Extensibilidad y Puntos de Integración
- Añadir nuevos dispositivos: editar `FACULTADES_CONFIG`.
- Nuevas escuelas: agregar entrada en `ESCUELAS_CONFIG` y asegurar facultad funcional.
- Soporte de más formatos de horarios: extender `HorarioDataManager.cargar_horarios_desde_excel` (e.g. CSV, API) manteniendo normalización.
- Persistencia intermedia (cache Parquet) no implementada: se puede añadir gestor en `data/`.
- API REST futura: encapsular `AsistenciaProcessor` y `ReporteGenerator` detrás de endpoints.

---
## 12. Limitaciones Actuales
- Dependencia absoluta de disponibilidad en línea de cada biométrico (no hay reintentos escalonados ni cola offline).
- No existe cache local de registros (todo es en vivo cada ejecución).
- Tolerancia configurable ignorada en la lógica principal (discrepancia 5 vs 10 min).
- Sin pruebas unitarias formales en `tests/` (estructura menciona carpeta pero no se listaron tests reales). 
- Falta mecanismo de auditoría consolidada de evidencias no usadas (se genera estructura pero no se exporta explícitamente a hoja separada salvo crudo RAW).
- Rutas absolutas Windows hardcode (portabilidad limitada).
- Credenciales expuestas en repositorio.
- No hay control de versiones de esquema de Excel ni validación avanzada (ej. detectar cambios masivos de columnas).

---
## 13. Recomendaciones de Mejora (Roadmap Técnico)
1. Unificar tolerancia de tardanza → usar `PROCESAMIENTO_CONFIG['tolerancia_minutos']` y exponer flag CLI.
2. Implementar método faltante `generar_cache_biometricos` o eliminar `test_cache.py` si es legado.
3. Externalizar credenciales a `.env` / variables de entorno + carga segura.
4. Crear suite de tests:
   - Mock de biométricos → CSV sample.
   - Casos: bloque continuo, tardanza límite, marca fuera de ventana, cursos compartidos.
5. Añadir consolidación multi-fecha real (un Excel con partición por fecha o columna adicional).
6. Validar integridad del Excel de horarios (checksum + diff de columnas).
7. Añadir logging estructurado (JSON) y niveles configurables.
8. Separar formatos de reporte (plantillas) para permitir branding institucional.
9. Introducir capa de repositorio/cache (Parquet) para regenerar reportes sin reconectar a biométricos.
10. Crear documentación técnica de algoritmos (diagrama de secuencia y de bloques).

---
## 14. Secuencia Interna (Diagrama Textual)
```
Usuario -> CLI -> HorarioDataManager -> (Excel) -> DF Horarios
Usuario -> CLI -> BiometricDataManager -> (HTTP Control iD) -> CSV -> DF Registros
DF Horarios + DF Registros -> AsistenciaProcessor (doble pasada) -> DF Procesado + Stats
DF Procesado + DF Registros RAW -> ReporteGenerator -> Excel (5 hojas)
CLI -> Consola (resumen / rutas generadas)
```

---
## 15. Métricas Derivadas (Definiciones)
- `presentes`: sesiones con `tardanza_txt == 'A TIEMPO'` o tardanza numérica (cuenta también tardanzas).
- `tardanzas`: sesiones donde `tardanza_txt` coincide con regex `\d+:\d+ min`.
- `ausentes`: sesiones con `tardanza_txt == 'SIN MARCA'`.
- `observados`: sesiones con `tardanza_txt == 'OBSERVADO'`.
- `% asistencia`: (presentes + tardanzas) / total * 100.
- `% ausencia`: ausentes / total * 100.

---
## 16. Consideraciones de Calidad de Datos
- Horarios inválidos (>50% horas faltantes) → rechazo total.
- Deduplicación biométrica impide ruido de marcas múltiples muy cercanas (≤45 min). Revisión: podría ser agresivo para sesiones cortas.
- Normalización de códigos docentes (últimos 4 dígitos) implica riesgo de colisiones entre docentes con sufijos iguales.
- Cursos compartidos se agregan por coincidencia textual contiene (case-insensitive); potencial falsos positivos.

---
## 17. Estado del Código / Salud Técnica
| Aspecto | Estado | Comentario |
|---------|--------|------------|
| Modularidad | Buena | Separación clara de capas. |
| Tests | Débil | No hay cobertura real. |
| Documentación interna | Moderada | Docstrings detallados en procesadores; README parcialmente desactualizado. |
| Manejo errores | Aceptable | Mensajes claros, pero sin clasificación estándar. |
| Seguridad | Baja | Credenciales en repositorio. |
| Portabilidad | Limitada | Rutas absolutas Windows y asunción de entorno local. |
| Config vs Uso | Inconsistente | Tolerancia duplicada (5 vs 10). |

---
## 18. Glosario Rápido
| Término | Definición |
|---------|------------|
| Bloque | Conjunto de sesiones contiguas separadas por ≤5 minutos. |
| Observado | Bloque con salida sin entrada en ventana (o evidencia parcial). |
| SIN MARCA | Ninguna marca válida de entrada o salida. |
| Evidencia no usada | Marca biométrica fuera de ventana que se registra para auditoría. |
| Curso compartido | Curso ofrecido a múltiples escuelas y considerado en reportes de cada una. |

---
## 19. Próximos Pasos Sugeridos (Prioridad Alta)
1. Corregir documentación CLI para reflejar flags actuales.
2. Exponer flag `--tolerancia-min` y alinear configuración.
3. Implementar cache persistente (Parquet) para reusabilidad y rendimiento.
4. Añadir test unitario mínimo para el algoritmo de doble pasada (caso simple + tardanza + ausencia).
5. Externalizar credenciales (seguridad básica inmediata).

---
## 20. Resumen Ejecutivo
El sistema entrega funcionalidad completa para generar reportes de asistencia biométrica por escuela y fecha con un algoritmo robusto que considera bloques de sesiones, ventanas flexibles y evidencias. La arquitectura es limpia y extensible, pero requiere mejoras en documentación coherente, pruebas, seguridad de credenciales, portabilidad y unificación de parámetros críticos.

---
Fin del documento.
