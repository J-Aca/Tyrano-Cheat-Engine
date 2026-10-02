import hashlib
import json
import os
import struct


MAGIC = b"TBR-CTLBF"
VERSION = b"0.0.1"


def codificar_varint(
    value: int,
    signed: bool = False,
) -> bytes:
    if signed:
        value = (
            (value << 1)
            ^ (value >> 31)
        )

    if value < 0:
        raise ValueError(
            "Varint cannot encode a negative unsigned value."
        )

    result = bytearray()

    while True:
        current = value & 0x7F
        value >>= 7

        if value:
            result.append(
                current | 0x80
            )
        else:
            result.append(
                current
            )
            break

    return bytes(result)


def decodificar_varint(
    data,
    signed: bool = False,
) -> int:
    value = 0

    for shift, byte in enumerate(data):
        value |= (
            (byte & 0x7F)
            << (shift * 7)
        )

        if not byte & 0x80:
            break

    if signed:
        return (
            value >> 1
        ) ^ -(
            value & 1
        )

    return value


def leer_varint(
    file,
    signed: bool = False,
) -> int:
    value = 0
    shift = 0

    while True:
        raw = file.read(1)

        if not raw:
            raise EOFError(
                "Unexpected end of table file."
            )

        byte = raw[0]

        value |= (
            (byte & 0x7F)
            << shift
        )

        if not byte & 0x80:
            break

        shift += 7

        if shift > 63:
            raise ValueError(
                "Invalid varint in table file."
            )

    if signed:
        return (
            value >> 1
        ) ^ -(
            value & 1
        )

    return value


def _save_table(file, item):
    is_header = (
        not item.get("path")
        and not item.get("value")
    )

    file.write(
        bytes([1 if is_header else 0])
    )

    name = str(
        item.get(
            "name",
            "",
        )
    )

    name_data = name.encode(
        "utf-8"
    )

    file.write(
        codificar_varint(
            len(name_data)
        )
    )
    file.write(
        name_data
    )

    if not is_header:
        path = str(
            item.get(
                "path",
                "",
            )
        )

        parts = path.split(".")

        if len(parts) < 2:
            raise ValueError(
                f"Invalid variable path: {path}"
            )

        path_type = parts[1]
        variable_path = ".".join(
            parts[2:]
        )

        path_types = {
            "f": 0,
            "tf": 1,
            "sf": 2,
        }

        if path_type not in path_types:
            raise ValueError(
                f"Unknown path type: {path_type}"
            )

        file.write(
            bytes([
                path_types[path_type]
            ])
        )

        path_data = variable_path.encode(
            "utf-8"
        )

        file.write(
            codificar_varint(
                len(path_data)
            )
        )
        file.write(
            path_data
        )

        value = item.get(
            "value"
        )

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass

        if value is None:
            dtype = 0
        elif isinstance(value, bool):
            dtype = 4
        elif isinstance(value, int):
            dtype = 2
        elif isinstance(value, float):
            dtype = 3
        elif isinstance(value, str):
            dtype = 1
        else:
            raise TypeError(
                f"Unknown type {type(value)}"
            )

        file.write(
            bytes([dtype])
        )

        if dtype == 1:
            value_data = value.encode(
                "utf-8"
            )

            file.write(
                codificar_varint(
                    len(value_data)
                )
            )
            file.write(
                value_data
            )

        elif dtype == 2:
            file.write(
                codificar_varint(
                    value,
                    signed=True,
                )
            )

        elif dtype == 3:
            file.write(
                struct.pack(
                    ">f",
                    value,
                )
            )

        elif dtype == 4:
            file.write(
                bytes([
                    int(value)
                ])
            )

    color = item.get(
        "color",
        (255, 255, 255),
    )

    color = tuple(
        int(channel) & 0xFF
        for channel in color[:3]
    )

    if len(color) != 3:
        color = (
            255,
            255,
            255,
        )

    file.write(
        struct.pack(
            ">BBB",
            *color,
        )
    )

    children = item.get(
        "children",
        [],
    )

    has_children = bool(children)

    file.write(
        bytes([
            1 if has_children else 0
        ])
    )

    if has_children:
        file.write(
            codificar_varint(
                len(children)
            )
        )

        for child in children:
            _save_table(
                file,
                child,
            )


def guardar_tabla(
    file_path,
    table,
):
    serialized = json.dumps(
        table,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    with open(
        file_path,
        "wb",
    ) as file:
        file.write(MAGIC)
        file.write(VERSION)

        file.write(
            hashlib.sha256(
                serialized
            ).digest()
        )

        file.write(
            codificar_varint(
                len(table)
            )
        )

        for item in table:
            _save_table(
                file,
                item,
            )


def _load_table(file):
    data = {}

    header_raw = file.read(1)

    if not header_raw:
        raise EOFError(
            "Unexpected end of table file."
        )

    is_header = bool(
        header_raw[0]
    )

    name_length = leer_varint(
        file
    )

    data["name"] = file.read(
        name_length
    ).decode("utf-8")

    if not is_header:
        path_type_raw = file.read(1)

        if not path_type_raw:
            raise EOFError(
                "Unexpected end of table file."
            )

        path_type = path_type_raw[0]

        path_length = leer_varint(
            file
        )

        path = file.read(
            path_length
        ).decode("utf-8")

        prefixes = {
            0: "stat.f.",
            1: "variable.tf.",
            2: "variable.sf.",
        }

        if path_type not in prefixes:
            raise ValueError(
                f"Unknown path type: {path_type}"
            )

        data["path"] = (
            prefixes[path_type]
            + path
        )

        dtype_raw = file.read(1)

        if not dtype_raw:
            raise EOFError(
                "Unexpected end of table file."
            )

        dtype = dtype_raw[0]

        if dtype == 0:
            data["value"] = None

        elif dtype == 1:
            length = leer_varint(
                file
            )

            data["value"] = file.read(
                length
            ).decode("utf-8")

        elif dtype == 2:
            data["value"] = leer_varint(
                file,
                signed=True,
            )

        elif dtype == 3:
            data["value"] = struct.unpack(
                ">f",
                file.read(4),
            )[0]

        elif dtype == 4:
            data["value"] = bool(
                int.from_bytes(
                    file.read(1),
                    byteorder="big",
                )
            )

        else:
            raise ValueError(
                f"Unknown data type: {dtype}"
            )

    else:
        data["path"] = ""
        data["value"] = ""

    color_data = file.read(3)

    if len(color_data) != 3:
        raise EOFError(
            "Unexpected end of table file."
        )

    data["color"] = struct.unpack(
        ">BBB",
        color_data,
    )

    children_raw = file.read(1)

    if not children_raw:
        raise EOFError(
            "Unexpected end of table file."
        )

    has_children = bool(
        children_raw[0]
    )

    if has_children:
        count = leer_varint(
            file
        )

        data["children"] = [
            _load_table(file)
            for _ in range(count)
        ]
    else:
        data["children"] = []

    return data


def cargar_tabla(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            file_path
        )

    with open(
        file_path,
        "rb",
    ) as file:
        if file.read(
            len(MAGIC)
        ) != MAGIC:
            raise ValueError(
                "Invalid table file."
            )

        version = file.read(
            len(VERSION)
        )

        if len(version) != len(VERSION):
            raise ValueError(
                "Invalid table file version."
            )

        expected_hash = file.read(32)

        if len(expected_hash) != 32:
            raise ValueError(
                "Invalid table file hash."
            )

        count = leer_varint(
            file
        )

        data = [
            _load_table(file)
            for _ in range(count)
        ]

        actual_hash = hashlib.sha256(
            json.dumps(
                data,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            ).encode("utf-8")
        ).digest()

        if expected_hash != actual_hash:
            raise ValueError(
                "Hash mismatch for save file."
            )

        return data
