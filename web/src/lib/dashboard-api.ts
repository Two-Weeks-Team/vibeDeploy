import { DASHBOARD_API_URL } from "./api";
import type { DeployedApp } from "@/types/dashboard";

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${DASHBOARD_API_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export async function getDashboardStats(): Promise<{
  total_meetings: number;
  total_brainstorms: number;
  avg_score: number;
  go_count: number;
  nogo_count: number;
}> {
  try {
    const response = await fetch(`${DASHBOARD_API_URL}/dashboard/stats`);
    if (!response.ok) throw new Error("Failed to fetch stats");
    return response.json();
  } catch {
    return {
      total_meetings: 0,
      total_brainstorms: 0,
      avg_score: 0,
      go_count: 0,
      nogo_count: 0,
    };
  }
}

export async function getDashboardResults(): Promise<
  Array<{
    thread_id: string;
    score: number;
    verdict: string;
    created_at: string;
  }>
> {
  try {
    const response = await fetch(`${DASHBOARD_API_URL}/dashboard/results`);
    if (!response.ok) throw new Error("Failed to fetch results");
    return response.json();
  } catch {
    return [];
  }
}

export async function getDashboardBrainstorms(): Promise<
  Array<{
    thread_id: string;
    created_at: string;
  }>
> {
  try {
    const response = await fetch(`${DASHBOARD_API_URL}/dashboard/brainstorms`);
    if (!response.ok) throw new Error("Failed to fetch brainstorms");
    return response.json();
  } catch {
    return [];
  }
}

export async function getDashboardDeployments(): Promise<DeployedApp[]> {
  try {
    const response = await fetch(`${DASHBOARD_API_URL}/dashboard/deployments`);
    if (!response.ok) throw new Error("Failed to fetch deployments");
    return response.json();
  } catch {
    return [];
  }
}
