# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Application factory for the OCI IAM and Deep Data Security learning example."""

import atexit
from urllib.parse import urlsplit

from flask import Flask, Response

from deepsec_webapp.config import RuntimeConfig
from deepsec_webapp.database import create_runtime_pool
from deepsec_webapp.sessions import DemoSessionStore
from deepsec_webapp.web import web


def create_app(config: RuntimeConfig | None = None) -> Flask:
    """Create the learning application and its least-privileged connection pool."""
    resolved_config = config or RuntimeConfig.from_env()
    browser_host = urlsplit(resolved_config.base_url).hostname
    if browser_host is None:
        # RuntimeConfig validates this first; keep the application factory fail-closed.
        raise RuntimeError("OAM_WEB_BASE_URL must be a valid URL origin.")
    # Werkzeug expects brackets around an IPv6 literal in its trusted-host list.
    trusted_host = f"[{browser_host}]" if ":" in browser_host else browser_host
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=resolved_config.secret_key,
        MAX_CONTENT_LENGTH=16 * 1024,
        # Host validation is defense in depth in case the example is placed
        # behind a local proxy despite its loopback-only configuration checks.
        TRUSTED_HOSTS=[trusted_host],
    )

    pool = create_runtime_pool(resolved_config)
    app.extensions["deepsec_config"] = resolved_config
    app.extensions["deepsec_pool"] = pool
    app.extensions["deepsec_sessions"] = DemoSessionStore()
    app.register_blueprint(web)

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        """Apply conservative browser defaults to every dynamic and static response."""
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if resolved_config.secure_browser_transport:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    atexit.register(pool.close, force=True)
    return app


__all__ = ["create_app"]
