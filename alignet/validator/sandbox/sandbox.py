from datetime import datetime
from docker.models.containers import Container


class SandBox:
    image: str
    temp_dir: str
    env_vars: dict
    on_finish: callable
    timeout: int
    start_time: datetime
    container: Container
    killed_by_watchdog: bool = False

    def __init__(
        self,
        *,
        image: str,
        temp_dir: str,
        env_vars: dict,
        on_finish: callable,
        timeout: int,
    ):
        self.image = image
        self.temp_dir = temp_dir
        self.env_vars = env_vars
        self.on_finish = on_finish
        self.timeout = timeout
        self.start_time = datetime.now()
        self.container = None
