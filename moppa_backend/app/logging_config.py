import logging


def configure_logging(level_name: str) -> None:
    normalized = level_name.strip().upper() or "INFO"
    level = getattr(logging, normalized, logging.INFO)
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    else:
        root_logger.setLevel(level)

    logging.getLogger("app").setLevel(level)
