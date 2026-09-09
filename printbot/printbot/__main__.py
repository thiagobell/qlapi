import logging
import sys

from printbot.bot import build_application
from printbot.config import InvalidConfigError, load_config
from printbot.qlapi_client import QlapiClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        config = load_config()
    except InvalidConfigError as exc:
        logger.error("Invalid configuration: %s", exc)
        sys.exit(1)

    client = QlapiClient(config.qlapi.base_url, timeout=config.qlapi.timeout_seconds)
    application = build_application(config, client)

    # run_polling manages its own event loop and signal handlers, and closes
    # the loop on exit. Deliberately no client.aclose() here: the httpx pool's
    # idle connections are bound to that now-closed loop, so closing them
    # afterwards raises "Event loop is closed". The process is exiting; the OS
    # reclaims the sockets.
    application.run_polling()


if __name__ == "__main__":
    main()
