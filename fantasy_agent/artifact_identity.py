from __future__ import annotations

import hashlib
from pathlib import Path

from fantasy_agent.contracts import ArtifactIdentity


_READ_CHUNK_BYTES = 1024 * 1024


def compute_artifact_identity(path: str | Path) -> ArtifactIdentity:
    digest = hashlib.sha256()
    with Path(path).open('rb') as artifact:
        for chunk in iter(lambda: artifact.read(_READ_CHUNK_BYTES), b''):
            digest.update(chunk)
    return ArtifactIdentity(digest=digest.hexdigest())
