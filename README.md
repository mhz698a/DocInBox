# DocInBox - Sistema de Recepción e Impresión de Documentos Locales

## 📌 Descripción del Proyecto
DocInBox es un sistema de red local (LAN) diseñado para la gestión, visualización e impresión de documentos recibidos desde dispositivos móviles u otras PCs de forma directa y sin configuraciones complejas en los clientes. Su propósito principal es obtener documentos o archivos de cualquier tipo para su uso o impresión de documentos.

### Flujo de Usuario:
1. El usuario cliente escanea un código QR (o las misma URL) generado por la aplicación que contiene la URL de la red local.
2. El cliente accede a una interfaz web móvil responsiva desde su celular y sube un documento.
3. El archivo llega a través de la red local a la PC que actúa como servidor principal.
4. Un operador revisa de forma nativa el documento en una interfaz de escritorio y decide enviarlo a imprimir o usarlo para lo que covenga.

---

## 🛠️ Stack Tecnológico y Arquitectura
El proyecto se compone de una arquitectura híbrida que integra un servidor web local y una aplicación de escritorio nativa en el mismo proceso de Python.

*   **Sistema Operativo Objetivo:** Microsoft Windows.
*   **Lenguaje de Programación:** Python 3.12.
*   **Backend Web (LAN):** Flask. Se ejecuta en un hilo secundario independiente para no bloquear el flujo del sistema.
*   **Interfaz de Administración (Desktop):** PyQt6. Controla el ciclo de vida del servidor y gestiona los archivos que llegan para impresiones u otro objetivo.
*   **Gestión de Estilos Desktop:** Hojas de estilo en cascada de Qt (QSS).

## Requerimentos:
- PyQt6
- Flask en un QThread y usando pyqtSignal
- PyMuPDF para visualizar pdfs
- PyQt6.QtPrintSupport