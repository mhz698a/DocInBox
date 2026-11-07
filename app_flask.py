"""Flask application that receives files from devices on the local network."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, current_app, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from config import Config

BASE_DIR = Path(__file__).resolve().parent


def create_app(test_config: dict | None = None) -> Flask:
    """Create the receiver application.

    The existing templates directory also contains the small static assets
    used by the upload page. They are exposed under /assets.
    """
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "templates"),
        static_url_path="/assets",
    )
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    app.config["UPLOAD_FOLDER"] = Path(app.config["UPLOAD_FOLDER"]).expanduser()
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            max_upload_mb=app.config["MAX_UPLOAD_MB"],
        )

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "DocInBox Receiver"}), 200

    @app.post("/api/upload")
    def upload_file():
        uploaded_file = request.files.get("file")
        if uploaded_file is None:
            return jsonify({"error": "No se recibió ningún archivo."}), 400

        original_name = (uploaded_file.filename or "").strip()
        safe_name = secure_filename(original_name)
        if not safe_name:
            return jsonify({"error": "El nombre del archivo no es válido."}), 400

        upload_id = uuid4().hex
        upload_folder: Path = current_app.config["UPLOAD_FOLDER"]
        stored_name = f"{upload_id}_{safe_name}"
        destination = upload_folder / stored_name
        temporary_path = upload_folder / f".{upload_id}.part"

        try:
            uploaded_file.save(temporary_path)
            file_size = temporary_path.stat().st_size

            if file_size == 0:
                temporary_path.unlink(missing_ok=True)
                return jsonify({"error": "El archivo está vacío."}), 400

            if file_size > current_app.config["MAX_UPLOAD_BYTES"]:
                temporary_path.unlink(missing_ok=True)
                limit_mb = current_app.config["MAX_UPLOAD_MB"]
                return jsonify(
                    {"error": f"El archivo supera el límite de {limit_mb} MB."}
                ), 413

            temporary_path.replace(destination)
        except OSError:
            temporary_path.unlink(missing_ok=True)
            current_app.logger.exception("No se pudo guardar el archivo recibido.")
            return jsonify(
                {"error": "No fue posible guardar el archivo en el servidor."}
            ), 500

        received_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        current_app.logger.info(
            "Documento recibido: %s (%s bytes, id=%s)",
            safe_name,
            file_size,
            upload_id,
        )

        return jsonify(
            {
                "id": upload_id,
                "filename": safe_name,
                "size": file_size,
                "received_at": received_at,
                "status": "received",
            }
        ), 201

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        limit_mb = app.config["MAX_UPLOAD_MB"]
        return jsonify(
            {"error": f"El archivo supera el límite de {limit_mb} MB."}
        ), 413

    return app


def main() -> None:
    """Run the standalone LAN receiver for development and initial testing."""
    from werkzeug.serving import run_simple

    app = create_app()
    print(
        f"DocInBox está escuchando en http://{Config.HOST}:{Config.PORT} "
        f"(límite: {Config.MAX_UPLOAD_MB} MB por archivo)."
    )
    run_simple(
        Config.HOST,
        Config.PORT,
        app,
        threaded=True,
        use_reloader=False,
        use_debugger=False,
    )


if __name__ == "__main__":
    main()
