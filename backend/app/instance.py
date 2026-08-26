"""Which serving instance answered a request.

Once the incident lives outside the process, the service is free to run on many
instances — and the only honest way to show that state is genuinely shared is to
be able to tell the instances apart. Cloud Run exposes an id on the metadata
server; every response carries it as ``X-Instance-Id``, so a caller can watch
several instances return the same incident.

Off Cloud Run there is no metadata server, so the id degrades to a per-process
label rather than failing.
"""

import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_METADATA_URL = "http://metadata.google.internal/computeMetadata/v1/instance/id"
_instance_id: str | None = None


def instance_id() -> str:
    """Short, stable id for this serving instance. Resolved once per process."""
    global _instance_id
    if _instance_id is not None:
        return _instance_id
    try:
        req = urllib.request.Request(_METADATA_URL, headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            _instance_id = resp.read().decode().strip()[-12:]
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        logger.debug("No metadata server (%s); using process id", e)
        _instance_id = f"local-{os.getpid()}"
    return _instance_id
