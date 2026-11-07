# DocInBox — Recepción y administración de documentos

DocInBox recibe documentos desde teléfonos y computadoras y permite administrarlos desde una aplicación de escritorio PyQt6. Flask escucha exclusivamente en localhost y Serveo proporciona la dirección pública HTTPS.

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
- Al abrir la aplicación, si existen documentos de sesiones anteriores se pregunta si se desea limpiar la bandeja. La limpieza elimina los archivos y sus registros; no se puede deshacer. Si se elige No, los documentos se conservan.
- Si algún archivo no puede eliminarse, su registro permanece para permitir una limpieza posterior.

### Tipos de archivo permitidos
El botón Permitir tipo de archivos abre una lista de casillas configurables. Los valores se guardan en QSettings y se aplican inmediatamente en el servidor.

Extensiones disponibles: doc, docx, xlsx, xls, ppt, pptx, pdf, png, jpg, jpeg, gif, txt, mp3, wav, flac, m4a, mp4, mkv y avi.

### Serveo SSH
- Se inicia automáticamente al arrancar el receptor.
- Flask escucha únicamente en 127.0.0.1; no se enlaza a la interfaz de red local.
- OpenSSH ejecuta el túnel dentro de un QThread y sin abrir una ventana de consola.
- El QR muestra exclusivamente una URL HTTPS pública de Serveo.
- La integración solicita un subdominio reservado aleatorio y exige una identidad SSH registrada. No utiliza túneles anónimos, porque Serveo indica que los túneles anónimos pueden revelar la IP de origen en el subdominio y en cabeceras HTTP.
- Se verifica la huella Ed25519 del servidor Serveo antes de permitir la conexión. Si la huella no coincide, no se abre el túnel.
- La página y POST /api/upload están protegidos por una clave temporal. Si la autenticación SSH o el túnel fallan, no se muestra una URL local ni se hace fallback a un túnel anónimo.

La clave pública SSH se genera una sola vez en el directorio de datos de DocInBox. En el primer inicio, la ventana muestra la clave y abre la consola de Serveo para que se registre. La clave privada permanece en el equipo. Si se elimina o sustituye, será necesario registrar la nueva clave.

Con cuentas gratuitas o túneles anónimos, Serveo puede mostrar una pantalla intermedia de advertencia al visitante. Si aparece, el destinatario debe continuar para llegar al formulario. Los túneles HTTP de cuentas de pago no muestran esa pantalla.

Documentación de Serveo:
- https://serveo.net/docs/
- https://serveo.net/terms/

## Requisitos

- Python 3.12 o compatible.
- Flask, PyQt6 y PyMuPDF.
- qrcode con Pillow.
- OpenSSH Client (ssh, ssh-keygen y ssh-keyscan).

En Windows, OpenSSH Client puede instalarse desde Características opcionales. Verifica su disponibilidad con:

    ssh -V
    ssh-keygen -?
    ssh-keyscan -?

Instala las dependencias Python:

    python -m pip install -r requirements.txt

## Iniciar DocInBox

    python app.py

La aplicación inicia Flask en localhost y crea automáticamente el túnel SSH. En el primer inicio, registra la clave pública que aparece en el diálogo de configuración de Serveo. Cuando el túnel se confirme, aparecerá el QR público.

Para iniciar únicamente Flask en modo de desarrollo local:

    python app.py --web-only

Este modo no genera túnel y no permite recibir archivos desde otros dispositivos.

## Datos locales en Windows

- Documentos: %LOCALAPPDATA%/DocInBox/Received
- Base de datos: %LOCALAPPDATA%/DocInBox/inbox.sqlite3
- Identidad SSH: %LOCALAPPDATA%/DocInBox/ssh/docinbox_ed25519
- Clave pública: %LOCALAPPDATA%/DocInBox/ssh/docinbox_ed25519.pub
- Huella conocida del servidor: %LOCALAPPDATA%/DocInBox/ssh/known_hosts

## Variables de entorno

| Variable | Valor predeterminado | Descripción |
|---|---:|---|
| DOCINBOX_PORT | 8765 | Puerto TCP local. |
| DOCINBOX_MAX_UPLOAD_MB | 100 | Tamaño máximo por archivo. |
| DOCINBOX_DATA_DIR | Directorio de datos del usuario | Directorio base local. |
| DOCINBOX_STORAGE_DIR | DATA_DIR/Received | Carpeta de archivos recibidos. |
| DOCINBOX_DATABASE_PATH | DATA_DIR/inbox.sqlite3 | Base de datos SQLite. |
| DOCINBOX_SERVEO_SSH_KEY | DATA_DIR/ssh/docinbox_ed25519 | Ruta alternativa a una clave SSH registrada. |
| DOCINBOX_SERVEO_SSH_PORT | 22 | Puerto SSH de Serveo. |

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

El servidor Flask no escucha en la IP LAN: solo en loopback. La dirección pública es proporcionada por Serveo y el acceso al formulario requiere una clave temporal. El túnel es HTTPS en el extremo público y SSH entre el equipo receptor y Serveo; el tráfico termina en el proxy público antes de reenviarse al servidor local.

La identidad SSH debe estar registrada en Serveo. No se debe desactivar la verificación de la huella del host ni recurrir a un túnel anónimo para solventar errores de autenticación. Si la conexión falla, el receptor permanece privado.

## Arquitectura

    Navegador móvil
          | HTTPS
          v
    Serveo reverse proxy
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
