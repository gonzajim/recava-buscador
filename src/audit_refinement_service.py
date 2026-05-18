"""
audit_refinement_service.py — V3.5
====================================
Motor de Auditoría en Cascada Crítica (Deep Audit).

Flujo:
  1. Recupera snapshot de primera fase desde Firestore.
  2. Descarga PDF original desde GCS → sube a Gemini File API.
  3. Lee Smart Cache normativo del usuario desde GCS.
  4. Construye prompt de supervisión con 4 pilares de contexto.
  5. Invoca Gemini 2.5 Pro con temperature=0.0 y response_schema estricto.
  6. Actualiza Firestore in-situ: backup primera fase → sobrescribe con refinados.
"""

import json
import time
import os
import shutil
import tempfile
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from src.config import logger, firestore_db
from src.legal_cache_service import get_legal_cache
import google.generativeai as genai

# ── GCS config ──────────────────────────────────────────────────────────────
PDF_BUCKET = os.getenv("LEGAL_CACHE_BUCKET", "recava-buscador-legal-cache")
PDF_PREFIX = "audit_pdfs"


def _get_gcs_client():
    from google.cloud import storage
    return storage.Client()


def save_pdf_to_gcs(file_path: str, thread_id: str) -> str:
    """Guarda el PDF de auditoría en GCS para uso posterior por Deep Audit."""
    blob_name = f"{PDF_PREFIX}/{thread_id}.pdf"
    client = _get_gcs_client()
    bucket = client.bucket(PDF_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    logger.info(f"[deep_audit] PDF guardado en GCS: gs://{PDF_BUCKET}/{blob_name}")
    return blob_name


def _download_pdf_from_gcs(blob_name: str) -> str:
    """Descarga PDF desde GCS a un archivo temporal."""
    client = _get_gcs_client()
    bucket = client.bucket(PDF_BUCKET)
    blob = bucket.blob(blob_name)
    temp_dir = tempfile.mkdtemp()
    local_path = os.path.join(temp_dir, "document.pdf")
    blob.download_to_filename(local_path)
    logger.info(f"[deep_audit] PDF descargado desde GCS a {local_path}")
    return local_path


def _build_cascade_prompt(first_phase_results: dict, legal_cache: dict,
                          indicators_snapshot: list) -> str:
    """Construye el system prompt enriquecido para la cascada crítica."""
    # Contexto normativo desde el Smart Cache
    normative_context = {}
    cache_indicators = legal_cache.get("indicators", {})
    for ind in indicators_snapshot:
        ind_id = ind.get("id", "")
        ind_cache = cache_indicators.get(ind_id, {})
        chunks = ind_cache.get("chunks", [])
        normative_context[ind_id] = {
            "ref": ind.get("ref", ""),
            "question": ind.get("question", ""),
            "search_rules": ind.get("search_rules", ""),
            "chunks_normativos": chunks[:10]
        }

    results_json = json.dumps(first_phase_results, ensure_ascii=False, indent=2)
    normative_json = json.dumps(normative_context, ensure_ascii=False, indent=2)

    return f"""[CONTEXTO ENRIQUECIDO DE SUPERVISIÓN DE AUDITORÍA - CASCADA CRÍTICA]

1. INFORME ORIGINAL A ANALIZAR:
Accedido directamente mediante la Gemini File API adjunta (file_uri estructurado).

2. BASE LEGAL COMPLETA + REGLAS DE BÚSQUEDA EXPERTAS (SMART CACHE):
{normative_json}

3. RESULTADOS OBTENIDOS EN LA PRIMERA ITERACIÓN:
{results_json}

[INSTRUCCIÓN OPERATIVA DE MÁXIMA POTENCIA]
Asumes el rol del Socio Director General de Auditoría de Sostenibilidad.
Tu tarea es evaluar críticamente la exactitud de los resultados de la primera
fase frente al documento PDF real, cruzándolos con los requisitos legales
(Chunks) y las sugerencias específicas de los expertos (Reglas de Búsqueda).

Para cada indicador debes:
1. Validar la veracidad estricta de 'evidencia_literal' y corroborar que
   'pagina_real' coincida con el contenido del PDF.
2. Si los hallazgos de la primera fase son incompletos o imprecisos, reevaluarlos.
3. Generar un bloque obligatorio de 'instrucciones_complementarias' bajo
   'razonamiento_avanzado' detallando las desviaciones técnicas o validaciones
   de calidad realizadas.
4. Reescribir por completo 'hallazgos_y_evidencias_completas', asegurando que
   la cita literal sea exacta y la página física esté verificada.

══════════════════════════════════════════════════════════════
RESTRICCIONES DE RIGOR PROFESIONAL — CUMPLIMIENTO OBLIGATORIO:
══════════════════════════════════════════════════════════════
❌ PROHIBIDO extrapolar, inferir o suponer datos no presentes en el PDF → usar "NA".
❌ PROHIBIDO hacer interpretaciones subjetivas.
❌ PROHIBIDO marcar "SI" si el dato aparece únicamente en fuente externa → usar "FE".
❌ PROHIBIDO mantener una valoración de la primera fase si detectas errores.

FORMATO DE RESPUESTA: JSON puro conforme al response_schema. Sin texto adicional."""


def _get_response_schema():
    """Devuelve el response_schema estricto para Deep Audit."""
    return {
        "type": "object",
        "properties": {
            "id_auditoria": {"type": "string"},
            "auditoria_refinada": {
                "type": "object",
                "properties": {
                    "indicadores_evaluados": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "neis": {"type": "string"},
                                "epigrafe": {"type": "string"},
                                "cumple_definitivo": {
                                    "type": "string",
                                    "enum": ["SI", "NO", "NA", "FE"]
                                },
                                "razonamiento_avanzado": {
                                    "type": "object",
                                    "properties": {
                                        "comparativa_normativa": {"type": "string"},
                                        "instrucciones_complementarias_expertas": {"type": "string"}
                                    },
                                    "required": ["comparativa_normativa",
                                                  "instrucciones_complementarias_expertas"]
                                },
                                "hallazgos_y_evidencias_completas": {
                                    "type": "object",
                                    "properties": {
                                        "evidencia_literal_refinada": {"type": "string"},
                                        "pagina_real_verificada": {"type": "string"},
                                        "justificacion_vacios_critica": {"type": "string"}
                                    },
                                    "required": ["evidencia_literal_refinada",
                                                  "pagina_real_verificada",
                                                  "justificacion_vacios_critica"]
                                }
                            },
                            "required": ["neis", "epigrafe", "cumple_definitivo",
                                         "razonamiento_avanzado",
                                         "hallazgos_y_evidencias_completas"]
                        }
                    }
                },
                "required": ["indicadores_evaluados"]
            }
        },
        "required": ["id_auditoria", "auditoria_refinada"]
    }


def _map_refined_to_results(refined_response: dict, indicators_snapshot: list) -> dict:
    """Mapea la respuesta refinada al formato original de results para compatibilidad."""
    ref_to_id = {}
    for ind in indicators_snapshot:
        ref_to_id[ind.get("ref", "").strip()] = ind["id"]

    refined_results = {}
    indicadores = refined_response.get("auditoria_refinada", {}).get("indicadores_evaluados", [])

    for idx, item in enumerate(indicadores):
        epigrafe = item.get("epigrafe", "").strip()
        neis = item.get("neis", "").strip()
        ind_id = ref_to_id.get(epigrafe) or ref_to_id.get(neis)
        if not ind_id and idx < len(indicators_snapshot):
            ind_id = indicators_snapshot[idx]["id"]
        if not ind_id:
            ind_id = str(idx + 1)

        raz = item.get("razonamiento_avanzado", {})
        hall = item.get("hallazgos_y_evidencias_completas", {})

        refined_results[ind_id] = {
            "indicator_id": ind_id,
            "cumple": item.get("cumple_definitivo", "NA"),
            "evidencia_literal": hall.get("evidencia_literal_refinada", ""),
            "pagina_real": hall.get("pagina_real_verificada", "N/A"),
            "razonamiento": {
                "comparativa_normativa": raz.get("comparativa_normativa", ""),
                "ubicacion_contextual": "Sección autónoma",
                "justificacion_vacios": hall.get("justificacion_vacios_critica", ""),
                "instrucciones_complementarias_expertas": raz.get(
                    "instrucciones_complementarias_expertas", "")
            },
            "is_refined": True
        }

    return refined_results


# ═══════════════════════════════════════════════════════════════════════════
# Punto de entrada principal — se ejecuta en hilo secundario
# ═══════════════════════════════════════════════════════════════════════════

def run_deep_audit_async(thread_id: str, uid: str):
    """Ejecuta la Auditoría Avanzada en Cascada en background."""
    doc_ref = firestore_db.collection("empirical_audits").document(thread_id)
    gemini_file = None
    temp_path = None

    try:
        doc_ref.update({
            "status": "refining",
            "status_detail": "preparing_deep_audit",
            "updated_at": SERVER_TIMESTAMP
        })

        # 1. Recuperar snapshot de primera fase
        doc_snap = doc_ref.get()
        if not doc_snap.exists:
            raise Exception(f"Auditoría {thread_id} no encontrada")

        audit_data = doc_snap.to_dict()
        first_phase_results = audit_data.get("results", {})
        indicators_snapshot = audit_data.get("indicadores_utilizados_snapshot", [])
        pdf_gcs_path = audit_data.get("pdf_gcs_path")

        if not first_phase_results:
            raise Exception("No hay resultados de primera fase para refinar")
        if not pdf_gcs_path:
            raise Exception("PDF no disponible en GCS. Solo auditorías V3.5+ soportan Deep Audit.")

        # 2. Descargar PDF desde GCS y subir a Gemini
        doc_ref.update({"status_detail": "uploading_pdf_to_gemini"})
        temp_path = _download_pdf_from_gcs(pdf_gcs_path)

        for attempt in range(1, 4):
            try:
                gemini_file = genai.upload_file(temp_path)
                break
            except Exception as e:
                logger.warning(f"[deep_audit] Upload intento {attempt} fallido: {e}")
                if attempt == 3:
                    raise
                time.sleep(3 * attempt)

        while gemini_file.state.name == "PROCESSING":
            time.sleep(2)
            gemini_file = genai.get_file(gemini_file.name)

        if gemini_file.state.name == "FAILED":
            raise Exception("Gemini File API: procesamiento del PDF fallido.")

        # 3. Cargar Smart Cache normativo
        doc_ref.update({"status_detail": "loading_legal_cache"})
        legal_cache = get_legal_cache(uid=uid) or get_legal_cache() or {"indicators": {}}

        # 4. Construir prompt enriquecido e invocar Gemini
        doc_ref.update({"status_detail": "executing_deep_audit"})
        system_prompt = _build_cascade_prompt(
            first_phase_results, legal_cache, indicators_snapshot)

        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=_get_response_schema()
            ),
            system_instruction=system_prompt
        )

        response = model.generate_content([
            gemini_file,
            f"Ejecuta la Auditoría Avanzada en Cascada Crítica para {thread_id}. "
            "Revisa críticamente cada indicador de la primera fase contra el PDF adjunto."
        ])

        refined_response = json.loads(response.text)
        logger.info(f"[deep_audit] Respuesta Gemini recibida para {thread_id}")

        # 5. Mapear al formato compatible
        refined_results = _map_refined_to_results(refined_response, indicators_snapshot)

        # 6. Actualizar Firestore in-situ (spec sección 6)
        doc_ref.update({
            "resultados_granulares_primera_fase": first_phase_results,
            "results": refined_results,
            "tiene_segunda_iteracion": True,
            "fecha_ejecucion_refinamiento": SERVER_TIMESTAMP,
            "status": "completed",
            "status_detail": "deep_audit_done",
            "updated_at": SERVER_TIMESTAMP
        })

        logger.info(f"[deep_audit] Deep Audit completado — thread={thread_id}")

    except Exception as e:
        logger.error(f"[deep_audit] Error en Deep Audit {thread_id}: {e}", exc_info=True)
        doc_ref.update({
            "status": "completed",
            "status_detail": f"deep_audit_error: {str(e)}",
            "updated_at": SERVER_TIMESTAMP
        })
    finally:
        if temp_path:
            try:
                shutil.rmtree(os.path.dirname(temp_path), ignore_errors=True)
            except Exception:
                pass
        if gemini_file:
            try:
                genai.delete_file(gemini_file.name)
            except Exception:
                pass
