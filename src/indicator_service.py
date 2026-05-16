"""
indicator_service.py — V3.1
============================
Gestión de la matriz de indicadores por usuario.

Responsabilidades:
  - get_indicators(uid)       → Devuelve la lista de indicadores activos del usuario.
                                Si no tiene personalizados, usa los 37 base.
  - save_indicators(uid, df)  → Persiste una nueva matriz en Firestore y dispara
                                la regeneración de caché en segundo plano.
  - parse_excel(file_stream)  → Parsea y valida un archivo Excel/CSV subido por el usuario.
"""

import pandas as pd
import threading
from src.config import logger, firestore_db
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# ── Indicadores base por defecto (37 indicadores NEIS S1) ────────────────────
DEFAULT_INDICATORS = [
    {"id": "1",  "ref": "S1-9 66. a)",       "question": "¿Divulga la distribución por género (en número y porcentaje) en la alta dirección?"},
    {"id": "2",  "ref": "S1-9 66. b)",       "question": "¿Divulga la distribución de los asalariados por grupos de edad?"},
    {"id": "3",  "ref": "S1-10 69.",         "question": "¿Divulga si todos sus asalariados perciben un salario adecuado de conformidad con los índices de referencia aplicables?"},
    {"id": "4",  "ref": "S1-10 70.",         "question": "Si no todos lo perciben, ¿divulga los países en que los asalariados ganan menos del índice de referencia?"},
    {"id": "5",  "ref": "S1-10 70.",         "question": "Si no todos lo perciben, ¿divulga el porcentaje de asalariados en esa situación por países?"},
    {"id": "6",  "ref": "S1-10 71.",         "question": "¿Divulga la información del requisito con respecto a los trabajadores no asalariados?"},
    {"id": "7",  "ref": "S1-11 74. a)",      "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida de ingresos por enfermedad?"},
    {"id": "8",  "ref": "S1-11 74. b)",      "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida de ingresos por desempleo?"},
    {"id": "9",  "ref": "S1-11 74. c)",      "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida por accidentes y discapacidad?"},
    {"id": "10", "ref": "S1-11 74. d)",      "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida por permiso parental?"},
    {"id": "11", "ref": "S1-11 74. e)",      "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida por jubilación?"},
    {"id": "12", "ref": "S1-11 75. [1]",     "question": "Si no todos están cubiertos, ¿divulga los países sin protección social?"},
    {"id": "13", "ref": "S1-11 75. [2]",     "question": "Si no todos están cubiertos, ¿divulga por países los tipos de asalariados sin protección por cada acontecimiento vital?"},
    {"id": "14", "ref": "S1-11 76.",         "question": "¿Divulga la información con respecto a los trabajadores no asalariados de su personal propio?"},
    {"id": "15", "ref": "S1-12 79.",         "question": "¿Divulga el porcentaje de personas con discapacidad entre sus asalariados?"},
    {"id": "16", "ref": "S1-12 80.",         "question": "¿Divulga el porcentaje de asalariados con discapacidad con desglose por género?"},
    {"id": "17", "ref": "S1-14 88. a) [1]",  "question": "Personal asalariado: ¿divulga el % cubierto por el sistema de gestión de salud y seguridad?"},
    {"id": "18", "ref": "S1-14 88. a) [2]",  "question": "Trabajadores no asalariados: ¿divulga el % cubierto por el sistema de gestión de salud y seguridad?"},
    {"id": "19", "ref": "S1-14 88. b) [1]",  "question": "Personal asalariado: ¿divulga el número de muertes por lesiones/enfermedades laborales?"},
    {"id": "20", "ref": "S1-14 88. b) [2]",  "question": "Trabajadores no asalariados: ¿divulga el número de muertes por lesiones/enfermedades laborales?"},
    {"id": "21", "ref": "S1-14 88. b) [3]",  "question": "Otros trabajadores de la cadena de valor: ¿divulga el número de muertes laborales?"},
    {"id": "22", "ref": "S1-14 88. b) [4]",  "question": "¿Divulga separadamente las muertes por lesiones y las causadas por problemas de salud?"},
    {"id": "23", "ref": "S1-14 88. c) [1]",  "question": "Personal asalariado: ¿divulga el número y tasa de accidentes de trabajo registrables?"},
    {"id": "24", "ref": "S1-14 88. c) [2]",  "question": "Trabajadores no asalariados: ¿divulga el número y tasa de accidentes registrables?"},
    {"id": "25", "ref": "S1-14 88. d)",      "question": "Personal asalariado: ¿divulga el número de casos de problemas de salud relacionados con el trabajo?"},
    {"id": "26", "ref": "S1-14 88. d) [2]",  "question": "Trabajadores no asalariados: ¿divulga el número de casos de problemas de salud laborales?"},
    {"id": "27", "ref": "S1-14 88.e)",       "question": "Personal asalariado: ¿divulga el número de días perdidos por lesiones/muertes laborales?"},
    {"id": "28", "ref": "S1-14 88. e) [2]",  "question": "Trabajadores no asalariados: ¿divulga el número de días perdidos por lesiones/muertes laborales?"},
    {"id": "29", "ref": "S1-14 90.",         "question": "¿Divulga el % de trabajadores propios cubiertos por un sistema de SST auditado o certificado?"},
    {"id": "30", "ref": "S1-14 90. {AR 81}", "question": "¿Divulga la existencia/ausencia de auditoría SST y las normas subyacentes?"},
    {"id": "31", "ref": "S1-15 93. a)",      "question": "¿Divulga el % de asalariados con derecho a acogerse a permisos familiares?"},
    {"id": "32", "ref": "S1-15 93. b)",      "question": "¿Divulga el % de asalariados que se acogieron a permisos familiares, con desglose por género?"},
    {"id": "33", "ref": "S1-16 97. a) [1]",  "question": "¿Divulga la brecha salarial de género expresada como % del nivel retributivo medio masculino?"},
    {"id": "34", "ref": "S1-16 97. a) [2]",  "question": "¿Divulga la brecha salarial de género por categoría de asalariado?"},
    {"id": "35", "ref": "S1-16 97. a) [3]",  "question": "¿Divulga la brecha salarial de género por país o segmento?"},
    {"id": "36", "ref": "S1-16 97. b) [1]",  "question": "¿Divulga la relación entre la remuneración del mejor pagado y la media del resto?"},
    {"id": "37", "ref": "S1-16 97. b). [2]", "question": "¿Divulga esa relación ajustada por poder adquisitivo entre países?"},
]

# Columnas obligatorias del Excel del usuario
REQUIRED_COLUMNS = {"NEIS", "Epígrafe", "Indicador"}


def parse_excel(file_stream, filename: str) -> list:
    """
    Parsea un archivo Excel (.xlsx) o CSV y devuelve una lista de indicadores.
    Lanza ValueError si el archivo no tiene la estructura requerida.
    """
    try:
        fname = filename.lower()
        if fname.endswith(".csv"):
            df = pd.read_csv(file_stream, dtype=str)
        else:
            df = pd.read_excel(file_stream, dtype=str)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo: {e}")

    # Normalizar nombres de columna (quitar espacios extra)
    df.columns = [c.strip() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"El archivo no contiene las columnas obligatorias: {', '.join(sorted(missing))}. "
            f"Se encontraron: {', '.join(df.columns.tolist())}"
        )

    # Eliminar filas vacías en la columna Indicador
    df = df.dropna(subset=["Indicador"])
    df = df[df["Indicador"].str.strip() != ""]

    if len(df) == 0:
        raise ValueError("El archivo no contiene indicadores válidos (columna 'Indicador' vacía).")

    indicators = []
    for idx, row in df.iterrows():
        indicators.append({
            "id":       str(idx + 1),
            "ref":      str(row.get("NEIS", "")).strip() + " " + str(row.get("Epígrafe", "")).strip(),
            "question": str(row["Indicador"]).strip()
        })

    logger.info(f"[indicators] Parseados {len(indicators)} indicadores desde '{filename}'.")
    return indicators


def get_indicators(uid: str) -> list:
    """
    Devuelve la lista de indicadores activos del usuario.
    Si no tiene personalizados, devuelve los 37 indicadores base.
    """
    try:
        doc = firestore_db.collection("usuarios_config").document(uid).get()
        if doc.exists:
            data = doc.to_dict()
            custom = data.get("indicadores_activos", [])
            if custom:
                logger.info(f"[indicators] Usuario {uid}: {len(custom)} indicadores personalizados cargados.")
                return custom
    except Exception as e:
        logger.warning(f"[indicators] Error cargando indicadores de usuario {uid}: {e}. Usando base por defecto.")

    logger.info(f"[indicators] Usuario {uid}: usando 37 indicadores base por defecto.")
    return DEFAULT_INDICATORS


def save_indicators(uid: str, indicators: list) -> None:
    """
    Sobrescribe los indicadores activos del usuario en Firestore y
    dispara en background la regeneración de la caché normativa.
    """
    firestore_db.collection("usuarios_config").document(uid).set({
        "indicadores_activos": indicators,
        "updated_at":          SERVER_TIMESTAMP,
        "total_indicadores":   len(indicators)
    }, merge=True)
    logger.info(f"[indicators] Usuario {uid}: {len(indicators)} indicadores guardados en Firestore.")

    # Disparar regeneración de caché en background sin bloquear la respuesta HTTP
    def _regen():
        try:
            from src.legal_cache_service import sync_legal_cache_for_user
            sync_legal_cache_for_user(uid=uid, indicators=indicators)
        except Exception as e:
            logger.error(f"[indicators] Error regenerando caché para usuario {uid}: {e}")

    threading.Thread(target=_regen, daemon=True).start()
    logger.info(f"[indicators] Regeneración de caché para {uid} iniciada en background.")
