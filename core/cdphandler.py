from typing import Optional
from pathlib import Path
from urllib.parse import (
    unquote,
    urlparse,
)

import asyncio
import aiohttp
import json
import math
import socket


SKIP_PROPERTIES = (
    "__proto__",
    "length",
)


async def check_port_async(
    port,
    timeout: Optional[float] = 0.5,
) -> bool:
    try:
        loop = asyncio.get_running_loop()

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        sock.setblocking(False)

        try:
            await asyncio.wait_for(
                loop.sock_connect(
                    sock,
                    (
                        "127.0.0.1",
                        int(port),
                    ),
                ),
                timeout=timeout,
            )
            return True
        finally:
            sock.close()

    except (
        OSError,
        ConnectionRefusedError,
        asyncio.TimeoutError,
    ):
        return False


def check_port(
    port,
    timeout: Optional[float] = 0.5,
) -> bool:
    return asyncio.run(
        check_port_async(
            port,
            timeout,
        )
    )


async def wait_for_port_async(
    port,
    timeout: Optional[float] = 5,
) -> bool:
    start = asyncio.get_running_loop().time()

    while True:
        if await check_port_async(port):
            return True

        await asyncio.sleep(0.1)

        if (
            timeout is not None
            and asyncio.get_running_loop().time() - start
            > timeout
        ):
            return False


def wait_for_port(
    port,
    timeout: Optional[float] = 5,
) -> bool:
    return asyncio.run(
        wait_for_port_async(
            port,
            timeout,
        )
    )


def _normalize_path(value):
    value = unquote(str(value))
    value = value.replace("\\", "/")
    return value.rstrip("/").lower()


def _target_matches_game(
    target_url: str,
    game_path: Path,
) -> bool:
    if not target_url:
        return False

    normalized_game = _normalize_path(
        game_path.parent
    )

    parsed = urlparse(target_url)

    candidates = [
        target_url,
        parsed.path,
    ]

    for candidate in candidates:
        candidate = _normalize_path(candidate)

        if normalized_game and normalized_game in candidate:
            return True

    return False


async def get_cdp_ws_url_async(
    port,
    path_url,
    wait: Optional[bool] = False,
) -> str:
    if wait:
        available = await wait_for_port_async(
            port
        )

        if not available:
            raise ConnectionRefusedError(
                f"CDP port {port} did not become available."
            )

    if isinstance(path_url, str):
        path_url = Path(path_url)

    endpoints = (
        f"http://127.0.0.1:{port}/json/list",
        f"http://127.0.0.1:{port}/json",
    )

    timeout = aiohttp.ClientTimeout(
        total=5
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:
        targets = None

        last_error = None

        for endpoint in endpoints:
            try:
                async with session.get(
                    endpoint
                ) as response:
                    response.raise_for_status()
                    targets = await response.json()
                    break
            except Exception as exc:
                last_error = exc

        if targets is None:
            raise ConnectionError(
                f"Unable to query CDP targets on port "
                f"{port}: {last_error}"
            )

        if isinstance(targets, dict):
            targets = [targets]

        page_targets = [
            target
            for target in targets
            if target.get("type") == "page"
            and target.get("webSocketDebuggerUrl")
        ]

        if not page_targets:
            page_targets = [
                target
                for target in targets
                if target.get(
                    "webSocketDebuggerUrl"
                )
            ]

        for target in page_targets:
            target_url = target.get(
                "url",
                "",
            )

            if _target_matches_game(
                target_url,
                path_url,
            ):
                return target[
                    "webSocketDebuggerUrl"
                ]

        if len(page_targets) == 1:
            return page_targets[0][
                "webSocketDebuggerUrl"
            ]

        return None


def get_cdp_ws_url(
    port,
    path_url,
    wait: Optional[bool] = False,
) -> str:
    return asyncio.run(
        get_cdp_ws_url_async(
            port,
            path_url,
            wait,
        )
    )


class RuntimeMethods:
    EVALUATE = "Runtime.evaluate"
    GET_PROPERTIES = "Runtime.getProperties"


class TyranoVars:
    F = "TYRANO.kag.stat.f"
    TF = "TYRANO.kag.variable.tf"
    SF = "TYRANO.kag.variable.sf"

    F_PART = "stat.f"
    TF_PART = "variable.tf"
    SF_PART = "variable.sf"


class CDPHandler:
    def __init__(
        self,
        websocket_url,
    ) -> None:
        self.websocket_url = websocket_url

        self.session = None
        self.websocket = None

        self.pending = {}

        self._msg_id = 0
        self._listener_task = None
        self._active = False
        self._connect_lock = asyncio.Lock()

    async def _get_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def connect(self) -> None:
        async with self._connect_lock:
            if (
                self.websocket is not None
                and not self.websocket.closed
            ):
                return

            await self._close_transport()

            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=None
                )
            )

            try:
                self.websocket = await self.session.ws_connect(
                    self.websocket_url,
                    autoping=True,
                    heartbeat=20,
                    receive_timeout=None,
                    max_msg_size=0,
                )
            except Exception:
                await self._close_transport()
                raise

            self._active = True

            self._listener_task = asyncio.create_task(
                self._listener()
            )

    async def _close_transport(self):
        if self._listener_task is not None:
            current = asyncio.current_task()

            if self._listener_task is not current:
                self._listener_task.cancel()

                try:
                    await self._listener_task
                except (
                    asyncio.CancelledError,
                    Exception,
                ):
                    pass

            self._listener_task = None

        if self.websocket is not None:
            try:
                await self.websocket.close()
            except Exception:
                pass

        self.websocket = None

        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass

        self.session = None

    async def close(self) -> None:
        self._active = False

        for future in list(
            self.pending.values()
        ):
            if not future.done():
                future.cancel()

        self.pending.clear()

        await self._close_transport()

    async def _listener(self):
        try:
            while self._active:
                if (
                    self.websocket is None
                    or self.websocket.closed
                ):
                    break

                message = await self.websocket.receive()

                if message.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(
                            message.data
                        )
                    except json.JSONDecodeError:
                        continue

                    message_id = data.get("id")

                    if message_id is not None:
                        future = self.pending.pop(
                            message_id,
                            None,
                        )

                        if (
                            future is not None
                            and not future.done()
                        ):
                            if "error" in data:
                                future.set_exception(
                                    RuntimeError(
                                        str(
                                            data[
                                                "error"
                                            ]
                                        )
                                    )
                                )
                            else:
                                future.set_result(
                                    data
                                )

                elif message.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            print(
                f"CDP listener error: {exc!r}"
            )

        finally:
            if self._active:
                for future in list(
                    self.pending.values()
                ):
                    if not future.done():
                        future.set_exception(
                            ConnectionError(
                                "CDP WebSocket disconnected."
                            )
                        )

                self.pending.clear()

    async def send(
        self,
        method,
        params=None,
    ):
        if params is None:
            params = {}

        if (
            self.websocket is None
            or self.websocket.closed
        ):
            await self.connect()

        message_id = await self._get_id()

        message = {
            "id": message_id,
            "method": method,
            "params": params,
        }

        future = asyncio.get_running_loop().create_future()

        self.pending[message_id] = future

        try:
            await self.websocket.send_json(
                message
            )

            return await future

        except Exception:
            self.pending.pop(
                message_id,
                None,
            )

            if not future.done():
                future.cancel()

            raise

    async def get_properties(
        self,
        object_id,
    ) -> list:
        result = await self.send(
            RuntimeMethods.GET_PROPERTIES,
            {
                "objectId": object_id,
                "ownProperties": True,
            },
        )

        return result[
            "result"
        ][
            "result"
        ]

    async def evaluate(
        self,
        expression,
        return_value: Optional[bool] = False,
    ):
        result = await self.send(
            RuntimeMethods.EVALUATE,
            {
                "expression": expression,
                "returnByValue": return_value,
            },
        )

        result = result[
            "result"
        ][
            "result"
        ]

        result_type = result.get(
            "type"
        )

        if result_type == "undefined":
            return "??"

        if (
            result_type == "object"
            and not return_value
        ):
            return result.get(
                "objectId"
            )

        if (
            result.get("subtype")
            == "null"
        ):
            return None

        if "value" in result:
            return result["value"]

        return "??"

    async def _get_value(
        self,
        key,
        value,
    ):
        result = {}

        value_type = value.get(
            "type"
        )

        if value_type == "object":
            object_id = value.get(
                "objectId"
            )

            if not object_id:
                result[key] = None
                return result

            properties = await self.get_properties(
                object_id
            )

            data = []
            data_dict = {}

            for prop in properties:
                prop_name = prop.get(
                    "name",
                    "",
                )
                prop_value = prop.get(
                    "value",
                    {},
                )

                if prop_name in SKIP_PROPERTIES:
                    continue

                prop_type = prop_value.get(
                    "type"
                )

                if (
                    prop_type
                    in (
                        "string",
                        "boolean",
                    )
                    or prop_value.get(
                        "subtype"
                    )
                    == "null"
                ):
                    value_data = prop_value.get(
                        "value"
                    )

                    if prop_name.isdigit():
                        data.append(
                            value_data
                        )
                    else:
                        data_dict[
                            prop_name
                        ] = value_data

                elif prop_type == "number":
                    if "value" in prop_value:
                        value_data = prop_value[
                            "value"
                        ]
                    else:
                        value_data = math.nan

                    if prop_name.isdigit():
                        data.append(
                            value_data
                        )
                    else:
                        data_dict[
                            prop_name
                        ] = value_data

                elif prop_type == "undefined":
                    if prop_name.isdigit():
                        data.append("??")
                    else:
                        data_dict[
                            prop_name
                        ] = "??"

                else:
                    nested = await self._get_value(
                        prop_name,
                        prop_value,
                    )

                    if isinstance(
                        nested,
                        list,
                    ):
                        data.append(
                            nested
                        )
                    else:
                        data_dict.update(
                            nested
                        )

            if (
                key.isdigit()
                and value.get("subtype")
                == "array"
            ):
                return data

            if data_dict:
                result[key] = data_dict
            else:
                result[key] = data

        elif value_type in (
            "string",
            "boolean",
        ):
            result[key] = value.get(
                "value"
            )

        elif value_type == "number":
            result[key] = value.get(
                "value",
                math.nan,
            )

        elif value_type == "undefined":
            result[key] = "??"

        else:
            raise NotImplementedError(
                value
            )

        return result

    async def get_value(
        self,
        expression,
    ):
        response = await self.send(
            RuntimeMethods.EVALUATE,
            {
                "expression": expression,
                "returnByValue": False,
            },
        )

        result = response[
            "result"
        ][
            "result"
        ]

        if "value" in result:
            return result["value"]

        object_id = result.get(
            "objectId"
        )

        if not object_id:
            return "??"

        properties = await self.get_properties(
            object_id
        )

        data = {}

        for prop in properties:
            if prop["name"] in SKIP_PROPERTIES:
                continue

            value = await self._get_value(
                prop["name"],
                prop["value"],
            )

            data.update(value)

        return data

    async def _construct_expression(
        self,
        target,
        data,
    ):
        serialized = json.dumps(
            data,
            ensure_ascii=False,
        )

        return (
            f"Object.assign({target}, "
            f"{serialized})"
        )

    async def set_value_json(
        self,
        target,
        data,
    ) -> None:
        expression = await self._construct_expression(
            target,
            data,
        )

        await self.send(
            RuntimeMethods.EVALUATE,
            {
                "expression": expression,
            },
        )

    async def set_value(
        self,
        target,
        value,
    ) -> None:
        if isinstance(value, dict):
            raise ValueError(
                "Dictionary detected, use "
                "set_value_json instead."
            )

        serialized = json.dumps(
            value,
            ensure_ascii=False,
        )

        await self.send(
            RuntimeMethods.EVALUATE,
            {
                "expression": (
                    f"{target} = {serialized}"
                ),
            },
        )
