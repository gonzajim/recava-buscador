# app.py - FORCE UPDATE 2026-05-15 19:30
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
# Orígenes permitidos
_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "https://recava-buscador.web.app,https://recava-buscador.firebaseapp.com,https://recava-buscador-panel.web.app,http://localhost:3000,http://localhost:8000")
_allowed_origins = [origin.strip() for origin in _allowed_origins_str.split(",") if origin.strip()]

if not _allowed_origins:
    _allowed_origins = ["*"]
    logger.warning("CORS_ORIGINS not defined, defaulting to '*'")
elif "*" in _allowed_origins:
    _allowed_origins = ["*"]

CORS(
    app,
    origins=_allowed_origins,
    supports_credentials=True,
    methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    expose_headers=["X-Request-Id"],
    max_age=86400
)

# Rate Limiting
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
    logger.info(json.dumps({"evt": "request_start", "id": request._id, "path": request.path, "method": request.method}))


@app.after_request
def _req_end(resp):
    dur_ms = int((time.time() - getattr(request, "_t0", time.time())) * 1000)
    resp.headers["X-Request-Id"] = getattr(request, "_id", "")
    return resp


# =============================================================================
# 3) Autenticación y helpers
# =============================================================================
def require_firebase_user_or_403():
    if os.getenv("DISABLE_AUTH_FOR_LOCAL", "false").lower() == "true":
        return {"uid": "local_dev_user", "email": "local@dev.com", "email_verified": True}

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, description="Falta Authorization Bearer token")
    id_token = auth_header.split(" ", 1)[1]
    try:
        decoded = fb_auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        logger.warning(f"Auth: token inválido: {e}")
        abort(401, description="Token inválido")


def _iso_utc(ts):
    if ts is None: return None
    if isinstance(ts, datetime.datetime):
        if ts.tzinfo is None: ts = ts.replace(tzinfo=datetime.timezone.utc)
        return ts.astimezone(datetime.timezone.utc).isoformat()
    try: return ts.isoformat()
    except: pass
    try: return datetime.datetime.fromisoformat(str(ts)).astimezone(datetime.timezone.utc).isoformat()
    except: return str(ts)


# =============================================================================
# 4) Endpoints del Módulo de Auditoría Empírica (NEIS S1)
# =============================================================================

@app.route("/api/audit/empirical", methods=["GET", "POST"])
def handle_empirical_audit_root():
    """Maneja el listado (GET) y la creación (POST) de auditorías."""
    decoded_user = require_firebase_user_or_403()
    uid = decoded_user.get("uid")

    if request.method == "GET":
        try:
            # Quitamos el order_by para evitar el error de índice
            docs = firestore_db.collection("empirical_audits") \
                .where("uid", "==", uid) \
                .limit(50) \
                .stream()
            
            audits = []
            for doc in docs:
                d = doc.to_dict()
                audits.append({
                    "thread_id": doc.id,
                    "filename": d.get("filename", "Sin nombre"),
                    "status": d.get("status", "unknown"),
                    "created_at": _iso_utc(d.get("created_at"))
                })
            
            # Ordenamos en memoria
            audits.sort(key=lambda x: x['created_at'] or '', reverse=True)
            return ok(audits[:10])
        except Exception as e:
            logger.error(f"Error listando auditorías: {e}", exc_info=True)
            return fail(f"Error al obtener historial: {str(e)}", status=500)

    elif request.method == "POST":
        if 'file' not in request.files:
            return fail("No se encontró ningún archivo", status=400)
        file = request.files['file']
        if file.filename == '':
            return fail("Archivo vacío", status=400)
            
        temp_dir = tempfile.mkdtemp()
        filename = werkzeug.utils.secure_filename(file.filename) or "document.pdf"
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path)

        thread_id = f"empirical_{uuid.uuid4().hex}"
        threading.Thread(target=run_empirical_audit_async, args=(thread_id, file_path, uid)).start()

        return jsonify({"ok": True, "thread_id": thread_id}), 202


@app.route("/api/audit/empirical/<thread_id>", methods=["GET"])
def get_empirical_audit(thread_id):
    try:
        doc_snap = firestore_db.collection("empirical_audits").document(thread_id).get()
        if not doc_snap.exists:
            return fail("Auditoría no encontrada", status=404)
        data = doc_snap.to_dict()
        for key in ("created_at", "updated_at", "completed_at"):
            if key in data and data[key] is not None:
                data[key] = _iso_utc(data[key])
        return ok(data)
    except Exception as e:
        logger.error(f"Error leyendo auditoría {thread_id}: {e}")
        return fail(f"Error interno", status=500)


@app.route("/api/audit/empirical/<thread_id>/feedback", methods=["PATCH"])
def patch_empirical_feedback(thread_id):
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
        return fail(f"Error interno", status=500)


@app.route("/health", methods=["GET"])
def health_check():
    return ok({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
