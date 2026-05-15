# app.py
import os
import time
import json
import uuid
import datetime
from flask import request, jsonify, abort

# --- Configuración base y clientes externos ---
from src.config import app, logger, firestore_db

# --- Gemini y Módulo Empírico ---
from src.empirical_audit_service import run_empirical_audit_async
import threading
import tempfile
import werkzeug.utils

# --- Firebase Admin / Firestore ---
import firebase_admin
from firebase_admin import credentials, auth as fb_auth, firestore

# Firestore server timestamps y decoradores transaccionales
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# --- CORS (opcional) y Rate Limiting ---
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# =============================================================================
# 0) Inicialización de Firebase Admin
# =============================================================================

# =============================================================================
# 1) CORS y Rate Limiting
# =============================================================================
# Orígenes permitidos: Lee desde variable de entorno o usa defaults seguros
_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "https://recava-buscador.web.app,https://recava-buscador.firebaseapp.com,https://recava-buscador-panel.web.app,http://localhost:3000,http://localhost:8000")
_allowed_origins = [origin.strip() for origin in _allowed_origins_str.split(",") if origin.strip()]

# Si no se define nada específico, permitir solo los dominios de Firebase y localhost
if not _allowed_origins:
    _allowed_origins = ["*"]
    logger.warning("CORS_ORIGINS not defined, defaulting to '*'")
elif "*" in _allowed_origins:
    _allowed_origins = ["*"]
    logger.info("CORS configured to allow all origins via '*'")

CORS(
    app,
    # Permite solo los orígenes especificados
    origins=_allowed_origins,
    # Permite credenciales si las usaras (aunque ahora usas Authorization header)
    supports_credentials=True,
    # Métodos y Headers necesarios para tu app
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    # Headers que el frontend podrá leer
    expose_headers=["X-Request-Id"],
    # Tiempo que el navegador puede cachear la respuesta OPTIONS (preflight)
    max_age=86400 # 1 día
)
logger.info(f"CORS configured for origins: {_allowed_origins}")

# Rate Limiting (sin cambios)
limiter = Limiter(get_remote_address, app=app, default_limits=["120/minute"])


# =============================================================================
# 2) Utilidades de respuesta y logging
# =============================================================================
def ok(data, **meta):
    resp = {"ok": True, "data": data}
    if meta:
        resp["meta"] = meta
    return jsonify(resp), 200


def fail(message, status=400, **details):
    return jsonify({"ok": False, "error": {"message": message, **details}}), status


@app.before_request
def _req_start():
    request._id = uuid.uuid4().hex[:12]
    request._t0 = time.time()
    # No logueamos el cuerpo (datos sensibles); solo metadatos
    logger.info(
        json.dumps(
            {"evt": "request_start", "id": request._id, "path": request.path, "method": request.method}
        )
    )


@app.after_request
def _req_end(resp):
    dur_ms = int((time.time() - getattr(request, "_t0", time.time())) * 1000)
    resp.headers["X-Request-Id"] = getattr(request, "_id", "")
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    logger.info(json.dumps({"evt": "request_end", "id": request._id, "status": resp.status_code, "ms": dur_ms}))
    return resp


# =============================================================================
# 3) Autenticación y helpers
# =============================================================================
def require_firebase_user_or_403():
    """Verifica ID token Firebase; exige email verificado. 401 si falta/incorrecto, 403 si no verificado."""
    if os.getenv("DISABLE_AUTH_FOR_LOCAL", "false").lower() == "true":
        return {
            "uid": "local_dev_user",
            "email": "local@dev.com",
            "email_verified": True
        }

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, description="Falta Authorization Bearer token")
    id_token = auth_header.split(" ", 1)[1]
    try:
        decoded = fb_auth.verify_id_token(id_token)
    except Exception as e:
        logger.warning(f"Auth: token inválido: {e}")
        abort(401, description="Token inválido")
    # if not decoded.get("email_verified", False):
    #     abort(403, description="Email no verificado")
    logger.debug(
        f"Auth OK uid={decoded.get('uid')} email={decoded.get('email')} verified={decoded.get('email_verified')}"
    )
    return decoded


def _build_user_metadata(decoded_user: dict) -> dict:
    user_id = decoded_user.get("user_id") or decoded_user.get("uid")
    return {
        "user_id": user_id,
        "uid": decoded_user.get("uid"),
        "email": decoded_user.get("email"),
        "email_verified": decoded_user.get("email_verified"),
    }


def _iso_utc(ts):
    """Normaliza a ISO-8601 UTC (acepta datetime/FirestoreTimestamp/str/None)."""
    if ts is None:
        return None
    if isinstance(ts, datetime.datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        return ts.astimezone(datetime.timezone.utc).isoformat()
    # Firestore Timestamp tiene .isoformat() tras conversión a datetime por SDK en responses
    try:
        return ts.isoformat()  # si ya es datetime-like
    except Exception:
        pass
    try:
        return datetime.datetime.fromisoformat(str(ts)).astimezone(datetime.timezone.utc).isoformat()
    except Exception:
        return str(ts)


# =============================================================================
# 4) Endpoints del Módulo de Auditoría Empírica (NEIS S1)
# =============================================================================


@app.route("/api/audit/empirical", methods=["POST"])
def start_empirical_audit():
    """Inicia una auditoría empírica asíncrona sobre un documento (PDF adjunto)."""
    decoded_user = require_firebase_user_or_403()
    uid = decoded_user.get("uid")

    if 'file' not in request.files:
        return fail("No se encontró ningún archivo", status=400)
        
    file = request.files['file']
    if file.filename == '':
        return fail("Archivo vacío", status=400)
        
    # Guardar en temporal
    temp_dir = tempfile.mkdtemp()
    filename = werkzeug.utils.secure_filename(file.filename) or "document.pdf"
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)

    # Generar un thread_id único para esta auditoría
    thread_id = f"empirical_{uuid.uuid4().hex}"

    # Iniciar proceso en background
    threading.Thread(
        target=run_empirical_audit_async,
        args=(thread_id, file_path, uid)
    ).start()

    return jsonify({
        "ok": True, 
        "message": "Empirical audit started", 
        "thread_id": thread_id
    }), 202


@app.route("/api/audit/empirical/<thread_id>", methods=["GET"])
def get_empirical_audit(thread_id):
    """Lee el estado y resultados de una auditoría empírica por su thread_id."""
    # En local no requerimos auth para facilitar pruebas; en producción se puede reactivar
    # decoded_user = require_firebase_user_or_403()
    try:
        doc_snap = firestore_db.collection("empirical_audits").document(thread_id).get()
        if not doc_snap.exists:
            return fail("Auditoría no encontrada", status=404)
        data = doc_snap.to_dict()
        # Serializar timestamps a ISO string
        for key in ("created_at", "updated_at", "completed_at"):
            if key in data and data[key] is not None:
                data[key] = _iso_utc(data[key])
        return ok(data)
    except Exception as e:
        logger.error(f"Error leyendo auditoría {thread_id}: {e}", exc_info=True)
        return fail(f"Error interno: {str(e)}", status=500)


@app.route("/api/audit/empirical/<thread_id>/feedback", methods=["PATCH"])
def patch_empirical_feedback(thread_id):
    """Actualiza la validación humana de un indicador."""
    body = request.get_json(silent=True) or {}
    indicator_id = body.get("indicator_id")
    human_validation = body.get("human_validation")
    if indicator_id is None:
        return fail("indicator_id requerido", status=400)
    try:
        firestore_db.collection("empirical_audits").document(thread_id).update({
            f"results.{indicator_id}.human_validation": human_validation
        })
        return ok({"updated": True})
    except Exception as e:
        logger.error(f"Error actualizando feedback {thread_id}/{indicator_id}: {e}", exc_info=True)
        return fail(f"Error interno: {str(e)}", status=500)


@app.route("/health", methods=["GET"])
def health_check():
    """Comprobación básica de que el proceso está vivo."""
    return ok({"status": "healthy"})


@app.route("/readyz", methods=["GET"])
def readyz():
    """Comprobación de dependencias: Firestore (y opcional OpenAI si quieres añadir)."""
    try:
        # Ping liviano a Firestore
        firestore_db.collection("_ready").document("ping").get()
        # Podrías añadir una llamada barata a OpenAI si tu política lo permite:
        # _ = client.models.list()  # cuidado con costes/latencia
        return ok({"status": "ready"})
    except Exception as e:
        return fail("degraded", status=503, details=str(e))


# =============================================================================
# 7) Entry point
# =============================================================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
