import logging

from flask import request


def configure_logging(app):
    level_name = app.config.get("LOG_LEVEL", "INFO")
    level = getattr(logging, level_name, logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s"
    )

    app.logger.setLevel(level)
    for handler in app.logger.handlers:
        handler.setLevel(level)
        handler.setFormatter(formatter)

    @app.after_request
    def log_unsuccessful_response(response):
        if response.status_code >= 400:
            app.logger.warning(
                "request_failed method=%s path=%s endpoint=%s status=%s",
                request.method,
                request.path,
                request.endpoint or "unknown",
                response.status_code,
            )
        return response
