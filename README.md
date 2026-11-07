# DocInBox — Recepción local de documentos

DocInBox permite recibir archivos desde teléfonos y otras computadoras conectadas a la misma red local. El dispositivo cliente abre una página web y envía los documentos directamente al equipo receptor; no necesita instalar una aplicación.

## Primera base funcional

Esta etapa incorpora el receptor web y deja preparado el servicio para integrarlo con la ventana de escritorio PyQt6:

- Servidor Flask con página web adaptable a móvil y escritorio.
- Recepción individual de archivos mediante POST /api/upload. La página permite seleccionar varios archivos y los envía uno por uno.
- Endpoint GET /api/health para comprobar que el receptor está activo.
- Almacenamiento fuera del directorio del proyecto, con nombre interno único para evitar sobrescrituras.
- Normalización del nombre recibido, límite de tamaño configurable y respuestas JSON para errores.
- LanServerThread, basado en QThread, para ejecutar el servidor WSGI sin bloquear la futura interfaz de escritorio.
- Pruebas automatizadas del flujo HTTP y del almacenamiento.

El backend no impone una lista de extensiones: la validación de tipos y la vista previa de documentos se integrarán en las siguientes etapas. Los archivos recibidos se almacenan como datos; el receptor no los ejecuta ni ofrece una ruta pública para descargarlos.

## Requisitos

- Python 3.12 o compatible.
- Flask.
- PyQt6.
- PyMuPDF (la visualización de PDF se conectará desde la interfaz de escritorio).

Instala las dependencias:

    python -m pip install -r requirements.txt

## Iniciar el receptor

En el equipo que recibirá los documentos:

    python app.py

Por defecto, el servidor escucha en todas las interfaces de red, en el puerto 8765. Desde otro dispositivo conectado a la misma LAN, abre la dirección IPv4 del equipo receptor:

    http://IP_DEL_EQUIPO:8765

La dirección 0.0.0.0 es la dirección de enlace del servidor y no debe escribirse en el navegador del cliente. En Windows, puede consultarse la IPv4 local con ipconfig.

## Configuración por variables de entorno

| Variable | Valor predeterminado | Descripción |
|---|---:|---|
| DOCINBOX_HOST | 0.0.0.0 | Interfaz de red donde escucha el servidor. |
| DOCINBOX_PORT | 8765 | Puerto TCP del receptor. |
| DOCINBOX_MAX_UPLOAD_MB | 100 | Tamaño máximo de cada archivo. |
| DOCINBOX_STORAGE_DIR | %LOCALAPPDATA%/DocInBox/Received en Windows | Carpeta destino de los archivos recibidos. |

En sistemas distintos de Windows, la carpeta predeterminada es ~/Documents/DocInBox/Received.

## API inicial

### Comprobar el estado

GET /api/health

Respuesta:

    {"status": "ok", "service": "DocInBox Receiver"}

### Recibir un archivo

POST /api/upload con multipart/form-data y un campo llamado file.

Respuesta 201 Created:

    {
      "id": "identificador-unico",
      "filename": "documento.pdf",
      "size": 12345,
      "received_at": "2026-11-06T12:00:00+00:00",
      "status": "received"
    }

## Ejecutar pruebas

    python -m unittest discover -s tests -v

## Consideraciones de red y seguridad

Esta primera versión está pensada para una LAN de confianza. Cualquier dispositivo que pueda alcanzar el puerto del servidor puede enviar archivos; todavía no hay autenticación, emparejamiento por QR ni control de usuarios. Mantén el receptor en una red privada y limita el acceso al puerto 8765 mediante el firewall del equipo. No expongas este servicio directamente a Internet.

## Arquitectura prevista

    Dispositivo cliente (navegador)
              | HTTP / LAN
              v
         Flask Receiver
              |
              v
      Carpeta de documentos recibidos
              |
              v
      Servicio de vigilancia / cola
              | señales Qt
              v
        Interfaz PyQt6
              |
              v
      Vista previa / impresión

La cola de documentos, la vista previa nativa, el QR de acceso y la integración de impresión quedan fuera de esta primera base para implementarse como módulos independientes.
