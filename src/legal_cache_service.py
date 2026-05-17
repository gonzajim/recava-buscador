"""
legal_cache_service.py
======================
Smart Cache semanal para el corpus normativo ESRS/CSRD.

Flujo:
  1. sync_legal_cache()  → consulta Pinecone (top_k=20 por indicador)
                           y sube normativa_cache.json a GCS.
  2. get_legal_cache()   → descarga el JSON desde GCS y lo devuelve
                           como dict (listo para inyectar en RAM).
  3. needs_sync()        → devuelve True si han pasado >7 días desde
                           el último sync (comprobado en Firestore).
"""

import json
import os
import datetime
from src.config import logger, firestore_db
from src.vector_service import hybrid_search_engine_cached

# ── Constantes ──────────────────────────────────────────────────────────────
CACHE_BUCKET  = os.getenv("LEGAL_CACHE_BUCKET", "recava-buscador-legal-cache")
CACHE_BLOB    = "normativa_cache.json"
USER_CACHE_BLOB_TEMPLATE = "normativa_cache_{uid}.json"  # Por-usuario
SYNC_CONFIG_DOC = ("system", "config")   # Firestore: collection / document
SYNC_INTERVAL_DAYS = 7
TOP_K_CHUNKS  = 20

# 37 indicadores (misma lista que empirical_audit_service.py)
INDICATORS = [
    {"id": "1",  "ref": "S1-9 66. a)",           "question": "¿Divulga la distribución por género (en número y porcentaje) en la alta dirección?"},
    {"id": "2",  "ref": "S1-9 66. b)",           "question": "¿Divulga la distribución de los asalariados por grupos de edad?"},
    {"id": "3",  "ref": "S1-10 69.",             "question": "¿Divulga si todos sus asalariados perciben un salario adecuado de conformidad con los índices de referencia aplicables?"},
    {"id": "4",  "ref": "S1-10 70.",             "question": "Si no todos lo perciben, ¿divulga los países en que los asalariados ganan menos del índice de referencia?"},
    {"id": "5",  "ref": "S1-10 70.",             "question": "Si no todos lo perciben, ¿divulga el porcentaje de asalariados en esa situación por países?"},
    {"id": "6",  "ref": "S1-10 71.",             "question": "¿Divulga la información del requisito con respecto a los trabajadores no asalariados?"},
    {"id": "7",  "ref": "S1-11 74. a)",          "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida de ingresos por enfermedad?"},
    {"id": "8",  "ref": "S1-11 74. b)",          "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida de ingresos por desempleo?"},
    {"id": "9",  "ref": "S1-11 74. c)",          "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida por accidentes y discapacidad?"},
    {"id": "10", "ref": "S1-11 74. d)",          "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida por permiso parental?"},
    {"id": "11", "ref": "S1-11 74. e)",          "question": "¿Divulga si todos los asalariados están cubiertos por protección social contra pérdida por jubilación?"},
    {"id": "12", "ref": "S1-11 75. [1]",         "question": "Si no todos están cubiertos, ¿divulga los países sin protección social?"},
    {"id": "13", "ref": "S1-11 75. [2]",         "question": "Si no todos están cubiertos, ¿divulga por países los tipos de asalariados sin protección por cada acontecimiento vital?"},
    {"id": "14", "ref": "S1-11 76.",             "question": "¿Divulga la información con respecto a los trabajadores no asalariados de su personal propio?"},
    {"id": "15", "ref": "S1-12 79.",             "question": "¿Divulga el porcentaje de personas con discapacidad entre sus asalariados?"},
    {"id": "16", "ref": "S1-12 80.",             "question": "¿Divulga el porcentaje de asalariados con discapacidad con desglose por género?"},
    {"id": "17", "ref": "S1-14 88. a) [1]",      "question": "Personal asalariado: ¿divulga el % cubierto por el sistema de gestión de salud y seguridad?"},
    {"id": "18", "ref": "S1-14 88. a) [2]",      "question": "Trabajadores no asalariados: ¿divulga el % cubierto por el sistema de gestión de salud y seguridad?"},
    {"id": "19", "ref": "S1-14 88. b) [1]",      "question": "Personal asalariado: ¿divulga el número de muertes por lesiones/enfermedades laborales?"},
    {"id": "20", "ref": "S1-14 88. b) [2]",      "question": "Trabajadores no asalariados: ¿divulga el número de muertes por lesiones/enfermedades laborales?"},
    {"id": "21", "ref": "S1-14 88. b) [3]",      "question": "Otros trabajadores de la cadena de valor: ¿divulga el número de muertes laborales?"},
    {"id": "22", "ref": "S1-14 88. b) [4]",      "question": "¿Divulga separadamente las muertes por lesiones y las causadas por problemas de salud?"},
    {"id": "23", "ref": "S1-14 88. c) [1]",      "question": "Personal asalariado: ¿divulga el número y tasa de accidentes de trabajo registrables?"},
    {"id": "24", "ref": "S1-14 88. c) [2]",      "question": "Trabajadores no asalariados: ¿divulga el número y tasa de accidentes registrables?"},
    {"id": "25", "ref": "S1-14 88. d)",          "question": "Personal asalariado: ¿divulga el número de casos de problemas de salud relacionados con el trabajo?"},
    {"id": "26", "ref": "S1-14 88. d) [2]",      "question": "Trabajadores no asalariados: ¿divulga el número de casos de problemas de salud laborales?"},
    {"id": "27", "ref": "S1-14 88.e)",           "question": "Personal asalariado: ¿divulga el número de días perdidos por lesiones/muertes laborales?"},
    {"id": "28", "ref": "S1-14 88. e) [2]",      "question": "Trabajadores no asalariados: ¿divulga el número de días perdidos por lesiones/muertes laborales?"},
    {"id": "29", "ref": "S1-14 90.",             "question": "¿Divulga el % de trabajadores propios cubiertos por un sistema de SST auditado o certificado?"},
    {"id": "30", "ref": "S1-14 90. {AR 81}",     "question": "¿Divulga la existencia/ausencia de auditoría SST y las normas subyacentes?"},
    {"id": "31", "ref": "S1-15 93. a)",          "question": "¿Divulga el % de asalariados con derecho a acogerse a permisos familiares?"},
    {"id": "32", "ref": "S1-15 93. b)",          "question": "¿Divulga el % de asalariados que se acogieron a permisos familiares, con desglose por género?"},
    {"id": "33", "ref": "S1-16 97. a) [1]",      "question": "¿Divulga la brecha salarial de género expresada como % del nivel retributivo medio masculino?"},
    {"id": "34", "ref": "S1-16 97. a) [2]",      "question": "¿Divulga la brecha salarial de género por categoría de asalariado?"},
    {"id": "35", "ref": "S1-16 97. a) [3]",      "question": "¿Divulga la brecha salarial de género por país o segmento?"},
    {"id": "36", "ref": "S1-16 97. b) [1]",      "question": "¿Divulga la relación entre la remuneración del mejor pagado y la media del resto?"},
    {"id": "37", "ref": "S1-16 97. b). [2]",     "question": "¿Divulga esa relación ajustada por poder adquisitivo entre países?"},
]


# ── Helpers GCS ─────────────────────────────────────────────────────────────

def _get_gcs_client():
    from google.cloud import storage
    return storage.Client()


def _upload_to_gcs(data: dict, blob_name: str = CACHE_BLOB) -> None:
    """Serializa el dict como JSON y lo sube al bucket."""
    client = _get_gcs_client()
    bucket = client.bucket(CACHE_BUCKET)
    blob   = bucket.blob(blob_name)
    blob.upload_from_string(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type="application/json"
    )
    logger.info(f"[legal_cache] {blob_name} subido a gs://{CACHE_BUCKET}/{blob_name}")


def _download_from_gcs(blob_name: str = CACHE_BLOB) -> dict:
    """Descarga y parsea el JSON de GCS."""
    client = _get_gcs_client()
    bucket = client.bucket(CACHE_BUCKET)
    blob   = bucket.blob(blob_name)
    content = blob.download_as_text(encoding="utf-8")
    return json.loads(content)


# ── API pública ──────────────────────────────────────────────────────────────

def needs_sync() -> bool:
    """
    Devuelve True si la caché no existe en Firestore o tiene más de 7 días.
    """
    try:
        col, doc = SYNC_CONFIG_DOC
        snap = firestore_db.collection(col).document(doc).get()
        if not snap.exists:
            return True
        last_sync = snap.to_dict().get("last_rag_sync")
        if last_sync is None:
            return True
        # Firestore devuelve datetime con timezone
        if last_sync.tzinfo is None:
            last_sync = last_sync.replace(tzinfo=datetime.timezone.utc)
        age = datetime.datetime.now(datetime.timezone.utc) - last_sync
        return age.days >= SYNC_INTERVAL_DAYS
    except Exception as e:
        logger.warning(f"[legal_cache] Error comprobando last_rag_sync: {e}. Se asume sync necesario.")
        return True


def sync_legal_cache() -> dict:
    """
    Rebuilds completo del corpus normativo:
    - Itera los 37 indicadores
    - Consulta Pinecone top_k=20 para cada uno
    - Consolida en normativa_cache.json y lo sube a GCS
    - Actualiza Firestore system/config.last_rag_sync
    Returns el dict del cache recién generado.
    """
    logger.info("[legal_cache] Iniciando sincronización del corpus normativo...")

    indicators_data = {}
    for ind in INDICATORS:
        question = ind['question']
        reglas  = ind.get('search_rules', '').strip()
        if reglas:
            query = (
                f"Indicador Objetivo: {question} | "
                f"CONTEXTO Y REGLAS CRÍTICAS DE BÚSOUEDA: {reglas}"
            )
        else:
            query = f"{ind['ref']} {question}"
        try:
            # Reutilizamos la función cacheada pero con top_k=20
            raw_context = hybrid_search_engine_cached(query, TOP_K_CHUNKS)
            # Dividimos el texto devuelto en chunks individuales
            chunks = [c.strip() for c in raw_context.split("\n\n") if c.strip()]
        except Exception as e:
            logger.warning(f"[legal_cache] Error recuperando chunks para ind {ind['id']}: {e}")
            chunks = []

        indicators_data[ind["id"]] = {
            "ref":      ind["ref"],
            "question": question,
            "chunks":   chunks
        }
        logger.info(f"[legal_cache] Indicador {ind['id']} → {len(chunks)} chunks recuperados.")

    cache = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "indicators":   indicators_data
    }

    # Subir a GCS
    _upload_to_gcs(cache)

    # Actualizar timestamp en Firestore
    try:
        col, doc = SYNC_CONFIG_DOC
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        firestore_db.collection(col).document(doc).set(
            {"last_rag_sync": SERVER_TIMESTAMP}, merge=True
        )
        logger.info("[legal_cache] Firestore system/config.last_rag_sync actualizado.")
    except Exception as e:
        logger.warning(f"[legal_cache] No se pudo actualizar Firestore: {e}")

    logger.info("[legal_cache] Sincronización completada.")
    return cache


def sync_legal_cache_for_user(uid: str, indicators: list) -> dict:
    """
    Rebuild de la caché normativa para un usuario específico con
    sus propios indicadores. Genera normativa_cache_[UID].json en GCS.
    """
    blob_name = USER_CACHE_BLOB_TEMPLATE.format(uid=uid)
    logger.info(f"[legal_cache] Iniciando sync caché para usuario {uid} ({len(indicators)} indicadores)...")

    indicators_data = {}
    for ind in indicators:
        question = ind.get('question', '')
        reglas   = ind.get('search_rules', '').strip()
        if reglas:
            query = (
                f"Indicador Objetivo: {question} | "
                f"CONTEXTO Y REGLAS CRÍTICAS DE BÚSOUEDA: {reglas}"
            )
        else:
            query = f"{ind.get('ref', '')} {question}"
        try:
            raw_context = hybrid_search_engine_cached(query, TOP_K_CHUNKS)
            chunks = [c.strip() for c in raw_context.split("\n\n") if c.strip()]
        except Exception as e:
            logger.warning(f"[legal_cache] Error chunks para ind {ind.get('id','?')} (user {uid}): {e}")
            chunks = []

        indicators_data[ind["id"]] = {
            "ref":      ind.get("ref", ""),
            "question": question,
            "chunks":   chunks
        }

    cache = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "uid":          uid,
        "indicators":   indicators_data
    }

    _upload_to_gcs(cache, blob_name=blob_name)

    # Marcar timestamp en Firestore del usuario
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        firestore_db.collection("usuarios_config").document(uid).set(
            {"last_rag_sync": SERVER_TIMESTAMP}, merge=True
        )
    except Exception as e:
        logger.warning(f"[legal_cache] No se pudo actualizar last_rag_sync de usuario {uid}: {e}")

    logger.info(f"[legal_cache] Caché de usuario {uid} generada en {blob_name}.")
    return cache


def check_and_warm_cache(uid: str) -> None:
    """
    Función de Background Warm-up ejecutada al login del usuario.
    Comprueba si la caché del usuario está vigente (<7 días) y,
    si no, la regenera en background sin bloquear la sesión del usuario.
    """
    try:
        # Determinar si el usuario tiene indicadores personalizados
        user_doc = firestore_db.collection("usuarios_config").document(uid).get()
        has_custom = False
        user_indicators = None

        if user_doc.exists:
            data = user_doc.to_dict()
            custom = data.get("indicadores_activos", [])
            if custom:
                has_custom = True
                user_indicators = custom

                # Comprobar si la caché personalizada está vigente
                last_sync = data.get("last_rag_sync")
                if last_sync:
                    if last_sync.tzinfo is None:
                        last_sync = last_sync.replace(tzinfo=datetime.timezone.utc)
                    age = datetime.datetime.now(datetime.timezone.utc) - last_sync
                    if age.days < SYNC_INTERVAL_DAYS:
                        logger.info(f"[warm_up] Caché de usuario {uid} vigente ({age.days}d). Sin acción.")
                        return

                logger.info(f"[warm_up] Regenerando caché personalizada para {uid}...")
                sync_legal_cache_for_user(uid=uid, indicators=user_indicators)
                return

        # Usuario sin indicadores personalizados → verificar caché global
        if needs_sync():
            logger.info(f"[warm_up] Caché global expirada. Regenerando para usuario {uid}...")
            sync_legal_cache()
        else:
            logger.info(f"[warm_up] Caché global vigente. Sin acción para {uid}.")

    except Exception as e:
        logger.error(f"[warm_up] Error en background warm-up para {uid}: {e}")


def get_legal_cache(uid: str = None) -> dict:
    """
    Descarga normativa_cache.json (global o por usuario) desde GCS.
    Si no existe o falla, retorna un dict vacío.
    """
    # Si el usuario tiene caché personalizada, intentarla primero
    if uid:
        blob_name = USER_CACHE_BLOB_TEMPLATE.format(uid=uid)
        try:
            cache = _download_from_gcs(blob_name=blob_name)
            logger.info(f"[legal_cache] Caché de usuario {uid} cargada (generada: {cache.get('generated_at', '?')})")
            return cache
        except Exception:
            logger.info(f"[legal_cache] Sin caché personalizada para {uid}. Usando global.")

    # Caché global por defecto
    try:
        cache = _download_from_gcs()
        logger.info(f"[legal_cache] Caché global cargada (generada: {cache.get('generated_at', '?')})")
        return cache
    except Exception as e:
        logger.warning(f"[legal_cache] No se pudo cargar cache desde GCS: {e}. Sin caché.")
        return {}
