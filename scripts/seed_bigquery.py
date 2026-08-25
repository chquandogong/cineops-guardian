#!/usr/bin/env python3
"""Seeds synthetic historical incidents into Google Cloud BigQuery."""
import os
from google.cloud import bigquery

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'project-55fbcfd2-0ad6-4c99-a25')
DATASET_ID = os.getenv('BIGQUERY_DATASET', 'cineops_guardian')
TABLE_ID = 'incident_history'

HISTORICAL_RECORDS = [
    {
        'incident_id': 'inc-stage-b-044',
        'event_date': '2026-08-10',
        'stage_name': 'Stage B — Virtual Volume',
        'asset_id': 'dolly-bravo-02',
        'asset_type': 'camera_dolly',
        'scene_take': 'Scene 18 Take 2',
        'symptoms_summary': 'Lens swap to 50mm Anamorphic caused dolly avoidance jitter and dropped camera sync.',
        'confirmed_root_cause': 'Stale URDF TF matrix between optical nodal point and base LiDAR.',
        'recovery_action': 'Reloaded approved calibration profile CALIB-RIG-STAGE-B-v2.',
        'delay_minutes': 4,
        'similarity_score': 0.94,
    },
    {
        'incident_id': 'inc-stage-a-019',
        'event_date': '2026-07-28',
        'stage_name': 'Stage A — Virtual Volume',
        'asset_id': 'dolly-alpha-01',
        'asset_type': 'camera_dolly',
        'scene_take': 'Scene 09 Take 5',
        'symptoms_summary': 'Dolly paused during rapid dolly-in near lighting scaffold with costmap warning.',
        'confirmed_root_cause': 'LiDAR mount vibration loosening + 20mm extrinsic calibration shift.',
        'recovery_action': 'Tightened mount bracket and executed recalibration script.',
        'delay_minutes': 7,
        'similarity_score': 0.82,
    },
    {
        'incident_id': 'inc-stage-c-008',
        'event_date': '2026-06-15',
        'stage_name': 'Stage C — LED Stage',
        'asset_id': 'jib-charlie-01',
        'asset_type': 'robotic_jib',
        'scene_take': 'Scene 03 Take 12',
        'symptoms_summary': 'Tracking frame drop at high slew rate; genlock packet loss exceeded 5%.',
        'confirmed_root_cause': 'Private 5G base station antenna polarization mismatch.',
        'recovery_action': 'Realigned directional patch antenna and switched to secondary RF channel.',
        'delay_minutes': 14,
        'similarity_score': 0.45,
    },
]

def main():
    print(f'Connecting to BigQuery project {PROJECT_ID}...')
    client = bigquery.Client(project=PROJECT_ID)
    dataset_ref = client.dataset(DATASET_ID)
    
    # Create dataset if not exists
    try:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = 'US'
        client.create_dataset(dataset, exists_ok=True)
        print(f'Dataset {DATASET_ID} confirmed.')
    except Exception as e:
        print(f'Dataset check: {e}')

    table_ref = dataset_ref.table(TABLE_ID)
    schema = [
        bigquery.SchemaField('incident_id', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('event_date', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('stage_name', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('asset_id', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('asset_type', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('scene_take', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('symptoms_summary', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('confirmed_root_cause', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('recovery_action', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField('delay_minutes', 'INT64', mode='REQUIRED'),
        bigquery.SchemaField('similarity_score', 'FLOAT64', mode='REQUIRED'),
    ]

    table = bigquery.Table(table_ref, schema=schema)
    client.create_table(table, exists_ok=True)
    print(f'Table {TABLE_ID} schema ready.')

    errors = client.insert_rows_json(table_ref, HISTORICAL_RECORDS)
    if not errors:
        print(f'Successfully inserted {len(HISTORICAL_RECORDS)} historical incidents.')
    else:
        print(f'Encountered errors inserting rows: {errors}')

if __name__ == '__main__':
    main()
