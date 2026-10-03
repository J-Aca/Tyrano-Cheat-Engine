# Tyrano Cheat Engine

![Descargas](https://img.shields.io/github/downloads/J-Aca/Tyrano-Cheat-Engine/total?logo=github&label=Descargas&color=brightgreen)

Aplicación de escritorio para inspeccionar y editar variables de juegos creados con **TyranoBuilder** y **TyranoScript**. Se conecta al runtime del juego mediante **Chrome DevTools Protocol (CDP)** y ofrece una interfaz gráfica Qt/PySide6.

> La compatibilidad depende de que el juego exponga un endpoint CDP accesible. Haz copias de seguridad de tus partidas antes de modificar variables.

## Funciones

### Lanzamiento y conexión
- Inicia un ejecutable de juego seleccionado desde la aplicación y permite detenerlo.
- Detecta/espera el puerto CDP configurado y conecta al WebSocket del runtime.
- Consulta y modifica propiedades del contexto Tyrano a través de CDP.
- Muestra el estado de conexión y registra eventos y errores.

### Búsqueda y escaneo
- Busca variables por **nombre** o explora valores con un escaneo de valores.
- Tipos de escaneo disponibles en la interfaz:
  - Valor exacto, mayor que, menor que y rango (entre dos valores).
  - Desconocido, aumentado, aumentado en, reducido, reducido en.
  - Cambiado, sin cambios e ignorar.
  - Contiene, empieza con, termina con y expresión regular.
- Los escaneos de valor pueden refinar candidatos con el estado previo; las opciones relativas comparan valores numéricos entre escaneos.
- Convierte entradas reconocibles a booleanos, `null`, enteros, decimales y JSON; lo demás se trata como texto.
- Puede omitir valores nulos/vacíos según la configuración y aplica un tiempo límite configurable al escaneo.
- Presenta resultados con valor actual, valor anterior y ruta; incluye progreso, recuento y limpieza de resultados.

### Lista de variables, edición y congelación
- Añade resultados a la lista de seguimiento; permite editar el valor mediante diálogo y operar con selecciones/contextos.
- Mantiene una lectura periódica para refrescar los valores mientras hay conexión.
- Permite marcar variables para intentar mantener su valor (reaplicación periódica mientras el juego está conectado).
- La lista admite selección múltiple, reordenamiento y operaciones contextuales.

### Importación y exportación
- Importa listas desde JSON o TXT. Acepta rutas en líneas de texto y estructuras JSON de lista/objeto; las filas pueden marcarse para incorporarlas a la lista de variables.
- Exporta rutas como TXT o elementos como JSON con nombre, ruta y valor; combina entradas importadas, variables seguidas y resultados, evitando rutas duplicadas.
- Permite vaciar la lista importada.

### Interfaz, ajustes y registros
- Interfaz bilingüe: español e inglés.
- Temas claro y oscuro incluidos, carga de tema personalizado y personalización de colores.
- Configuración persistente en `config.ini`: puerto, tema, idioma, opciones de escaneo y ruta de registro.
- Registro visible en la aplicación y guardado/exportación a archivo de texto.
- Menús de tutorial/ayuda y acerca de.

## Requisitos

- Python 3.10 o superior (recomendado).
- Windows es el entorno objetivo principal; la compatibilidad en otros sistemas no está garantizada.
- Juego TyranoBuilder/TyranoScript compatible con CDP y puerto local disponible (por defecto `9222`).
- Dependencias: PySide6 y aiohttp.

## Instalación y ejecución

```bash
git clone https://github.com/J-Aca/Tyrano-Cheat-Engine.git
cd Tyrano-Cheat-Engine
python -m pip install PySide6 aiohttp
python main.py
```

El `requirements.txt` incluido contiene comandos de instalación/ejecución para referencia, no el formato habitual de lista de paquetes; por eso se recomienda instalar las dependencias con el comando anterior.

## Uso rápido

1. Abre **Archivo → Iniciar juego** y selecciona el ejecutable.
2. Espera a que la aplicación conecte con el juego.
3. En **Escaneo**, elige búsqueda por nombre o por valor y configura el tipo de escaneo.
4. Añade los resultados que quieras seguir a la lista de valores.
5. Edita el valor desde la lista; marca la casilla correspondiente si quieres intentar congelarlo.
6. Usa **Importar lista**/**Exportar lista** para reutilizar rutas y **Guardar registros** para guardar el log.

Para búsquedas relativas (por ejemplo, aumentado/reducido/cambiado), realiza primero un escaneo base y luego vuelve a escanear tras cambiar el estado del juego. La expresión regular se interpreta como regex de Python.

## Configuración

Ejemplo de `config.ini`:

```ini
[websocket]
port = 9222

[app]
theme = "default-dark"
language = "es"

[scan]
timeout = 30
root = "f"
ignore_null = true
ignore_readonly = false
log_path = null
```

- `websocket.port`: puerto del endpoint CDP.
- `app.theme`: tema activo (`default-dark`, `default-light` o tema personalizado cargado desde la interfaz).
- `app.language`: `es` o `en`.
- `scan.timeout`: límite de espera del escaneo, en segundos.
- `scan.root`: raíz de variables a inspeccionar (`tf`, `f`, `sf` o `all`, según la interfaz).
- `scan.ignore_null`: omite valores nulos/vacíos del escaneo.
- `scan.ignore_readonly`: opción de configuración para variables de solo lectura.
- `scan.log_path`: ruta de registro persistente, si se configura.

## Estructura del proyecto

```text
Tyrano-Cheat-Engine/
├── core/                 # CDP, procesos, configuración, tablas y tareas asíncronas
├── resources/             # Icono de la aplicación
├── theme/                 # Temas claro/oscuro y colores
├── ui/                    # Ventanas, diálogos y widgets Qt
├── config.ini             # Ajustes predeterminados
├── main.py                # Arranque y coordinación de la aplicación
├── requirements.txt       # Comandos/dependencias de referencia
└── README.md
```

### Módulos principales

- `main.py`: lógica de escaneo, conexión, actualización de valores, congelación, importación/exportación, registros, ajustes y arranque.
- `core/cdphandler.py`: conexión CDP/WebSocket, evaluación de expresiones y lectura/escritura de propiedades Tyrano.
- `core/process.py`: inicio, estado y detención del proceso de juego.
- `core/config.py`: lectura y persistencia de configuración.
- `core/thread.py`, `core/worker.py`: ejecución asíncrona y trabajos en segundo plano para mantener la interfaz receptiva.
- `core/tablemanager.py`: serialización y carga/guardado de tablas.
- `core/themeloader.py`: carga de temas y conversión de colores.
- `ui/ui.py`: construcción y traducción de la interfaz; `ui/dialog.py` y `ui/widget.py`: diálogos y widgets auxiliares.

## Solución de problemas

- **No conecta:** confirma que el juego se inició desde la aplicación, que es compatible con CDP, que el puerto configurado coincide y está libre, y que el firewall permite la conexión local.
- **No aparecen variables:** espera a que cargue el juego, revisa la raíz de escaneo y la ruta/nombre; no todos los títulos exponen las variables de la misma forma.
- **El escaneo se demora o vence:** reduce el alcance de la búsqueda o ajusta `scan.timeout`.
- **Tema no disponible:** verifica que existan `theme/default-dark/` y `theme/default-light/` o vuelve a seleccionar un tema integrado.

## Limitaciones

- Es una herramienta de inspección/modificación en memoria; no sustituye un editor de partidas guardadas.
- Requiere un runtime compatible con CDP; no se garantiza para todos los juegos o versiones de Tyrano.
- La congelación depende de que la ruta siga siendo válida y el juego acepte la escritura.
- La configuración `ignore_readonly` existe, pero su efecto puede depender del contexto/runtime del juego.
- Windows es el sistema objetivo y no se declara compatibilidad multiplataforma completa.

## Licencia y créditos

El README original indica licencia MIT; consulta el archivo `LICENSE` de la distribución para los términos completos. El proyecto se atribuye a [J-Aca](https://github.com/J-Aca) y se basa en [Lucid Engine](https://github.com/Galactic647/Lucid-Engine), con modificaciones.

## Enlaces

- [Repositorio](https://github.com/J-Aca/Tyrano-Cheat-Engine)
- [TyranoBuilder](https://tyranobuilder.com/)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
