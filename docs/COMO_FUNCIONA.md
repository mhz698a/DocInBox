# Cómo funciona DocInBox
## Guía técnica de arquitectura y funcionamiento

Este documento explica el diseño interno de DocInBox para que una persona pueda estudiar el proyecto, seguir el recorrido de una petición y entender la responsabilidad de cada módulo.

La implementación descrita corresponde al código actual de esta rama: **recepción directa por red local mediante HTTP**. No hay un proveedor de túnel activo en el flujo de ejecución.

---

## 1. Objetivo y modelo mental

DocInBox tiene dos partes que cooperan:

1. **Aplicación anfitriona:** se ejecuta en el equipo que recibe y almacena los documentos. Su interfaz está construida con PyQt6.
2. **Página remitente:** se abre desde el navegador de un teléfono, tableta u otro equipo. Permite seleccionar archivos y enviarlos al servidor Flask.

El navegador no almacena los documentos. Envía cada archivo al equipo anfitrión. Flask valida la solicitud, almacena el contenido y registra sus metadatos en SQLite. La interfaz de escritorio consulta ese registro y representa las llegadas.

~~~mermaid
flowchart TD
    A["Dispositivo remitente<br/>Navegador web"] -->|"HTTP + clave"| B["Flask / Werkzeug"]
    B --> C["Validación de solicitud"]
    C --> D["Carpeta Received"]
    C --> E["DocumentStore"]
    E --> F[("SQLite")]
    G["Aplicación PyQt6"] --> H["InboxWatcher"]
    H --> E
    H --> G
    G --> I["Tabla y estadísticas"]
    G --> J["Código QR y exportación PDF"]
~~~

La aplicación de escritorio es el proceso anfitrión. El navegador es un cliente HTTP independiente que no necesita instalar Python, PyQt6 ni DocInBox.

## 2. Componentes principales

### 2.1. Punto de entrada: app.py

app.py decide qué modo debe iniciar:

- Sin argumentos, importa y ejecuta ui.wmain.main(), que abre la aplicación PyQt6.
- Con --web-only, importa app_flask.main() y ejecuta Flask en modo de desarrollo local.

La importación de la interfaz se realiza después de comprobar los argumentos. Así, el modo web no necesita crear la ventana PyQt6.

### 2.2. Configuración: config.py

La clase Config centraliza los valores predeterminados:

- Puerto HTTP: 8765.
- Tamaño máximo individual: 100 MiB.
- Directorio raíz de datos del usuario.
- Carpeta de documentos recibidos.
- Ruta de la base SQLite.
- Host 127.0.0.1 usado por el modo --web-only.

get_program_path() resuelve dónde están los recursos de la aplicación. En desarrollo usa el directorio del proyecto. En una aplicación congelada por PyInstaller usa sys._MEIPASS, que corresponde al directorio interno del bundle onedir.

El servidor iniciado por la interfaz de escritorio tiene un parámetro de host propio: LanServerThread usa 0.0.0.0 para admitir conexiones por las interfaces de red del equipo. Por ello, no debe confundirse el valor Config.HOST del modo web de desarrollo con el host que usa el modo de escritorio.

Las variables de entorno que controlan la configuración son:

| Variable | Uso |
|---|---|
| DOCINBOX_PORT | Puerto del receptor. |
| DOCINBOX_MAX_UPLOAD_MB | Tamaño máximo de cada archivo. |
| DOCINBOX_DATA_DIR | Directorio base de los datos. |
| DOCINBOX_STORAGE_DIR | Carpeta donde se conservan los archivos. |
| DOCINBOX_DATABASE_PATH | Ruta del archivo SQLite. |

### 2.3. Orquestador de escritorio: ui/wmain.py

MainWindow conecta los componentes y administra el ciclo de vida del receptor.

Sus responsabilidades principales son:

- Crear la aplicación Flask mediante create_app().
- Obtener el DocumentStore que Flask dejó en app.extensions.
- Cargar las extensiones permitidas de QSettings.
- Preguntar si se desea limpiar los documentos de sesiones anteriores.
- Construir la interfaz de administración.
- Crear e iniciar InboxWatcher.
- Iniciar LanServerThread después de mostrar la ventana.
- Crear o recuperar la clave de acceso persistente.
- Iniciar la detección de la dirección IPv4.
- Actualizar el QR y habilitar la exportación a PDF.
- Atender acciones de la tabla.
- Detener los hilos al apagar la ventana.

La ventana no contiene la implementación del servidor ni el SQL de la base de datos. Coordina servicios y widgets especializados.

### 2.4. Servidor de red: services/lan_server.py

LanServerThread hereda de QThread. Dentro de run() crea un servidor Werkzeug con:

- Host predeterminado 0.0.0.0.
- Puerto configurado.
- Aplicación Flask creada por create_app().
- threaded=True, que permite atender solicitudes HTTP mediante hilos de petición.

Cuando el servidor termina de enlazar el puerto, emite server_ready. La ventana recibe esa señal y comienza la detección de la dirección LAN.

El hilo expone tres señales:

| Señal | Propósito |
|---|---|
| server_ready(port) | El servidor ya está escuchando. |
| server_error(message) | No se pudo iniciar o mantener el servidor. |
| server_stopped() | El servidor terminó de ejecutarse. |

stop() solicita el apagado de Werkzeug sin ejecutar shutdown() bloqueando directamente el hilo de interfaz.

### 2.5. Detección de dirección LAN: services/localhostrun_tunnel.py

El nombre del archivo y de la clase LocalhostRunTunnelThread procede de una versión anterior. En el código actual se conserva para no romper las importaciones existentes, pero **ya no inicia localhost.run ni otro proveedor externo**.

La implementación actual ofrece dos funciones:

- detect_lan_ipv4(): consulta la tabla de rutas del sistema usando un socket UDP conectado a 10.255.255.255:1. No envía un archivo ni contenido de aplicación; usa el socket para obtener la dirección local seleccionada por el sistema operativo.
- build_lan_url(ip_address, port): valida una dirección IPv4 y un puerto y devuelve http://<ip>:<port>.

Si la detección falla, se usa 127.0.0.1 como fallback. Esa dirección solo es accesible desde el propio equipo, por lo que no sirve como dirección para otros dispositivos.

**La detección no reserva una IP estática.** Si el router cambia la concesión DHCP o el equipo cambia de interfaz, la dirección del QR puede cambiar. Para que un QR impreso conserve la misma dirección conviene reservar la IP del equipo en el servidor DHCP del router.

El hilo emite tunnel_ready y la ventana reutiliza esa señal para recibir la URL LAN. El nombre histórico de la señal tampoco implica que exista un túnel.

### 2.6. Aplicación web: app_flask.py

create_app() construye la instancia Flask y prepara sus dependencias.

Durante la inicialización:

1. Registra las carpetas templates.
2. Carga los valores de Config.
3. Aplica los valores de prueba cuando se proporciona test_config.
4. Normaliza las rutas de almacenamiento y base de datos.
5. Crea los directorios necesarios.
6. Normaliza las extensiones permitidas.
7. Crea DocumentStore, salvo que una prueba haya proporcionado uno.
8. Registra el repositorio en app.extensions["document_store"].

La función has_access() compara la clave presentada con la configurada usando secrets.compare_digest(). La comparación evita comparar cadenas secretas con una operación ordinaria de igualdad que pueda revelar diferencias de tiempo.

Las rutas HTTP principales son:

| Ruta | Método | Función |
|---|---|---|
| / | GET | Renderiza el formulario web; valida key cuando hay una clave configurada. |
| /api/health | GET | Devuelve un indicador de disponibilidad. |
| /api/upload | POST | Recibe y guarda un archivo. |

La ruta de salud no exige la clave de acceso. La página y la recepción sí la exigen cuando ACCESS_TOKEN tiene un valor.

## 3. Secuencia de inicio

Cuando el usuario ejecuta python app.py, el flujo del modo de escritorio es:

~~~mermaid
sequenceDiagram
    participant Entry as app.py
    participant UI as MainWindow
    participant Flask as create_app()
    participant DB as DocumentStore
    participant Watcher as InboxWatcher
    participant Server as LanServerThread
    participant LAN as Detector IPv4

    Entry->>UI: main()
    UI->>Flask: create_app()
    Flask->>DB: Inicializar SQLite
    DB-->>Flask: DocumentStore listo
    UI->>UI: Cargar QSettings y construir widgets
    UI->>DB: Consultar documentos anteriores
    UI->>Watcher: start()
    Watcher->>DB: list_documents()
    UI->>Server: start()
    Server->>Server: make_server(0.0.0.0, puerto)
    Server-->>UI: server_ready(puerto)
    UI->>UI: Recuperar o crear clave persistente
    UI->>LAN: start()
    LAN-->>UI: URL HTTP con IPv4 local
    UI->>UI: Construir URL con parámetro key y actualizar QR
~~~

### 3.1. Limpieza inicial

Antes de construir la interfaz, MainWindow._prompt_startup_cleanup() consulta DocumentStore.list_documents().

- Si la bandeja está vacía, no se muestra el diálogo.
- Si hay registros, se presenta el número de archivos y su tamaño acumulado.
- Si se elige No, los archivos permanecen.
- Si se elige Sí, clear_all_documents() intenta eliminar cada archivo y retira de SQLite únicamente los registros que pudo limpiar.
- Los archivos que no pueden eliminarse conservan su registro para permitir otro intento.

La limpieza es permanente. No existe una papelera de reciclaje ni una operación de deshacer.

## 4. Cómo funciona el enlace QR

La ventana usa QSettings("DocInBox", "DocInBox").

La clave se recupera con la entrada security/access_token. Si no existe, se genera con secrets.token_urlsafe(32), se guarda y se sincroniza con QSettings.

La dirección base que entrega el detector, por ejemplo:

~~~text
http://192.168.1.25:8765
~~~

se combina con la clave:

~~~text
http://192.168.1.25:8765/?key=<clave-persistente>
~~~

Esa URL completa se utiliza para:

- Generar el QR visible.
- Habilitar Copiar enlace y Abrir.
- Generar el PDF imprimible.

El QR no contiene una dirección pública de Internet. Contiene una dirección de red local. Para abrirla, el dispositivo necesita una ruta de red hacia el equipo anfitrión.

La clave es persistente entre ejecuciones. Por ello, un PDF puede seguir conteniendo una clave válida, pero el QR dejará de resolver si cambia la IPv4 o si el servidor deja de estar activo.

## 5. Recorrido de una recepción

Esta es la parte central del programa. La recepción se ejecuta en dos procesos lógicos: el navegador cliente y el servidor Flask anfitrión.

### 5.1. El navegador prepara el archivo

templates/index.html contiene el formulario y los elementos visuales. Flask inserta en la página:

- El límite de tamaño por archivo.
- Las extensiones aceptadas para el atributo accept.
- La clave de acceso en la etiqueta meta docinbox-key.

templates/app.js obtiene esos elementos y administra la selección:

1. Escucha el evento change del selector de archivos.
2. Escucha dragenter, dragover, dragleave y drop.
3. Dibuja una lista con los nombres y tamaños.
4. Activa el botón de envío cuando hay archivos seleccionados.
5. Al enviar, recorre la lista y crea un FormData por archivo.
6. Ejecuta un fetch() POST a /api/upload.
7. Añade el resultado de cada archivo a la página.

Los archivos se envían **uno por uno en secuencia**. Si uno falla, el JavaScript registra el error y continúa con los siguientes.

La clave de acceso se adjunta a cada solicitud mediante la cabecera X-DocInBox-Key.

### 5.2. Flask valida la solicitud

La ruta upload_file() realiza las verificaciones en este orden:

1. Comprueba la clave de acceso.
2. Verifica que exista el campo multipart llamado file.
3. Obtiene el nombre original.
4. Aplica secure_filename() para sanear el nombre.
5. Comprueba que la extensión esté en la lista permitida.
6. Guarda temporalmente el archivo.
7. Calcula el tamaño real guardado.
8. Rechaza los archivos vacíos.
9. Rechaza los archivos que superan MAX_UPLOAD_BYTES.
10. Mueve el archivo temporal a su nombre definitivo.
11. Registra los metadatos en SQLite.
12. Devuelve HTTP 201 con la información de la llegada.

El servidor no confía exclusivamente en el atributo accept de HTML. Esa propiedad ayuda a la selección en el navegador, pero la regla real se comprueba nuevamente en Flask.

### 5.3. Escritura segura en dos etapas

El archivo primero se guarda con un nombre temporal:

~~~text
.9d5...e81.part
~~~

Después de comprobar que no está vacío y que su tamaño está dentro del límite, se renombra a una ruta definitiva:

~~~text
<uuid>_<nombre_saneado>
~~~

El UUID evita que dos cargas con el mismo nombre colisionen.

Luego se inserta el registro en SQLite. Si el registro falla, Flask intenta eliminar el archivo definitivo para no dejar un archivo huérfano sin metadatos.

El almacenamiento temporal y el renombrado separan la escritura incompleta del archivo que la bandeja considera recibido.

~~~mermaid
flowchart TD
    A["POST /api/upload"] --> B{"Clave correcta"}
    B -- "No" --> E["403 Forbidden"]
    B -- "Sí" --> C{"Archivo presente y nombre válido"}
    C -- "No" --> F["400 Bad Request"]
    C -- "Sí" --> D{"Extensión permitida"}
    D -- "No" --> G["415 Unsupported Media Type"]
    D -- "Sí" --> H["Guardar .part"]
    H --> I{"Tamaño válido y no vacío"}
    I -- "No" --> J["Eliminar temporal y responder error"]
    I -- "Sí" --> K["Renombrar a UUID_nombre"]
    K --> L["Insertar metadatos en SQLite"]
    L --> M{"Registro correcto"}
    M -- "No" --> N["Eliminar archivo final y responder 500"]
    M -- "Sí" --> O["201 Created"]
~~~

### 5.4. Cómo se actualiza la ventana

InboxWatcher es un QObject con un QTimer de un segundo.

En cada actualización:

1. Llama a DocumentStore.list_documents().
2. Forma una firma con los campos que afectan a la representación: ID, nombre, tamaño, fecha y estado.
3. Compara esa firma con la última observada.
4. Si no cambió, no emite una señal.
5. Si cambió, emite documents_changed con la lista actual.

MainWindow._documents_changed() entrega los datos a DocsTableTab y StatsTableTab. De esa manera, Flask no necesita importar ni manipular widgets PyQt6.

## 6. Almacenamiento y modelo SQLite

El repositorio está encapsulado en services/document_store.py.

La tabla principal es documents:

| Campo | Tipo | Propósito |
|---|---|---|
| id | TEXT PRIMARY KEY | UUID único de la llegada. |
| filename | TEXT | Nombre saneado que se muestra al usuario. |
| stored_path | TEXT | Ruta absoluta del archivo guardado. |
| size | INTEGER | Tamaño en bytes; debe ser mayor que cero. |
| received_at | TEXT | Fecha y hora ISO 8601 en UTC. |
| status | TEXT | pending o handled. |

Se crea un índice por received_at para ordenar las llegadas más recientes.

DocumentStore abre una conexión por operación y configura busy_timeout en 10 segundos. Las operaciones de escritura hacen commit() y, cuando corresponde, rollback().

### Operaciones disponibles

- add_document(): agrega los metadatos de una llegada.
- list_documents(): devuelve los registros en orden descendente por fecha.
- get_document(): obtiene un elemento por ID.
- set_status(): cambia entre pending y handled.
- delete_document(): elimina el archivo y después su registro.
- clear_all_documents(): intenta limpiar la bandeja completa y conserva los registros de los archivos que fallaron al eliminarse.

La base SQLite contiene metadatos. El contenido binario de los documentos se guarda en la carpeta Received.

## 7. Preferencias y datos del usuario

En Windows, el directorio de datos predeterminado es:

~~~text
%LOCALAPPDATA%/DocInBox/
├── Received/
└── inbox.sqlite3
~~~

Las preferencias de QSettings incluyen, entre otras:

| Clave QSettings | Contenido |
|---|---|
| uploads/allowed_extensions | Extensiones habilitadas. |
| security/access_token | Clave compartida incluida en el QR. |

Estas preferencias pertenecen al usuario de Windows. No se deben guardar en la carpeta de instalación de Program Files, porque el usuario normal no debería necesitar permisos de escritura sobre los binarios.

El instalador no elimina la carpeta de datos del usuario al desinstalar.

## 8. Interfaz de administración

Los widgets de la interfaz separan las distintas responsabilidades.

### ui/widgets/docs_table_tab.py

DocsTableTab representa la bandeja:

- Conserva la lista de documentos recibidos.
- Filtra por texto del nombre.
- Filtra por estado.
- Conserva la selección cuando se actualizan los datos si el registro sigue visible.
- Emite selection_changed para habilitar o deshabilitar las acciones de la ventana.

### ui/widgets/stats_table_tab.py

StatsTableTab calcula y muestra:

- Total recibido.
- Pendientes.
- Atendidos.

Los valores se derivan de la lista de documentos que recibe desde la ventana.

### ui/widgets/file_types_dialog.py

FileTypesDialog construye una casilla por extensión soportada y permite seleccionar o desmarcar todas. Devuelve el conjunto de extensiones activas; MainWindow lo persiste y actualiza Flask.

### ui/widgets/header_qr.py

HeaderQrWidget muestra el QR, el enlace y las acciones para copiarlo o abrirlo. La matriz se crea con la biblioteca qrcode y se convierte a QPixmap para mostrarla en Qt.

La ventana es responsable de decidir cuándo hay un enlace válido y qué texto de modo se presenta. El widget se ocupa de representarlo.

### services/qr_pdf.py

generate_qr_pdf() recibe la URL y una ruta de salida:

1. Valida que la URL tenga esquema HTTP o HTTPS y host.
2. Construye la matriz QR con corrección de errores alta.
3. Crea una página tamaño carta en PyMuPDF.
4. Dibuja cada módulo oscuro del QR como un rectángulo vectorial.
5. Añade el título, una indicación, la dirección y el pie.
6. Guarda primero un archivo temporal y después lo mueve a la ruta final.

El QR vectorial evita que los módulos pierdan nitidez por interpolación de una imagen de baja resolución.

## 9. Seguridad: qué protege y qué no

Es importante separar **control de acceso** de **cifrado de transporte**.

### Controles implementados

- La clave de acceso se compara usando secrets.compare_digest().
- La página principal requiere ?key=... cuando el token está configurado.
- La carga exige X-DocInBox-Key cuando el token está configurado.
- La respuesta HTML usa Cache-Control: no-store y Referrer-Policy: no-referrer.
- Se sanea el nombre del archivo.
- Se valida la extensión en el servidor.
- Se comprueba el tamaño real después de guardar el archivo temporalmente.
- Se utiliza un UUID para evitar sobrescrituras por nombres duplicados.

### Límites importantes

- El listener del escritorio usa 0.0.0.0; no queda restringido a una sola interfaz.
- La URL se anuncia con HTTP, no HTTPS. No hay TLS ni cifrado del contenido durante el transporte.
- El token es compartido. No identifica a la persona que envía un documento.
- El token forma parte de la URL del QR. Quien obtiene una copia del QR puede tener permiso para enviar archivos.
- El endpoint /api/health no requiere autenticación.
- La validación por extensión no demuestra que el contenido corresponda realmente al tipo declarado y no sustituye un antivirus.
- No existe una cuenta de usuario ni una autorización por remitente.

Por estas razones, el uso previsto es una red local privada y de confianza, con el puerto permitido solo en el perfil privado del firewall. No se debe configurar port forwarding hacia Internet.

### Por qué 0.0.0.0 importa

0.0.0.0 significa que el proceso acepta conexiones dirigidas a cualquiera de sus interfaces IPv4. No significa por sí mismo que Internet pueda acceder al equipo: eso depende del router, la red y el firewall. Sin embargo, el listener tampoco garantiza por sí solo que el tráfico provenga de una red local. La política del firewall y del router es parte de la frontera de seguridad.

## 10. API y respuestas

### GET /

- Recibe la clave como parámetro key.
- Devuelve 403 si la clave configurada no coincide.
- Renderiza templates/index.html con el máximo de carga y la lista de extensiones.

### GET /api/health

Devuelve un estado JSON simple:

~~~json
{
  "status": "ok",
  "service": "DocInBox Receiver"
}
~~~

No consulta si la base de datos está íntegra ni si existe espacio disponible; solo confirma que Flask responde.

### POST /api/upload

Recibe multipart/form-data con el campo file. Cuando existe una clave, también requiere X-DocInBox-Key.

| Estado | Causa principal |
|---|---|
| 201 | Documento almacenado y registrado. |
| 400 | Falta el archivo, está vacío o el nombre no es válido. |
| 403 | Clave ausente o incorrecta. |
| 413 | Se superó el límite de tamaño. |
| 415 | Extensión no permitida. |
| 500 | Error de almacenamiento o registro. |

## 11. Compilación y distribución

PyInstaller y Inno Setup cumplen funciones distintas:

1. **PyInstaller** analiza el punto de entrada y crea una carpeta ejecutable con Python, los módulos importados, bibliotecas nativas, Qt y recursos seleccionados.
2. **Inno Setup** toma esa carpeta y la instala en Program Files; crea los accesos directos y el desinstalador.

### DocInBox.spec

El archivo de especificación:

- Parte de app.py.
- Requiere Windows y Python de 64 bits.
- Incluye las carpetas templates, el archivo ui/styles.css y assets/icon.ico.
- Añade imports que se cargan de forma indirecta para qrcode y PyMuPDF.
- Excluye interfaces Qt alternativas y paquetes usados para desarrollo, notebooks y plotting.
- Genera una carpeta dist/DocInBox en modo onedir.
- No empaqueta la carpeta tests ni la documentación como recursos de ejecución.

Las DLL, plugins de Qt y dependencias nativas se detectan mediante el análisis de PyInstaller. No se deben borrar manualmente archivos de dist/DocInBox sin volver a probar el ejecutable.

### DocInBox.iss

El script de Inno Setup:

- Copia el contenido de dist/DocInBox a {autopf}/DocInBox.
- Crea un acceso del menú Inicio.
- Ofrece una tarea opcional para crear acceso en el escritorio.
- Solicita elevación para instalar.
- Ejecuta la aplicación posterior a la instalación como el usuario original.
- No elimina %LOCALAPPDATA%/DocInBox durante la desinstalación.

### Flujo de compilación

~~~powershell
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install --upgrade pip
.\.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm DocInBox.spec
ISCC.exe DocInBox.iss
~~~

Los resultados esperados son:

- Ejecutable: dist/DocInBox/DocInBox.exe.
- Instalador: Output/DocInBox_Setup_1.0.0.exe.

El comando normal evita --clean para conservar la caché de PyInstaller. Usa --clean cuando cambie el entorno de compilación o se necesite descartar el análisis y los artefactos anteriores.

## 12. Pruebas automatizadas

Ejecutar desde la raíz:

~~~powershell
python -m unittest discover -s tests -v
~~~

Los archivos de prueba se organizan por responsabilidad:

| Archivo | Qué valida |
|---|---|
| test_receiver.py | Rutas Flask, respuestas HTTP, autenticación, subida y límites. |
| test_document_store.py | Inserción, consultas, estados y eliminación en SQLite. |
| test_localhostrun_tunnel.py | Detección de IPv4, fallback y construcción de la URL LAN. El nombre es histórico. |
| test_qr_pdf.py | PDF de una página, QR vectorial y validación de URL/ruta. |
| test_packaging_paths.py | Resolución de recursos en desarrollo y en PyInstaller. |

Las pruebas unitarias no sustituyen una validación manual de red. Para comprobar la instalación real hay que probar el receptor en un equipo Windows, permitir el puerto en el perfil privado del firewall y abrir la URL desde otro dispositivo de la misma red.

## 13. Ruta recomendada de estudio

Para entender el proyecto sin saltar entre módulos, conviene leerlos en este orden:

1. app.py: identifica los modos de entrada.
2. config.py: entiende los valores y las rutas de datos.
3. app_flask.py: sigue la creación de Flask y sus endpoints.
4. services/file_policy.py: estudia cómo se normalizan y verifican las extensiones.
5. services/document_store.py: estudia el modelo de datos y las operaciones SQL.
6. services/lan_server.py: observa cómo se inicia y detiene el listener.
7. services/localhostrun_tunnel.py: sigue la detección de la IP local y la construcción del enlace.
8. templates/index.html y templates/app.js: revisa el formulario del remitente y la subida por fetch.
9. services/file_watcher.py: entiende cómo la ventana detecta cambios en la bandeja.
10. ui/wmain.py y ui/widgets/: estudia cómo se conectan las señales, datos y acciones.
11. services/qr_pdf.py: revisa la generación del QR vectorial.
12. DocInBox.spec y DocInBox.iss: estudia cómo se convierte el proyecto en un producto instalable.

### Ejercicios para profundizar

- Sigue una carga con un breakpoint desde upload_file() hasta DocumentStore.add_document().
- Inspecciona el archivo SQLite y relaciona cada fila con su archivo físico.
- Cambia una extensión permitida y observa cómo cambia accept en el HTML y cómo responde Flask al enviar otra extensión.
- Detén el servidor durante una carga y observa el resultado devuelto al navegador.
- Cambia el puerto mediante DOCINBOX_PORT y comprueba qué enlace produce el detector LAN.
- Simula una falla de ruta en detect_lan_ipv4() y observa por qué el fallback a 127.0.0.1 no es accesible desde otros equipos.
- Ejecuta la aplicación congelada desde dist/DocInBox y verifica que encuentra plantillas, estilos e iconos.

## 14. Límites conocidos de la implementación actual

- La dirección detectada puede cambiar por DHCP o por cambios de interfaz; no se configura una reserva estática automáticamente.
- El acceso está orientado a la red local; no hay un servicio relay, un dominio público ni una configuración automática de acceso por Internet.
- El transporte HTTP no cifra el token ni los documentos.
- No existe identidad independiente por remitente, antivirus integrado ni inspección profunda del contenido.
- Algunos nombres de clase y módulos todavía conservan términos heredados de una versión previa con proveedor de túnel. En el flujo descrito aquí no se ejecuta un túnel remoto.

Estos límites deben tenerse en cuenta antes de adaptar DocInBox a una red compartida, a una instalación multiusuario o a un entorno expuesto a Internet.
