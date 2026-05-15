# legal_cache_service.py
# Smart Cache Semanal para el Corpus Legal (Pinecone → GCS → RAM)
import json
import os
import datetime
from typing import Optional

from google.cloud import storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from src.config import logger, firestore_db
from src.vector_service import retrieve_context

# --- Configuración ---
GCS_BUCKET_NAME = os.getenv("LEGAL_CACHE_BUCKET", "recava-buscador-legal-cache")
GCS_BLOB_NAME = "legal_cache/corpus_legal_v1.json"
CACHE_TTL_DAYS = 7
FIRESTORE_CACHE_DOC = "system/legal_cache"

# --- Caché en memoria del proceso ---
_in_memory_cache: Optional[dict] = None
_cache_loaded_at: Optional[datetime.datetime] = None


def _get_gcs_client():
    """Obtiene un cliente de GCS. Usa ADC en Cloud Run."""
    return storage.Client()


def _is_cache_expired() -> bool:
    """Consulta Firestore para verificar si la caché ha expirado (>7 días)."""
    try:
        doc = firestore_db.document(FIRESTORE_CACHE_DOC).get()
        if not doc.exists:
            logger.info("Legal cache: no existe registro en Firestore. Caché expirada.")
            return True

        data = doc.to_dict()
        last_sync = data.get("last_sync")
        if last_sync is None:
            return True

        # Firestore devuelve DatetimeWithNanoseconds (subclase de datetime)
        if hasattr(last_sync, 'timestamp'):
            last_sync_dt = last_sync
        else:
            last_sync_dt = datetime.datetime.fromisoformat(str(last_sync))

        age = datetime.datetime.now(datetime.timezone.utc) - last_sync_dt.replace(
            tzinfo=datetime.timezone.utc
        )
        expired = age.days >= CACHE_TTL_DAYS
        logger.info(
            f"Legal cache: última sincronización hace {age.days} días. "
            f"{'Expirada' if expired else 'Vigente'}."
        )
        return expired

    except Exception as e:
        logger.error(f"Error consultando estado de caché legal: {e}", exc_info=True)
        return True  # En caso de error, forzar reconstrucción


def _build_cache_from_pinecone(indicators: list[dict]) -> dict:
    """Ejecuta las 37 consultas a Pinecone y consolida el corpus legal."""
    logger.info(f"Construyendo caché legal desde Pinecone para {len(indicators)} indicadores...")
    cache_data = {
        "synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_indicators": len(indicators),
        "indicators": {}
    }

    for ind in indicators:
        query = f"{ind['ref']} {ind['question']}"
        try:
            legal_context = retrieve_context(query=query, top_k=5)
            cache_data["indicators"][ind["id"]] = {
                "ref": ind["ref"],
                "question": ind["question"],
                "legal_context": legal_context or ""
            }
            logger.info(f"  Indicador {ind['id']} cacheado ({len(legal_context)} chars)")
        except Exception as e:
            logger.error(f"  Error cacheando indicador {ind['id']}: {e}")
            cache_data["indicators"][ind["id"]] = {
                "ref": ind["ref"],
                "question": ind["question"],
                "legal_context": ""
            }

    return cache_data


def _upload_cache_to_gcs(cache_data: dict):
    """Sube el JSON consolidado a Google Cloud Storage."""
    try:
        client = _get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_BLOB_NAME)
        blob.upload_from_string(
            json.dumps(cache_data, ensure_ascii=False, indent=2),
            content_type="application/json"
        )
        logger.info(f"Legal cache subida a gs://{GCS_BUCKET_NAME}/{GCS_BLOB_NAME}")
    except Exception as e:
        logger.error(f"Error subiendo caché a GCS: {e}", exc_info=True)
        raise


def _update_firestore_timestamp():
    """Actualiza el timestamp de última sincronización en Firestore."""
    firestore_db.document(FIRESTORE_CACHE_DOC).set({
        "last_sync": SERVER_TIMESTAMP,
        "bucket": GCS_BUCKET_NAME,
        "blob": GCS_BLOB_NAME
    }, merge=True)
    logger.info("Timestamp de caché legal actualizado en Firestore.")


def _download_cache_from_gcs() -> Optional[dict]:
    """Descarga el JSON de la caché legal desde GCS."""
    try:
        client = _get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_BLOB_NAME)

        if not blob.exists():
            logger.warning("Blob de caché legal no existe en GCS.")
            return None

        content = blob.download_as_text()
        cache_data = json.loads(content)
        logger.info(
            f"Caché legal descargada desde GCS. "
            f"Fecha: {cache_data.get('synced_at')}. "
            f"Indicadores: {cache_data.get('total_indicators')}."
        )
        return cache_data

    except Exception as e:
        logger.error(f"Error descargando caché de GCS: {e}", exc_info=True)
        return None


def get_legal_cache(indicators: list[dict]) -> dict:
    """
    Punto de entrada principal.
    Devuelve el corpus legal consolidado, reconstruyéndolo si ha expirado.

    Returns:
        dict con estructura:
        {
            "synced_at": "ISO timestamp",
            "indicators": { "1": {"ref": ..., "legal_context": ...}, ... }
        }
    """
    global _in_memory_cache, _cache_loaded_at

    # 1. Si ya está en RAM y fue cargada hace menos de 1 hora, reutilizar
    if _in_memory_cache and _cache_loaded_at:
        age = datetime.datetime.now(datetime.timezone.utc) - _cache_loaded_at
        if age.total_seconds() < 3600:  # 1 hora de TTL en RAM
            logger.info("Legal cache: sirviendo desde memoria RAM.")
            return _in_memory_cache

    # 2. Verificar si la caché semanal ha expirado
    if _is_cache_expired():
        # Reconstruir desde Pinecone
        cache_data = _build_cache_from_pinecone(indicators)
        try:
            _upload_cache_to_gcs(cache_data)
            _update_firestore_timestamp()
        except Exception as e:
            logger.warning(f"No se pudo persistir caché en GCS: {e}. Usando datos en RAM.")
    else:
        # Descargar desde GCS
        cache_data = _download_cache_from_gcs()
        if cache_data is None:
            # Fallback: reconstruir si GCS falla
            logger.warning("Fallback: reconstruyendo caché desde Pinecone.")
            cache_data = _build_cache_from_pinecone(indicators)

    # 3. Almacenar en RAM
    _in_memory_cache = cache_data
    _cache_loaded_at = datetime.datetime.now(datetime.timezone.utc)

    return cache_data


def get_indicator_context(cache: dict, indicator_id: str) -> str:
    """Extrae el contexto legal de un indicador específico desde la caché."""
    indicator_data = cache.get("indicators", {}).get(indicator_id, {})
    return indicator_data.get("legal_context", "")
