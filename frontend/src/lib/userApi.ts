// BE must accept access token via Authorization: Bearer <accessToken>
// when NEXT_PUBLIC_USE_MOCK_API=false and real backend is configured.

import type { Profile } from "./types";

function getBaseUrl(): string {
  // if (process.env.NEXT_PUBLIC_USE_MOCK_API === "true") {
  //   return "/api/mock";
  // }
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
}

function buildHeaders(accessToken?: string): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  return headers;
}

export async function createUser(
  email?: string,
  accessToken?: string,
): Promise<{ userId: string }> {
  const res = await fetch(`${getBaseUrl()}/v1/users`, {
    method: "POST",
    headers: buildHeaders(accessToken),
    body: JSON.stringify(email ? { email } : {}),
  });
  if (!res.ok) throw new Error(`createUser failed: ${res.status}`);
  return res.json();
}

export async function getUser(
  userId: string,
  accessToken?: string,
): Promise<{ user: Record<string, unknown>; profile: Profile }> {
  const res = await fetch(`${getBaseUrl()}/v1/users/${userId}`, {
    headers: buildHeaders(accessToken),
  });
  if (!res.ok) throw new Error(`getUser failed: ${res.status}`);
  return res.json();
}

export async function patchProfile(
  userId: string,
  profilePatch: Partial<Profile>,
  accessToken?: string,
): Promise<{ profile: Profile }> {
  const res = await fetch(`${getBaseUrl()}/v1/users/${userId}/profile`, {
    method: "PATCH",
    headers: buildHeaders(accessToken),
    body: JSON.stringify({ profilePatch }),
  });
  if (!res.ok) throw new Error(`patchProfile failed: ${res.status}`);
  return res.json();
}
