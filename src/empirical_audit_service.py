"""
empirical_audit_service.py — V2.Final
======================================
Motor de auditoría NEIS S1 con Smart Cache y Prompt de Rigor Senior.

Flujo:
  1. Recibe file_path del PDF y uid del usuario.
  2. Verifica si el corpus normativo necesita sincronización (>7 días).
  3. Carga normativa_cache.json desde GCS en memoria RAM (una sola vez).
  4. Sube el PDF a Gemini File API (una sola vez → file_uri reutilizado en las 37 llamadas).
  5. Lanza evaluación concurrente de los 37 indicadores (max 5 workers).
  6. Cada evaluación inyecta los 20 chunks del indicador en el system_instruction.
  7. Persiste resultados en Firestore en tiempo real (streaming de resultados).
"""

import json
import time
import os
import shutil
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from src.config import logger, firestore_db
from src.legal_cache_service import get_legal_cache, sync_legal_cache, needs_sync
import google.generativeai as genai

# ── Lista de indicadores ─────────────────────────────────────────────────────
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


def _build_system_prompt(indicator: dict, chunks: list) -> str:
    """
    Construye el system_instruction de Auditor Senior con los 20 chunks de la caché.
    """
    chunks_text = "\n\n---\n\n".join(chunks) if chunks else "No hay contexto normativo disponible en caché."

    return f"""Eres un Auditor Senior de Sostenibilidad especializado en estándares CSRD/ESRS.
Tu misión es evaluar si el documento PDF cumple con el siguiente indicador con rigor técnico y legal absoluto.

══════════════════════════════════════════════════════════════
INDICADOR A EVALUAR:
  Referencia: {indicator['ref']}
  Pregunta:   {indicator['question']}
══════════════════════════════════════════════════════════════

BASE LEGAL — CORPUS NORMATIVO (top-20 fragmentos del estándar oficial):
{chunks_text}

══════════════════════════════════════════════════════════════
PROTOCOLO DE AUDITORÍA SENIOR — INSTRUCCIONES OBLIGATORIAS:
══════════════════════════════════════════════════════════════

1. CAMPO "cumple" — VALORES PERMITIDOS:
   • "SI"  → El informe contiene el dato con claridad y suficiencia técnica.
   • "NO"  → El informe trata el tema pero la información es incompleta o insuficiente.
   • "NA"  → El dato no aparece en ninguna parte del informe.
   • "FE"  → El informe remite EXPLÍCITAMENTE a un documento o sitio web externo
             (ej: "ver nuestra web", "disponible en el Informe Anual adjunto").

2. CAMPO "evidencia_literal" — OBLIGATORIO:
   • Cita textual exacta del PDF que justifica tu decisión.
   • Si la respuesta es numérica o muy extensa, realiza una síntesis FIEL a la literalidad.
   • Si es NA: dejar vacío "".

3. CAMPO "pagina_real" — OBLIGATORIO:
   • Número de página exacto donde se localiza la evidencia.
   • Si es NA: usar "N/A".

4. CAMPO "razonamiento" — OBLIGATORIO, debe incluir TRES partes:
   a) COMPARATIVA: Explica cómo la evidencia hallada cumple o no los requisitos
      de los fragmentos normativos de la BASE LEGAL.
   b) UBICACIÓN CONTEXTUAL: Clasifica si la información está en:
      - "autonoma": sección dedicada específicamente a NEIS S1 / ESRS S1.
      - "dispersa": información entremezclada en el EINF u otras secciones genéricas.
      - "ausente": no se localiza información.
   c) JUSTIFICACIÓN DE VACÍOS (solo si cumple es NA o NO):
      Indica qué requisito técnico específico del estándar falta o por qué
      la información hallada es insuficiente para cumplir con rigor.

5. CAMPO "ubicacion_contextual":
   • Valor independiente: "autonoma" | "dispersa" | "ausente".

══════════════════════════════════════════════════════════════
RESTRICCIONES DE RIGOR PROFESIONAL — CUMPLIMIENTO OBLIGATORIO:
══════════════════════════════════════════════════════════════
❌ PROHIBIDO extrapolar, inferir o suponer datos no presentes en el PDF → usar "NA".
❌ PROHIBIDO hacer interpretaciones subjetivas. Toda afirmación debe ser verificable
   mediante la evidencia_literal.
❌ PROHIBIDO marcar "SI" si el dato aparece únicamente en fuente externa sin ser
   reproducido en el informe → usar "FE".

FORMATO DE RESPUESTA: JSON puro y estricto. Sin texto adicional fuera del JSON."""


def _evaluate_indicator(indicator: dict, gemini_file, legal_cache: dict) -> dict:
    """
    Evalúa un indicador usando el PDF (vía Gemini File API) y
    los chunks del corpus normativo precargados en memoria.
    """
    try:
        # Obtener los 20 chunks de la caché en RAM
        ind_cache = legal_cache.get("indicators", {}).get(indicator["id"], {})
        chunks = ind_cache.get("chunks", [])

        system_prompt = _build_system_prompt(indicator, chunks)

        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            ),
            system_instruction=system_prompt
        )

        response = model.generate_content(
            [gemini_file, "Evalúa el indicador en base al documento proporcionado y sigue el protocolo de auditoría senior al pie de la letra."]
        )

        result_json = json.loads(response.text)
        result_json["indicator_id"] = indicator["id"]

        # Normalizar ubicacion_contextual si el modelo la incluyó en razonamiento pero no como campo
        if "ubicacion_contextual" not in result_json:
            result_json["ubicacion_contextual"] = "ausente"

        return result_json

    except Exception as e:
        logger.error(f"Error evaluando indicador {indicator['id']}: {e}", exc_info=True)
        return {
            "indicator_id": indicator["id"],
            "cumple": "ERROR",
            "evidencia_literal": "",
            "pagina_real": "N/A",
            "ubicacion_contextual": "ausente",
            "razonamiento": f"Error interno en la evaluación: {str(e)}"
        }


def _compute_file_hash(file_path: str) -> str:
    """Calcula el MD5 del archivo para detectar duplicados."""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_empirical_audit_async(thread_id: str, file_path: str, uid: str):
    """
    Punto de entrada principal. Se ejecuta en un hilo secundario.
    """
    doc_ref = firestore_db.collection("empirical_audits").document(thread_id)

    # Calcular hash del documento
    try:
        doc_hash = _compute_file_hash(file_path)
    except Exception:
        doc_hash = "unknown"

    doc_ref.set({
        "uid":             uid,
        "filename":        os.path.basename(file_path),
        "hash_documento":  doc_hash,
        "status":          "processing",
        "created_at":      SERVER_TIMESTAMP,
        "results":         {}
    }, merge=True)

    logger.info(f"[audit] Iniciando auditoría V2.Final — thread={thread_id}, hash={doc_hash}")

    gemini_file = None
    temp_dir = os.path.dirname(file_path)

    try:
        # ── 1. Verificar y sincronizar Smart Cache ───────────────────────────
        if needs_sync():
            logger.info("[audit] Corpus normativo desactualizado. Sincronizando con Pinecone...")
            doc_ref.update({"status_detail": "syncing_legal_cache"})
            legal_cache = sync_legal_cache()
        else:
            logger.info("[audit] Cargando corpus normativo desde GCS...")
            legal_cache = get_legal_cache()

        # ── 2. Subir PDF a Gemini File API (única vez) ───────────────────────
        max_upload_retries = 3
        for attempt in range(1, max_upload_retries + 1):
            try:
                logger.info(f"[audit] Uploading PDF a Gemini (intento {attempt}/{max_upload_retries})...")
                gemini_file = genai.upload_file(file_path)
                break
            except Exception as upload_exc:
                logger.warning(f"[audit] Upload intento {attempt} fallido: {upload_exc}")
                if attempt == max_upload_retries:
                    raise
                time.sleep(3 * attempt)

        # Esperar a que Gemini procese el archivo
        while gemini_file.state.name == "PROCESSING":
            logger.info("[audit] Esperando procesamiento del PDF en Gemini...")
            time.sleep(2)
            gemini_file = genai.get_file(gemini_file.name)

        if gemini_file.state.name == "FAILED":
            raise Exception("Gemini File API: procesamiento del PDF fallido.")

        logger.info(f"[audit] PDF subido. URI: {gemini_file.uri}")
        doc_ref.update({"status_detail": "evaluating_indicators"})

        # ── 3. Evaluación concurrente de los 37 indicadores ──────────────────
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_ind = {
                executor.submit(_evaluate_indicator, ind, gemini_file, legal_cache): ind
                for ind in INDICATORS
            }

            for future in as_completed(future_to_ind):
                ind = future_to_ind[future]
                try:
                    result = future.result()
                    doc_ref.update({
                        f"results.{result['indicator_id']}": result,
                        "updated_at": SERVER_TIMESTAMP
                    })
                    logger.info(f"[audit] Indicador {result['indicator_id']} completado — cumple={result.get('cumple','?')}")
                except Exception as e:
                    logger.error(f"[audit] Error procesando indicador {ind['id']}: {e}")

        # ── 4. Marcar como completado ─────────────────────────────────────────
        doc_ref.update({
            "status":       "completed",
            "status_detail": "done",
            "completed_at": SERVER_TIMESTAMP
        })
        logger.info(f"[audit] Auditoría finalizada — thread={thread_id}")

    except Exception as e:
        logger.error(f"[audit] Fallo en auditoría {thread_id}: {e}", exc_info=True)
        doc_ref.update({
            "status":       "error",
            "status_detail": str(e),
            "updated_at":   SERVER_TIMESTAMP
        })
    finally:
        # Limpiar directorio temporal
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"[audit] Directorio temporal eliminado: {temp_dir}")
        except Exception as e:
            logger.warning(f"[audit] No se pudo eliminar directorio temporal: {e}")

        # Eliminar archivo de Gemini para liberar cuota
        if gemini_file:
            try:
                genai.delete_file(gemini_file.name)
                logger.info(f"[audit] Archivo Gemini eliminado: {gemini_file.name}")
            except Exception as e:
                logger.warning(f"[audit] No se pudo eliminar archivo Gemini: {e}")
