"""Visualizador de pila LIFO con soporte para texto e imágenes desde cámara.

Diseño:
- La sesión (cookie firmada, ~4 KB) guarda SOLO referencias ligeras a los elementos.
- Las fotos se guardan como archivos JPEG en ``instance/uploads`` y se sirven
  mediante una ruta protegida que solo entrega imágenes presentes en la pila
  de la sesión actual.
"""

from __future__ import annotations

import base64
import binascii
import logging
import os
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

app = Flask(__name__, instance_relative_config=True)
app.config.update(
    # En producción defina FLASK_SECRET_KEY como variable de entorno.
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,  # Rechaza peticiones > 2 MB
)

logger = logging.getLogger(__name__)

# --- Constantes ---------------------------------------------------------------
MAX_STACK_SIZE = 20
MAX_TEXT_LENGTH = 100
MAX_IMAGE_BYTES = 1_000_000  # ~1 MB por foto ya decodificada
UPLOAD_TTL_SECONDS = 24 * 60 * 60  # Limpieza de huérfanos tras 24 h
JPEG_MAGIC = b"\xff\xd8\xff"
IMAGE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
DATA_URL_RE = re.compile(r"^data:image/jpeg;base64,(?P<data>[A-Za-z0-9+/=\s]+)$")

# Claves cortas para mantener la cookie de sesión pequeña.
KIND_TEXT = "t"
KIND_IMAGE = "i"

UPLOAD_DIR = Path(app.instance_path) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# --- Operaciones de la pila ---------------------------------------------------
def is_empty(stack: list[Any]) -> bool:
    """Devuelve True si la pila no contiene elementos."""
    return len(stack) == 0


def len_stack(stack: list[Any]) -> int:
    """Devuelve el número de elementos de la pila."""
    return len(stack)


def get_stack() -> list[dict[str, str]]:
    """Obtiene una copia de la pila almacenada en la sesión."""
    return list(session.get("stack", []))


def save_stack(stack: list[dict[str, str]]) -> None:
    """Guarda la pila en la sesión (marca la sesión como modificada)."""
    session["stack"] = stack
    session.modified = True


def make_text_item(value: str) -> dict[str, str]:
    return {"k": KIND_TEXT, "v": value}


def make_image_item(image_id: str) -> dict[str, str]:
    return {"k": KIND_IMAGE, "v": image_id}


def is_image(item: dict[str, str]) -> bool:
    return item.get("k") == KIND_IMAGE


def describe(item: dict[str, str]) -> str:
    """Texto corto para mostrar en mensajes."""
    if is_image(item):
        return "una foto"
    value = item["v"]
    return f"«{value if len(value) <= 40 else value[:37] + '...'}»"


# --- Gestión de archivos ------------------------------------------------------
def image_path(image_id: str) -> Path:
    return UPLOAD_DIR / f"{image_id}.jpg"


def delete_image_file(image_id: str) -> None:
    try:
        image_path(image_id).unlink(missing_ok=True)
    except OSError:
        logger.exception("No se pudo eliminar la imagen %s", image_id)


def cleanup_old_uploads() -> None:
    """Elimina fotos antiguas que quedaron huérfanas (sesiones expiradas)."""
    limit = time.time() - UPLOAD_TTL_SECONDS
    for path in UPLOAD_DIR.glob("*.jpg"):
        try:
            if path.stat().st_mtime < limit:
                path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Error limpiando %s", path)


def decode_jpeg_data_url(data_url: str) -> bytes | None:
    """Decodifica y valida un data-URL JPEG. Devuelve None si no es válido."""
    match = DATA_URL_RE.match(data_url or "")
    if not match:
        return None
    try:
        raw = base64.b64decode(match.group("data"), validate=False)
    except (binascii.Error, ValueError):
        return None
    if not raw.startswith(JPEG_MAGIC) or len(raw) > MAX_IMAGE_BYTES:
        return None
    return raw


# --- CSRF básico --------------------------------------------------------------
def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


@app.context_processor
def inject_helpers() -> dict[str, Any]:
    return {"csrf_token": csrf_token}


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            abort(400, description="Token CSRF inválido. Recarga la página.")


# --- Rutas --------------------------------------------------------------------
@app.get("/")
def index():
    stack = get_stack()
    return render_template(
        "index.html",
        stack=stack,
        stack_size=len_stack(stack),
        max_stack_size=MAX_STACK_SIZE,
        max_text_length=MAX_TEXT_LENGTH,
    )


@app.get("/images/<image_id>")
def serve_image(image_id: str):
    """Entrega una foto solo si pertenece a la pila de la sesión actual."""
    if not IMAGE_ID_RE.match(image_id):
        abort(404)
    if not any(is_image(i) and i["v"] == image_id for i in get_stack()):
        abort(404)
    response = send_from_directory(UPLOAD_DIR, f"{image_id}.jpg", mimetype="image/jpeg")
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@app.post("/push")
def push():
    """Apila un texto."""
    value = request.form.get("value", "").strip()
    if not value:
        flash("Escribe un valor antes de agregarlo a la pila.", "warning")
        return redirect(url_for("index"))
    if len(value) > MAX_TEXT_LENGTH:
        flash(f"El texto no puede superar {MAX_TEXT_LENGTH} caracteres.", "warning")
        return redirect(url_for("index"))

    stack = get_stack()
    if len(stack) >= MAX_STACK_SIZE:
        flash(f"La pila alcanzó el límite de {MAX_STACK_SIZE} elementos. Retira alguno antes de agregar más.", "warning")
        return redirect(url_for("index"))

    item = make_text_item(value)
    stack.append(item)
    save_stack(stack)
    flash(f"Se agregó {describe(item)} a la pila.", "success")
    return redirect(url_for("index"))


@app.post("/push-photo")
def push_photo():
    """Apila una foto enviada como data-URL JPEG. Responde JSON."""
    stack = get_stack()
    if len(stack) >= MAX_STACK_SIZE:
        return jsonify(ok=False, message=f"La pila alcanzó el límite de {MAX_STACK_SIZE} elementos."), 409

    raw = decode_jpeg_data_url(request.form.get("photo", ""))
    if raw is None:
        return jsonify(ok=False, message="La imagen no es válida o es demasiado grande."), 400

    cleanup_old_uploads()
    image_id = uuid.uuid4().hex
    try:
        image_path(image_id).write_bytes(raw)
    except OSError:
        logger.exception("No se pudo guardar la imagen")
        return jsonify(ok=False, message="No se pudo guardar la foto en el servidor."), 500

    stack.append(make_image_item(image_id))
    save_stack(stack)
    flash("Se agregó una foto a la pila.", "success")
    return jsonify(ok=True)


@app.post("/pop")
def pop():
    stack = get_stack()
    if is_empty(stack):
        flash("La pila está vacía; no hay elementos que retirar.", "warning")
        return redirect(url_for("index"))

    item = stack.pop()
    save_stack(stack)
    if is_image(item):
        delete_image_file(item["v"])
    flash(f"Se retiró {describe(item)} de la pila.", "success")
    return redirect(url_for("index"))


@app.post("/peek")
def peek():
    stack = get_stack()
    if is_empty(stack):
        flash("La pila está vacía; no hay elemento superior.", "warning")
    else:
        top = stack[-1]
        flash(f"Elemento en la cima: {describe(top)}.", "info")
    return redirect(url_for("index"))


@app.post("/clear")
def clear():
    for item in get_stack():
        if is_image(item):
            delete_image_file(item["v"])
    save_stack([])
    flash("La pila se vació correctamente.", "success")
    return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(_error):
    return jsonify(ok=False, message="La imagen es demasiado grande."), 413


if __name__ == "__main__":
    # Solo para desarrollo local. En producción usar un servidor WSGI y FLASK_DEBUG=0
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="127.0.0.1", port=5000)
