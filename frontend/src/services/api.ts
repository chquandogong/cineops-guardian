import { Incident } from '../types';

const BASE_URL = '/api/v1';

export async function fetchCurrentIncident(): Promise<Incident> {
  const response = await fetch(`${BASE_URL}/incidents/current`);
  if (!response.ok) {
    throw new Error(`Failed to fetch incident: ${response.statusText}`);
  }
  return response.json();
}

export async function triggerInvestigation(): Promise<Incident> {
  const response = await fetch(`${BASE_URL}/incidents/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to run investigation: ${response.statusText}`);
  }
  return response.json();
}

export async function approveRecovery(actionId: string, operatorName: string): Promise<Incident> {
  const response = await fetch(`${BASE_URL}/incidents/approve-recovery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action_id: actionId, operator_name: operatorName }),
  });
  if (!response.ok) {
    throw new Error(`Failed to approve recovery: ${response.statusText}`);
  }
  return response.json();
}

export async function resetIncident(): Promise<Incident> {
  const response = await fetch(`${BASE_URL}/incidents/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to reset incident: ${response.statusText}`);
  }
  return response.json();
}

export function getMcapDownloadUrl(incidentId: string): string {
  return `${BASE_URL}/incidents/${incidentId}/recording.mcap`;
}
