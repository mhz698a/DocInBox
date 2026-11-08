# DocInBox

**DocInBox** es una aplicación de escritorio para recibir documentos desde teléfonos y computadoras conectados a una red local y administrarlos desde una bandeja centralizada.

Combina una interfaz de administración construida con **PyQt6**, un servidor HTTP **Flask**, almacenamiento de archivos en el equipo anfitrión y un catálogo **SQLite**. El receptor web permite seleccionar o arrastrar varios archivos desde un navegador; la aplicación de escritorio registra las llegadas y permite buscarlas, clasificarlas, abrirlas, copiarlas o eliminarlas.

> **Alcance de red actual:** la versión de esta rama utiliza una dirección IPv4 local y HTTP. No inicia un túnel externo ni publica el receptor en Internet. Los dispositivos que envían documentos deben poder alcanzar el equipo anfitrión por la red local.

## Funcionalidades

### Recepción desde el navegador

- Página adaptable para teléfonos, tabletas y computadoras.
- Selección múltiple de archivos y soporte para arrastrar y soltar.
- Envío individual de los archivos seleccionados y presentación del resultado de cada envío.
- Validación de la clave de acceso, la extensión, el nombre y el tamaño de cada archivo.
- Nombres internos únicos para que dos archivos con el mismo nombre no se sobrescriban.
- Registro de cada llegada en SQLite y almacenamiento fuera de la carpeta de instalación.

### Administración desde el escritorio

- Inicio automático del receptor al abrir la aplicación.
- Tabla de documentos con búsqueda por nombre y filtro por estado.
- Contadores de documentos recibidos, pendientes y atendidos.
- Acciones para abrir el archivo, mostrar su ubicación, copiar su ruta, cambiar su estado y eliminarlo.
- Configuración persistente de las extensiones permitidas.
- Limpieza inicial opcional de los documentos de sesiones anteriores.
- Generación de un PDF imprimible con el código QR de acceso activo.

### Código QR y acceso local

- Detecta la IPv4 que el sistema operativo selecciona para la salida de red.
- Construye una URL HTTP con esa dirección y el puerto del receptor.
- Genera una clave de acceso persistente en la configuración del usuario.
- El botón **Imprimir Código QR** permite guardar el QR como PDF tamaño carta y abrirlo después de generarlo.
- La dirección IP puede cambiar si cambia la configuración de la red. Para usar un QR impreso durante más tiempo, conviene reservar una IP para el equipo en el router mediante DHCP.

### Extensiones permitidas de forma predeterminada

doc, docx, xlsx, xls, ppt, pptx, pdf, png, jpg, jpeg, gif, txt, mp3, wav, flac, m4a, mp4, mkv, avi.

La lista puede modificarse desde **Permitir tipo de archivos**. La configuración se guarda mediante QSettings y se aplica al servidor sin reiniciarlo.

## Requisitos

### Para ejecutar desde el código fuente

- Windows 10/11 (la interfaz y los scripts de instalación están orientados a Windows).
- Python de 64 bits, preferentemente Python 3.12.
- Las dependencias de requirements.txt.

Instalación de dependencias:

~~~powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -r requirements.txt
~~~

### Para compilar el instalador

Además de los requisitos anteriores:

- Windows x64.
- Python x64.
- PyInstaller, instalado mediante requirements-build.txt.
- Inno Setup 6 con ISCC.exe.

## Uso

### 1. Iniciar el receptor

Desde la carpeta raíz del proyecto:

~~~powershell
python app.py
~~~

La aplicación abre la ventana de administración, inicia Flask y detecta la dirección IPv4 local. Cuando termina la detección, muestra el enlace y el código QR.

### 2. Conectar un dispositivo

1. Conecta el teléfono o la computadora a la misma red local que el equipo que ejecuta DocInBox.
2. Escanea el código QR o abre el enlace mostrado en la ventana.
3. Selecciona o arrastra los documentos que deseas enviar.
4. Pulsa **Enviar documentos** y revisa el resultado de cada archivo.
5. Las llegadas aparecen en la tabla de DocInBox.

La red Wi-Fi, VLAN o las reglas del firewall deben permitir que el dispositivo alcance la dirección IPv4 del equipo anfitrión y el puerto configurado. La dirección 127.0.0.1 solo sirve dentro del propio equipo; si aparece en el QR, la detección de la IP LAN no encontró una interfaz utilizable.

### 3. Administrar documentos

Selecciona una fila de la tabla para habilitar las acciones inferiores:

- **Abrir documento:** abre el archivo con la aplicación predeterminada de Windows.
- **Mostrar ubicación:** abre el Explorador y selecciona el archivo.
- **Copiar ruta:** copia la ruta absoluta.
- **Marcar como atendido / Marcar como pendiente:** cambia el estado guardado en SQLite.
- **Eliminar:** pide confirmación y elimina permanentemente el archivo y su registro.

El filtro permite mostrar todos los documentos, solo los pendientes o solo los atendidos. El buscador filtra por nombre.

### 4. Configurar extensiones

Pulsa **Permitir tipo de archivos**, marca las extensiones que se aceptarán y guarda los cambios. La validación se aplica tanto al selector web como al endpoint Flask. Si una extensión no está habilitada, el servidor responde con HTTP 415.

### 5. Imprimir el código QR

1. Espera a que el receptor termine de iniciar y aparezca el enlace.
2. Pulsa **Imprimir Código QR**.
3. Elige la ruta y el nombre del archivo PDF.
4. Confirma si deseas abrir el PDF después de guardarlo.

El PDF contiene un QR vectorial y la URL completa, incluida la clave de acceso. El QR impreso solo seguirá funcionando mientras la dirección IPv4 del equipo siga siendo la misma y el receptor esté activo.

### 6. Detener el receptor

Pulsa **Detener receptor**. El servidor deja de aceptar conexiones. Cerrar la ventana también detiene los hilos que administra la aplicación.

### Modo web de desarrollo

Para ejecutar únicamente Flask en el equipo local, sin la ventana PyQt6:

~~~powershell
python app.py --web-only
~~~

Este modo utiliza 127.0.0.1 y el puerto configurado. Es útil para probar el formulario desde el mismo equipo, pero no anuncia una dirección LAN ni permite que otros dispositivos se conecten directamente.

## Red y seguridad

El modo de escritorio crea el servidor Werkzeug con 0.0.0.0, es decir, escucha en todas las interfaces IPv4 disponibles. La URL del QR usa la IPv4 LAN detectada por el sistema. La accesibilidad real depende de la red, de las VLAN, de las reglas del firewall y del enrutamiento del entorno.

**La comunicación actual usa HTTP sin TLS.** Esto significa que el contenido de los archivos y la clave de acceso no están cifrados durante el tránsito por la red local. Utiliza DocInBox únicamente en una red privada y de confianza. Evita redes Wi-Fi públicas o compartidas, y no configures un reenvío de puertos del router que exponga el puerto del receptor a Internet.

La clave de acceso funciona como un secreto compartido:

- Se genera cuando no existe una clave guardada y se conserva mediante QSettings.
- Se incluye en el enlace del QR como parámetro key.
- La página web entrega la clave al JavaScript y las cargas la presentan en la cabecera X-DocInBox-Key.
- Cualquier persona que tenga el enlace o una copia del QR puede enviar archivos mientras el receptor esté activo.

No hay cuentas individuales ni identificación de cada remitente. El endpoint GET /api/health es público y no requiere esa clave. La validación de tipos se basa en la extensión del nombre; no es un análisis antivirus ni una inspección completa del contenido del archivo.

Para permitir el tráfico en Windows, configura el Firewall de Windows para aceptar el puerto TCP utilizado por DocInBox en el perfil **Privado**, según las políticas de tu red. No abras el acceso para redes públicas sin una evaluación de seguridad.

## Datos y configuración

Por defecto, en Windows los documentos y la base de datos se guardan fuera de Program Files:

| Dato | Ubicación predeterminada |
|---|---|
| Archivos recibidos | %LOCALAPPDATA%/DocInBox/Received |
| Base de datos | %LOCALAPPDATA%/DocInBox/inbox.sqlite3 |
| Preferencias y clave de acceso | Almacenamiento de configuración del usuario mediante QSettings |

Los datos del usuario no forman parte de la carpeta de instalación. El desinstalador elimina el programa instalado, no la bandeja del usuario.

### Variables de entorno

| Variable | Valor predeterminado | Descripción |
|---|---|---|
| DOCINBOX_PORT | 8765 | Puerto TCP del receptor. |
| DOCINBOX_MAX_UPLOAD_MB | 100 | Tamaño máximo permitido por archivo, en MiB. |
| DOCINBOX_DATA_DIR | %LOCALAPPDATA%/DocInBox | Directorio base de los datos del usuario. |
| DOCINBOX_STORAGE_DIR | DATA_DIR/Received | Carpeta donde se guardan los archivos recibidos. |
| DOCINBOX_DATABASE_PATH | DATA_DIR/inbox.sqlite3 | Archivo de base de datos SQLite. |

Las variables se deben definir antes de iniciar el proceso. DOCINBOX_STORAGE_DIR y DOCINBOX_DATABASE_PATH permiten separar la carpeta de archivos y la base de datos del directorio base.

## API del receptor

### Estado del servicio

~~~http
GET /api/health
~~~

Respuesta:

~~~json
{
  "status": "ok",
  "service": "DocInBox Receiver"
}
~~~

### Enviar un archivo

~~~http
POST /api/upload
~~~

El cuerpo debe ser multipart/form-data con un campo llamado file. Cuando la clave de acceso está configurada, también se requiere:

~~~http
X-DocInBox-Key: <clave-del-QR>
~~~

Códigos de respuesta principales:

| Código | Significado |
|---|---|
| 201 | Archivo guardado y registrado. |
| 400 | Falta el archivo, está vacío o su nombre no es válido. |
| 403 | Clave de acceso ausente o incorrecta. |
| 413 | Archivo mayor que el límite configurado. |
| 415 | Extensión no permitida. |
| 500 | Falló el almacenamiento o el registro del documento. |

## Pruebas

Desde la raíz del repositorio:

~~~powershell
python -m unittest discover -s tests -v
~~~

Las pruebas cubren la recepción Flask, la persistencia SQLite, la validación de extensiones, la detección de la IPv4 LAN, la generación del PDF QR y la resolución de recursos en modo PyInstaller.

## Compilación de Windows x64

El proyecto incluye DocInBox.spec para PyInstaller y DocInBox.iss para Inno Setup. La instalación resultante se coloca en **Program Files**.

### 1. Crear el entorno de compilación

En PowerShell, desde la raíz del proyecto:

~~~powershell
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install --upgrade pip
.\.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
~~~

requirements-build.txt instala las dependencias de ejecución y añade la versión fijada de PyInstaller. PyInstaller no se incorpora a las dependencias necesarias para ejecutar DocInBox desde Python.

### 2. Generar el paquete con PyInstaller

~~~powershell
.\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm DocInBox.spec
~~~

El ejecutable queda en:

    dist/DocInBox/DocInBox.exe

El modo onedir conserva el ejecutable y las bibliotecas necesarias en una carpeta de distribución. El archivo de especificación incluye únicamente los recursos de ejecución que no se descubren automáticamente: plantillas web, hoja de estilos de PyQt6 e icono. PyInstaller analiza las importaciones y reúne las dependencias detectadas. También excluye bindings Qt alternativos y paquetes de desarrollo que el programa no utiliza.

Para una recompilación completa desde cero, se puede añadir --clean al comando. No se utiliza en la compilación normal para conservar la caché de análisis y acelerar las siguientes compilaciones.

### 3. Probar el ejecutable

Antes de crear el instalador, ejecuta:

~~~powershell
.\dist\DocInBox\DocInBox.exe
~~~

Comprueba el inicio de la ventana, la detección de la dirección LAN, la recepción desde otro dispositivo, las acciones de la bandeja y la generación del PDF.

### 4. Crear el instalador

Con Inno Setup 6 instalado y ISCC.exe disponible:

~~~powershell
ISCC.exe DocInBox.iss
~~~

El instalador se genera en:

    Output/DocInBox_Setup_1.0.0.exe

El script de Inno Setup:

- Instala el contenido de dist/DocInBox en Program Files/DocInBox.
- Crea un acceso directo en el menú Inicio.
- Ofrece un acceso directo opcional en el escritorio.
- Solicita privilegios de administrador para instalar.
- Inicia la aplicación con las credenciales del usuario que ejecutó el instalador.
- Conserva los datos de %LOCALAPPDATA%/DocInBox al desinstalar.

Para cambiar la versión, actualiza AppVersion y VersionInfoVersion en DocInBox.iss.

## Estructura del proyecto

~~~text
DocInBox/
├── app.py
├── app_flask.py
├── config.py
├── DocInBox.spec
├── DocInBox.iss
├── requirements.txt
├── requirements-build.txt
├── assets/
├── docs/
├── services/
├── templates/
├── tests/
└── ui/
~~~

La guía de estudio de la arquitectura y del flujo interno está en [docs/COMO_FUNCIONA.md](docs/COMO_FUNCIONA.md).
