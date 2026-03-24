import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(level_name: str, log_file_path: str) -> None:
    normalized = level_name.strip().upper() or "INFO"
    level = getattr(logging, normalized, logging.INFO)
    root_logger = logging.getLogger()
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    root_logger.setLevel(level)

    if not any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in root_logger.handlers
    ):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    normalized_path = log_file_path.strip()
    if normalized_path:
        target_path = Path(normalized_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path = target_path.resolve()

        if not any(
            isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).resolve() == resolved_path
            for handler in root_logger.handlers
        ):
            file_handler = RotatingFileHandler(
                resolved_path,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    logging.getLogger("app").setLevel(level)
