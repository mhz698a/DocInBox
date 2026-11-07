# DocInBox — Recepción y administración de documentos

DocInBox recibe documentos desde teléfonos y computadoras y permite administrarlos desde una aplicación de escritorio PyQt6. El servidor Flask trabaja en un hilo Qt independiente.

## Funcionalidad implementada

### Receptor web
- Página web adaptable para seleccionar o arrastrar documentos.
- Recepción de varios archivos, enviados individualmente.
- Límite de tamaño configurable, rechazo de archivos vacíos y normalización de nombres.
- Almacenamiento fuera del directorio del proyecto y nombres internos únicos.
- Registro de cada recepción en SQLite.

### Administración de llegadas
- Ventana de escritorio que inicia el servidor Flask automáticamente.
- Tabla de documentos recibidos con búsqueda y filtro por estado.
- Contadores de documentos totales, pendientes y atendidos.
- Abrir archivo, mostrar su ubicación, copiar la ruta, marcar como atendido o pendiente y eliminarlo.
- Actualización de la bandeja cuando Flask registra una recepción.

### Publicación mediante Pinggy
- Inicio y detención del túnel desde la ventana.
- El SDK de Pinggy se ejecuta fuera del hilo de interfaz.
- El QR cambia automáticamente de la URL LAN a la URL pública HTTPS.
- El enlace público incluye una clave aleatoria temporal. La página y el endpoint de subida la validan; al detener el túnel, la clave se invalida.
- El servidor local sigue atendiendo en la red LAN.

El enlace/QR público funciona como una invitación: cualquiera que obtenga una copia puede enviar documentos mientras el túnel siga activo. Detén el túnel cuando termines de recibir archivos. El plan gratuito de Pinggy puede tener duración limitada y generar una URL diferente al volver a iniciar el túnel; consulta sus condiciones vigentes.

## Requisitos

- Python 3.12 o compatible.
- Flask.
- PyQt6.
- PyMuPDF.
- Pinggy Python SDK.
- qrcode con Pillow.

Instalación:

    python -m pip install -r requirements.txt

## Iniciar DocInBox

La aplicación de escritorio inicia el receptor automáticamente:

    python app.py

Para iniciar solamente Flask, sin abrir PyQt6:

    python app.py --web-only

Por defecto, el receptor escucha en todas las interfaces de red, en el puerto 8765. En la ventana se muestra la URL local y su QR. En otro dispositivo conectado a la misma red, escanea el QR o abre la dirección IPv4 del equipo receptor.

## Publicar con Pinggy

1. Inicia DocInBox y espera a que el estado indique que el receptor está activo.
2. Pulsa Publicar con Pinggy.
3. La aplicación crea el túnel y espera la URL pública HTTPS.
4. Cuando se conecte, el QR mostrará el enlace público protegido con una clave temporal.
5. Comparte el QR o enlace con los dispositivos que deban enviar archivos.
6. Pulsa Detener túnel cuando termines. La clave anterior dejará de ser válida y el QR volverá a la dirección LAN.

La integración utiliza el SDK oficial de Python; no requiere iniciar manualmente otra ventana de terminal. El paquete pinggy se instala con requirements.txt.

## Datos locales

En Windows, la configuración predeterminada utiliza:

- Documentos: %LOCALAPPDATA%/DocInBox/Received
- Base de datos: %LOCALAPPDATA%/DocInBox/inbox.sqlite3

En otros sistemas, los datos se guardan en ~/.local/share/DocInBox.

## Variables de entorno

| Variable | Valor predeterminado | Descripción |
|---|---:|---|
| DOCINBOX_HOST | 0.0.0.0 | Interfaz de red donde escucha Flask. |
| DOCINBOX_PORT | 8765 | Puerto TCP local. |
| DOCINBOX_MAX_UPLOAD_MB | 100 | Tamaño máximo de cada archivo. |
| DOCINBOX_DATA_DIR | Directorio de datos del usuario | Directorio base de datos local. |
| DOCINBOX_STORAGE_DIR | DATA_DIR/Received | Carpeta de documentos recibidos. |
| DOCINBOX_DATABASE_PATH | DATA_DIR/inbox.sqlite3 | Base SQLite de la bandeja. |

## API inicial

### Estado
GET /api/health

    {"status": "ok", "service": "DocInBox Receiver"}

### Recepción
POST /api/upload con multipart/form-data, campo file.

Cuando se usa Pinggy, se requiere el encabezado X-DocInBox-Key, entregado solamente a la página abierta con la clave temporal.

## Pruebas

    python -m unittest discover -s tests -v

## Consideraciones de seguridad

El servicio LAN no tiene autenticación cuando el túnel está apagado y debe usarse dentro de una red privada de confianza. Al iniciar Pinggy se activa una clave aleatoria que protege la página y la recepción pública; no se debe compartir el enlace más allá de los destinatarios previstos. El túnel HTTPS termina TLS en la infraestructura de Pinggy y reenvía la petición al servidor local. No expongas el servicio directamente a Internet ni mantengas el túnel abierto sin necesidad.

## Arquitectura

    Navegador cliente
         | HTTP / HTTPS
         v
    Flask Receiver
         |
         +--> DocumentStore (SQLite)
         |         |
         |         v
         |      Bandeja PyQt6
         |
         +--> Carpeta Received
         |
    Pinggy SDK (opcional)
         |
         v
    URL pública HTTPS + QR

La vista previa nativa de PDF, la impresión, los perfiles de remitente y la política de retención se implementarán en etapas posteriores.
