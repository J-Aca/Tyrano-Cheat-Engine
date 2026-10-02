from typing import Union

import configparser
import json
import os


CONFIG_FILE = "config.ini"

THEME_DIRECTORY = "theme"

DEFAULT_CONFIG = {
    "websocket": {
        "port": 9222,
    },
    "app": {
        "theme": "default-dark",
        "language": "en",
    },
}


def crear_configuracion() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()

    if os.path.exists(CONFIG_FILE):
        parser.read(
            CONFIG_FILE,
            encoding="utf-8",
        )

    for section, data in DEFAULT_CONFIG.items():
        if not parser.has_section(section):
            parser.add_section(section)

        for option, value in data.items():
            if not parser.has_option(
                section,
                option,
            ):
                parser.set(
                    section,
                    option,
                    json.dumps(value),
                )

    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        parser.write(file)

    return parser


def cargar_configuracion() -> dict:
    parser = crear_configuracion()

    data = {}

    for section in parser.sections():
        data[section] = {}

        for option, value in parser.items(section):
            try:
                data[section][option] = json.loads(
                    value
                )
            except json.JSONDecodeError:
                data[section][option] = value

    return data


def obtener_valor_configuracion(
    section: str,
    option: str,
) -> Union[str, int, float, bool]:
    parser = crear_configuracion()

    value = parser.get(
        section,
        option,
    )

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def guardar_valor_configuracion(section: str, option: str, value) -> None:
    parser = crear_configuracion()
    if not parser.has_section(section):
        parser.add_section(section)
    parser.set(section, option, json.dumps(value, ensure_ascii=False))
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        parser.write(file)
