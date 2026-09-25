# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Run the non-production OCI IAM and Deep Data Security web application."""

from deepsec_webapp import create_app

app = create_app()

if __name__ == "__main__":
    config = app.extensions["deepsec_config"]
    app.run(host=config.host, port=config.port, debug=False)
