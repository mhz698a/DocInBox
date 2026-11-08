# DocInBox — Recepción y administración de documentos

DocInBox recibe documentos desde teléfonos y computadoras y permite administrarlos desde una aplicación de escritorio PyQt6. Flask escucha exclusivamente en localhost y localhost.run proporciona una dirección HTTPS pública temporal.

## Funcionalidad

### Receptor web
- Página adaptable para seleccionar o arrastrar varios documentos.
- Recepción individual de archivos, con registro de cada llegada en SQLite.
- Tamaño máximo configurable, nombres saneados y nombres internos únicos.
- Validación de extensiones tanto en el navegador como en el endpoint Flask.
- Almacenamiento fuera del directorio del proyecto.

### Administración de llegadas
- Ventana de escritorio PyQt6 que inicia el receptor automáticamente.
- Tabla con búsqueda, filtro por estado y contadores.
- Abrir documento, mostrar ubicación, copiar ruta, marcar como atendido/pendiente y eliminar.
- Generar un PDF imprimible del código QR de acceso activo; permite elegir dónde guardarlo y abrirlo al terminar.
- Al abrir la aplicación, si existen documentos de sesiones anteriores se pregunta si se desea limpiar la bandeja. La limpieza elimina los archivos y sus registros; no se puede deshacer. Si se elige No, los documentos se conservan.
- Si algún archivo no puede eliminarse, su registro permanece para permitir una limpieza posterior.

### Tipos de archivo permitidos
El botón Permitir tipo de archivos abre una lista de casillas configurables. Los valores se guardan en QSettings y se aplican inmediatamente en el servidor.

Extensiones disponibles: doc, docx, xlsx, xls, ppt, pptx, pdf, png, jpg, jpeg, gif, txt, mp3, wav, flac, m4a, mp4, mkv y avi.

### Túnel SSH mediante localhost.run
- Se inicia automáticamente al arrancar el receptor.
- Flask escucha únicamente en 127.0.0.1; no se enlaza a la interfaz de red local.
- OpenSSH ejecuta el túnel dentro de un QThread y sin abrir una ventana de consola.
- Se usa el usuario documentado nokey@localhost.run para el plan gratuito; no se generan claves SSH de usuario ni se requiere registro.
- El QR muestra exclusivamente la URL HTTPS temporal anunciada por localhost.run.
- Se aceptan los dominios gratuitos documentados bajo localhost.run y lhr.life; la dirección se detecta desde la salida de SSH.
- La clave del servidor SSH se conserva mediante StrictHostKeyChecking=accept-new: la primera conexión se recuerda automáticamente y los cambios posteriores se rechazan.
- Se desactiva la inyección de cabeceras HTTP de proxy. La página y POST /api/upload siguen protegidos por una clave temporal de DocInBox.
- Si falla la conexión, el receptor permanece privado y no muestra la dirección local.

Los dominios gratuitos son temporales y pueden cambiar regularmente o después de unas horas. DocInBox vuelve a generar el QR con la dirección que entrega cada nueva conexión. La IP pública de origen sigue siendo visible para localhost.run como proveedor del túnel; los dispositivos que escanean el QR solo reciben la dirección pública y nunca la IP local del equipo.

Documentación oficial:
- https://localhost.run/docs
- https://localhost.run/docs/faq
- https://localhost.run/docs/security
- https://localhost.run/docs/cli
## Requisitos

- Python 3.12 o compatible.
- Flask, PyQt6 y PyMuPDF.
- qrcode con Pillow.
- OpenSSH Client (ssh.exe).

En Windows, OpenSSH Client puede instalarse desde Características opcionales. Verifica su disponibilidad con:

    ssh -V

Instala las dependencias Python:

    python -m pip install -r requirements.txt

## Iniciar DocInBox

    python app.py

La aplicación inicia Flask en localhost y crea automáticamente el túnel SSH sin cuenta ni registro. Cuando localhost.run anuncie la dirección HTTPS temporal, aparecerá el QR público.

Para iniciar únicamente Flask en modo de desarrollo local:

    python app.py --web-only

Este modo no genera túnel y no permite recibir archivos desde otros dispositivos.

## Datos locales en Windows

- Documentos: %LOCALAPPDATA%/DocInBox/Received
- Base de datos: %LOCALAPPDATA%/DocInBox/inbox.sqlite3
- Clave de host SSH aprendida en la primera conexión: %LOCALAPPDATA%/DocInBox/ssh/localhostrun_known_hosts

## Variables de entorno

| Variable | Valor predeterminado | Descripción |
|---|---:|---|
| DOCINBOX_PORT | 8765 | Puerto TCP local. |
| DOCINBOX_MAX_UPLOAD_MB | 100 | Tamaño máximo por archivo. |
| DOCINBOX_DATA_DIR | Directorio de datos del usuario | Directorio base local. |
| DOCINBOX_STORAGE_DIR | DATA_DIR/Received | Carpeta de archivos recibidos. |
| DOCINBOX_DATABASE_PATH | DATA_DIR/inbox.sqlite3 | Base de datos SQLite. |
| DOCINBOX_LOCALHOSTRUN_SSH_PORT | 22 | Puerto SSH de localhost.run. |

## API inicial

### Estado

GET /api/health

    {"status": "ok", "service": "DocInBox Receiver"}

### Recepción

POST /api/upload con multipart/form-data y un campo llamado file. Cuando el túnel está activo, requiere X-DocInBox-Key.

Las extensiones no habilitadas reciben HTTP 415. Los archivos mayores al límite reciben HTTP 413.

## Pruebas

    python -m unittest discover -s tests -v

## Seguridad

El servidor Flask no escucha en la IP LAN: solo en loopback. La dirección pública es proporcionada por localhost.run y el acceso al formulario requiere una clave temporal. La URL HTTPS termina TLS en el proxy de localhost.run y el tráfico continúa cifrado por SSH hasta el servidor local. El proveedor conoce la IP pública de origen de la conexión SSH, pero los remitentes no reciben la IP local del equipo. La primera clave SSH del servidor se acepta y almacena automáticamente; una clave cambiada posteriormente provoca el rechazo del túnel.

## Arquitectura

    Navegador móvil
          | HTTPS
          v
    localhost.run reverse proxy
          | SSH autenticado
          v
    127.0.0.1:8765
          |
          +--> Flask Receiver
          |
          +--> DocumentStore (SQLite)
          |
          +--> Received/
          |
          v
    Bandeja de administración PyQt6
