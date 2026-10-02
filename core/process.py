from core import config

from pathlib import Path
from typing import Union, Optional

import os
import subprocess


class GameProcess:
    def __init__(
        self,
        game: Union[Path, str],
        port: Optional[int] = None,
    ) -> None:
        if isinstance(game, str):
            game = Path(game)

        game = game.expanduser().resolve()

        if not game.exists():
            raise FileNotFoundError(game)

        if not game.is_file():
            raise ValueError(
                f"Game path is not a file: {game}"
            )

        self.game = game
        self.game_name = game.name
        self.port = (
            int(port)
            if port is not None
            else int(
                config.obtener_valor_configuracion(
                    "websocket",
                    "port",
                )
            )
        )

        self.process = None

    @property
    def is_running(self) -> bool:
        return (
            self.process is not None
            and self.process.poll() is None
        )

    def construir_argumentos(self):
        return [
            str(self.game),
            f"--remote-debugging-port={self.port}",
            "--remote-debugging-address=127.0.0.1",
            "--disable-web-security",
        ]

    def iniciar_juego(self):
        if self.is_running:
            return self.process

        self.process = subprocess.Popen(
            self.construir_argumentos(),
            cwd=str(self.game.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt"
                else 0
            ),
        )

        return self.process

    def detener(self):
        if not self.is_running:
            self.process = None
            return

        try:
            self.process.terminate()
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        finally:
            self.process = None
