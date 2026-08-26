"""Where the incident under investigation lives.

The incident used to be a field on a module-level service object, so two Cloud Run
instances disagreed about it and the service had to be pinned to one. That is fine
for a single demo stage and wrong for anything else: the console polls
``/incidents/current`` while a POST or an SSE stream is mutating the incident, and
those requests are not guaranteed to land on the same instance.

Two backends behind one interface:

* ``memory``    — process-local. Hermetic, no credentials, right for mock mode and
  local development, and the fallback if Firestore is unreachable.
* ``firestore`` — one document per incident id, so every instance reads the same
  state and progress written mid-stream is visible to a concurrent reader.

The incident is a Pydantic model, so persistence is ``model_dump`` on the way out
and ``model_validate`` on the way back.
"""

import logging
from typing import Any, Protocol

from backend.app.domain.mock_data import get_mock_incident
from backend.app.domain.models import Incident
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class IncidentStore(Protocol):
    """Load/save for the incident currently under investigation."""

    backend: str

    async def load(self, incident_id: str) -> Incident: ...

    async def save(self, incident: Incident) -> None: ...


class InMemoryIncidentStore:
    """Process-local store. Correct only while the service runs as one instance."""

    backend = "memory"

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}

    async def load(self, incident_id: str) -> Incident:
        incident = self._incidents.get(incident_id)
        if incident is None:
            incident = get_mock_incident()
            self._incidents[incident_id] = incident
        return incident

    async def save(self, incident: Incident) -> None:
        self._incidents[incident.incident_id] = incident


class FirestoreIncidentStore:
    """One Firestore document per incident, shared across every instance."""

    backend = "firestore"

    def __init__(self) -> None:
        from google.cloud import firestore

        kwargs: dict[str, Any] = {"project": settings.GOOGLE_CLOUD_PROJECT}
        if settings.FIRESTORE_DATABASE:
            kwargs["database"] = settings.FIRESTORE_DATABASE
        self._client = firestore.AsyncClient(**kwargs)
        self._collection = settings.FIRESTORE_COLLECTION

    def _doc(self, incident_id: str):
        return self._client.collection(self._collection).document(incident_id)

    async def load(self, incident_id: str) -> Incident:
        snapshot = await self._doc(incident_id).get()
        if snapshot.exists:
            try:
                return Incident.model_validate(snapshot.to_dict())
            except Exception as e:  # noqa: BLE001 - a stale document must not 500
                logger.warning("Stored incident %s failed validation: %s", incident_id, e)
        incident = get_mock_incident()
        await self.save(incident)
        return incident

    async def save(self, incident: Incident) -> None:
        await self._doc(incident.incident_id).set(incident.model_dump(mode="json"))


def build_incident_store() -> IncidentStore:
    """Returns the configured store, degrading to memory if Firestore is unusable."""
    if settings.INCIDENT_STORE != "firestore":
        return InMemoryIncidentStore()
    try:
        store = FirestoreIncidentStore()
    except Exception as e:  # noqa: BLE001 - never fail startup over a store choice
        logger.warning(
            "Firestore incident store unavailable (%s: %s); using in-process state. "
            "Pin the service to one instance if this persists.",
            type(e).__name__,
            e,
        )
        return InMemoryIncidentStore()
    logger.info(
        "Incident state in Firestore collection %r (database %r)",
        settings.FIRESTORE_COLLECTION,
        settings.FIRESTORE_DATABASE or "(default)",
    )
    return store
