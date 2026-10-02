# Tyrano Cheat Engine
![downloads](https://img.shields.io/github/downloads/J-Aca/Tyrano-Cheat-Engine/total?logo=github&label=Downloads&color=brightgreen)


Herramienta de inspección y edición de variables para juegos creados con **TyranoBuilder** y **TyranoScript**.

La aplicación permite iniciar un juego compatible, conectarse a él mediante el **Chrome DevTools Protocol (CDP)** y consultar o modificar variables internas de Tyrano desde una interfaz gráfica.


## Características

- Interfaz gráfica basada en Qt y PySide6.
- Conexión con juegos Tyrano mediante WebSocket/CDP.
- Inicio y detención del juego desde la aplicación.
- Búsqueda de variables por nombre.
- Búsqueda por valor exacto.
- Visualización periódica de los valores en tiempo real.
- Edición de valores de variables.
- Compatibilidad con variables de Tyrano como:
  - `stat.f`
  - `variable.tf`
  - `variable.sf`
  - Variables bajo `TYRANO.kag`
- Registro de actividad exportable a un archivo de texto.
- Temas claro y oscuro.
- Interfaz en español e inglés.
- Configuración persistente mediante `config.ini`.

## Requisitos

- Python 3.10 o superior.
- Windows.
- Un juego creado con TyranoBuilder/TyranoScript.
- Un juego compatible con la conexión mediante Chrome DevTools Protocol.
- Puerto CDP disponible, por defecto `9222`.

## Instalación

Clona el repositorio:

```bash
git clone https://github.com/J-Aca/Tyrano-Cheat-Engine.git
cd Tyrano-Cheat-Engine
```

Instala las dependencias:

```bash
python -m pip install PySide6 aiohttp
```

También puedes instalar las dependencias desde el archivo incluido:

```bash
python -m pip install -r requirements.txt
```

## Ejecución

Inicia la aplicación con:

```bash
python main.py
```

Desde la interfaz:

1. Abre el menú para iniciar un juego.
2. Selecciona el ejecutable del juego.
3. Espera a que se establezca la conexión.
4. Busca una variable por nombre o por valor.
5. Añade los resultados a la tabla de valores.
6. Modifica el valor desde la tabla cuando sea necesario.

## Configuración

La configuración se encuentra en `config.ini`:

```ini
[websocket]
port = 9222

[app]
theme = "default-dark"
language = "es"
```

### Opciones disponibles

- `websocket.port`: puerto utilizado para la comunicación CDP.
- `app.theme`: tema visual de la aplicación.
- `app.language`: idioma de la interfaz.

Idiomas disponibles:

- `es`
- `en`

Temas incluidos:

- `default-dark`
- `default-light`

## Búsqueda de variables

La aplicación permite buscar variables de dos formas:

### Por nombre

Busca coincidencias dentro de las variables disponibles. Por ejemplo:

```text
gold
```

Esto puede encontrar variables como:

```text
stat.f.gold
variable.tf.gold
```

### Por valor exacto

Busca variables cuyo valor coincida exactamente con el valor introducido.

Ejemplos:

```text
100
true
false
"texto"
```

También se reconocen valores numéricos, booleanos, `null`, `none` y estructuras JSON válidas.

> Actualmente el escaneo exacto es el modo principal disponible. Otros tipos de escaneo y modos de rescaneo pueden estar en desarrollo.

## Estructura del proyecto

```text
Tyrano-Cheat-Engine/
├── core/
│   ├── cdphandler.py
│   ├── config.py
│   ├── process.py
│   ├── tablemanager.py
│   └── thread.py
├── theme/
│   ├── default-dark/
│   └── default-light/
├── ui/
│   └── ui.py
├── config.ini
├── main.py
├── requirements.txt
├── LICENSE
└── README.md
```

### Descripción de los componentes

- `main.py`: punto de entrada y lógica principal de la aplicación.
- `core/`: conexión CDP, gestión de procesos, configuración y tareas asíncronas.
- `ui/`: componentes de la interfaz gráfica.
- `theme/`: hojas de estilo de la aplicación.
- `config.ini`: configuración del puerto, tema e idioma.
- `requirements.txt`: dependencias necesarias para ejecutar el proyecto.

## Solución de problemas

### No se puede conectar con el juego

Comprueba lo siguiente:

- El juego se inició desde la aplicación.
- El ejecutable seleccionado es el correcto.
- El puerto configurado está disponible.
- El juego es compatible con CDP.
- Ningún firewall está bloqueando la conexión local.
- El valor de `port` coincide con el puerto utilizado por el juego.

### No aparecen variables

Verifica que:

- El juego ya terminó de cargar.
- La variable existe dentro del contexto de Tyrano.
- Estás utilizando el nombre de variable correcto.
- Has seleccionado el modo de búsqueda adecuado.
- La variable pertenece a alguno de los espacios inspeccionados por la aplicación.

### La interfaz aparece sin tema

Comprueba que exista la carpeta correspondiente dentro de `theme/`:

```text
theme/default-dark/
theme/default-light/
```

También puedes restaurar la configuración utilizando:

```ini
[app]
theme = "default-dark"
```

## Desarrollo

Para ejecutar el proyecto durante el desarrollo:

```bash
python main.py
```

Antes de enviar cambios, comprueba que:

- La aplicación se inicia correctamente.
- La conexión con un juego funciona.
- Las búsquedas no bloquean la interfaz.
- Los cambios de valores se reflejan correctamente.
- La configuración se guarda y se carga correctamente.
- Los temas y traducciones continúan funcionando.

## Limitaciones actuales

- Está orientado principalmente a Windows.
- Requiere un juego compatible con Chrome DevTools Protocol.
- El escaneo exacto es el modo soportado actualmente.
- Algunos tipos de escaneo pueden estar planificados, pero todavía no implementados.
- La compatibilidad puede variar entre juegos y versiones de TyranoBuilder/TyranoScript.
- No todos los juegos Tyrano exponen sus variables de la misma manera.


## Licencia

Este proyecto se distribuye bajo la licencia MIT. Consulta el archivo [`LICENSE`](LICENSE) para obtener más información.

## Autor

Modificado por [J-Aca](https://github.com/J-Aca).

## Enlaces

- [Repositorio](https://github.com/J-Aca/Tyrano-Cheat-Engine)
- [TyranoBuilder](https://tyranobuilder.com/)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)

El proyecto está basado en [Lucid Engine](https://github.com/Galactic647/Lucid-Engine). con pequeñas modificaciones 