# Sistema Biométrico Modular UNAC v1.1 (README actualizado)

Sistema modular para obtención, procesamiento y reporte de asistencia docente a partir de registros biométricos (Control iD) y programación académica oficial de la Universidad Nacional del Callao.

---
## � Objetivos
1. Centralizar la captura de marcas biométricas por facultad.
2. Normalizar y cruzar registros con horarios académicos (Excel institucional).
3. Aplicar algoritmo de doble pasada para determinar asistencia, tardanza, ausencia y observados.
4. Generar reportes Excel profesionales por escuela y fecha (o procesamiento masivo ALL).
5. Facilitar auditoría mediante evidencia cruda y métricas claras.

---
## ✨ Principales Características
- Arquitectura modular (config / data / processing / interface).
- Algoritmo de bloque con ventanas ±50 min para entrada y salida.
- Detección de bloques contiguos y compresión visual de sesiones.
- Resúmenes especializados: Observados, Tardanzas, Faltas, Evidencia RAW.
- Columnas normalizadas para matching robusto por código de docente.
- Manejo de cursos compartidos entre escuelas (configurable).
- Logging a archivo (`biometrico_cli.log`) + consola.

---
## 🧩 Arquitectura de Carpetas (Resumen)
```
modular/
├── main.py                 # Punto de entrada (invoca CLI)
├── config/                 # Config centralizada
│   ├── __init__.py         # Ensamblado de constantes / validadores
│   ├── biometricos.py      # Dispositivos (IPs, puertos, credenciales)
│   └── escuelas.py         # Escuelas y mapeo a facultades
├── src/
│   ├── data/
│   │   ├── biometricos.py  # Captura y normalización de registros Control iD
│   │   └── horarios.py     # Lectura / cache / normalización de horarios Excel
│   ├── processing/
│   │   ├── asistencia.py   # Algoritmo doble pasada (matching y estadísticos)
│   │   └── reporte.py      # Generación de Excel formateado
│   └── interface/
│       └── cli.py          # Parser de argumentos y orquestación
└── reportes/               # Salida de archivos (subcarpetas por fecha)
```

---
## 📦 Dependencias Principales
| Paquete | Uso |
|---------|-----|
| `pandas` | Manipulación tabular y exportación Excel |
| `numpy` | Operaciones numéricas auxiliares |
| `requests` | Llamadas HTTP a dispositivos Control iD |
| `openpyxl` | Lectura de Excel de horarios |
| `XlsxWriter` | Formato avanzado de reportes |
| `unidecode` | Normalización de texto (acentos) |

Sugerencia de `requirements.txt`:
```
pandas
numpy
requests
openpyxl
XlsxWriter
unidecode
```

---
## 🚀 Uso (CLI Actual por Flags)
Mostrar ayuda general:
```
python modular/main.py --help
```

### Comandos / Flags Disponibles
| Flag | Descripción |
|------|-------------|
| `--esc` | Código de escuela (ej: `INGENIERIA_DE_SISTEMAS`) o `ALL` |
| `--date` | Fecha(s) `YYYY-MM-DD` separadas por comas |
| `--list-escuelas` | Lista todas las escuelas configuradas (activa/inactiva) |
| `--verificar-config` | Valida consistencia de configuración global |
| `--validar-conectividad` | Test de conexión/auth a dispositivos biométricos |
| `--archivo-horarios` | Ruta alternativa al Excel de programación |
| `--hoja` | Nombre de hoja específica del Excel |
| `--salida` | Directorio destino de reportes |
| `--nombre-archivo` | Nombre personalizado del archivo XLSX |
| `--debug` | Habilita flags internos (placeholder) |

### Ejemplos
Reporte simple (fecha actual si omites `--date`):
```
python modular/main.py --esc INGENIERIA_DE_SISTEMAS --date 2025-09-30
```

Procesar todas las escuelas activas:
```
python modular/main.py --esc ALL --date 2026-04-07
```

Múltiples fechas:
```
python modular/main.py --esc ENFERMERIA --date 2026-03-30,2026-03-31,2026-04-01,2026-04-04,2026-04-06,2026-04-07,2026-04-08
```

Usar otro archivo de horarios:
```
python modular/main.py --esc ADMINISTRACION --date 2025-09-30 --archivo-horarios "data/OTRO_ARCHIVO.xlsx"
```

Cambiar directorio de salida y nombre de archivo:
```
python modular/main.py --esc FISICA --date 2025-09-30 --salida reportes/custom --nombre-archivo reporte_fisica.xlsx
```

Listar escuelas:
```
python modular/main.py --list-escuelas
```

Verificar configuración:
```
python modular/main.py --verificar-config
```

Validar conectividad:
```
python modular/main.py --validar-conectividad
```

---
## 🧠 Algoritmo de Asistencia (Resumen)
1. Expansión de horarios del día objetivo y agrupación en bloques (gap ≤5 min).
2. Pasada A (entradas): busca primera marca en ventana `[inicio - 50m, inicio + 50m]`.
3. Pasada B (salidas): busca marca más cercana en `[fin - 50m, fin + 50m]`.
4. Estados de bloque: `OK`, `OBSERVADO`, `SIN_MARCA`, `ENTRADA_SIN_SALIDA`.
5. Tardanza = retraso real – tolerancia (tolerancia efectiva actual: 5 min en código; configuración dice 10 → pendiente unificación).
6. Evidencias de marcas no asignadas para auditoría contextual.

---
## 🗂️ Estructura del Reporte Excel
Se generan 5 hojas:
| Hoja | Contenido |
|------|-----------|
| `Detalle_sesiones` | Sesiones procesadas (formato final) |
| `Resumen_Observados` | Docentes con observaciones (sin entrada/salida) |
| `Resumen_Tardanzas` | Agrupación y minutos acumulados de tardanza |
| `Resumen_Faltas` | Bloques de ausencia continua y sesiones perdidas |
| `Evidencia_Biometricos_RAW` | Registros biométricos normalizados (si se pasó el DF) |

Colores: faltas (rojo), observados (amarillo), encabezados (azul suave).

---
## ⚙️ Configuración Relevante
Ubicada en `modular/config/__init__.py`:
| Clave | Propósito |
|-------|-----------|
| `HORARIO_EXCEL` | Ruta absoluta al Excel maestro (recomendado hacerla relativa o variable de entorno) |
| `PROCESAMIENTO_CONFIG` | Columnas mínimas, tolerancia declarada, cursos compartidos |
| `SISTEMA_CONFIG` | Timeouts, reintentos, prefijo de reportes |
| `REPORTE_CONFIG` | Estilos y nombres lógicos (parcialmente no usados todavía) |

Discrepancia conocida: `PROCESAMIENTO_CONFIG['tolerancia_minutos']=10` vs uso real `TOLERANCIA_MIN=5` en el algoritmo.

---
## 🔐 Seguridad (Consideraciones)
- Credenciales de dispositivos están en texto plano (`biometricos.py`).
- Recomendado mover a `.env` o variables de entorno y cargar con `os.getenv`.
- No hay cifrado en tránsito más allá de HTTP interno (sin TLS).

Ejemplo sugerido de variables de entorno:
```
CONTROLID_FIME_USER=admin
CONTROLID_FIME_PASS=admin
```
Luego mapear en tiempo de carga.

---
## 🧪 Pruebas
Actualmente no hay suite formal. Recomendaciones:
| Caso | Objetivo |
|------|----------|
| Bloque continuo | Verificar compresión y replicado de entrada/salida asumida |
| Tardanza límite | Validar frontera EXACTA de tolerancia |
| Sin marcas | Clasificación `SIN_MARCA` y conteo de ausentes |
| Observado | Salida sin entrada → estado `OBSERVADO` |
| Cursos compartidos | Inclusión en escuela solicitante |

Se puede integrar `pytest` + fixtures CSV simulando biométrico.

---
## 🛠️ Roadmap Sugerido
1. Unificar tolerancia (usar configuración y permitir flag `--tolerancia-min`).
2. Implementar cache persistente (Parquet) y añadir flag `--usar-cache`.
3. Externalizar credenciales.
4. Agregar comando de consolidación multi-fecha real (`--consolidar`).
5. Parametrizar nombres de hojas vía `REPORTE_CONFIG`.
6. Añadir metadatos (tolerancia usada, hash de horarios) dentro del Excel (hoja `Metadata`).
7. Incluir validación de la quinta hoja en `validar_reporte_existente`.
8. Generar documentación automática (p.e. `mkdocs`).

---
## ❗ Inconsistencias Actuales (Resumen Rápido)
- CLI documentada antes con subcomandos → ahora sólo flags.
- Tolerancia: config 10 vs implementación 5.
- Método `generar_cache_biometricos` referenciado pero no implementado.
- `REPORTE_CONFIG` parcialmente ignorado por `ReporteGenerator`.
- README anterior mencionaba hojas genéricas distintas.

---
## 🤝 Contribución
1. Crear rama feature: `git checkout -b feature/unificar-tolerancia`.
2. Implementar cambios y añadir pruebas.
3. Actualizar este README si se altera interfaz.
4. Enviar PR con descripción clara (cambios + impacto + pasos de prueba).

---
## 📄 Licencia / Uso Interno
Proyecto interno académico. Definir una licencia explícita (MIT / Internal Only) si se va a distribuir.

---
## 📬 Contacto / Mantenimiento
- Equipo de Analítica / Sistemas UNAC.
- Archivos de log: `biometrico_cli.log`.
- Reportes: carpeta `reportes/<YYYY-MM-DD>/`.

---
## 🧾 Changelog Resumido
| Versión | Cambio |
|---------|--------|
| 1.0.0 | Primera versión modular documentada |
| 1.1.0 | README unificado, descripción exacta de hojas, aclaración de tolerancia |

---
Fin del README actualizado.