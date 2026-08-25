#!/usr/bin/env python3
"""Generates live or mock telemetry for CineOps Guardian."""

import json
import os

from backend.app.domain.mock_data import get_mock_incident
from backend.app.integrations.mcap.generator import generate_synthetic_mcap


def main():
    print("Generating synthetic incident dataset...")
    incident = get_mock_incident()

    os.makedirs("synthetic/scenarios", exist_ok=True)
    os.makedirs("synthetic/telemetry", exist_ok=True)
    os.makedirs("synthetic/recordings", exist_ok=True)

    with open("synthetic/scenarios/stage_a_dolly_tf_drift.json", "w") as f:
        json.dump(incident.model_dump(), f, indent=2)

    mcap_path = generate_synthetic_mcap("synthetic/recordings/stage_a_take_003.mcap")
    print(f"Synthetic MCAP generated: {mcap_path}")
    print("Scenario saved to synthetic/scenarios/stage_a_dolly_tf_drift.json")


if __name__ == "__main__":
    main()
