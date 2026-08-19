import type {
  CollectionRecord,
  CollectionWrite,
  HealthResponse,
  SessionAnalysis,
  Account,
  AvailableTest,
  LoginResponse,
  TestSession,
  UserCreate,
} from "./types";

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(url, { ...init, headers });
  if (!response.ok) {
    let message = `Сервис вернул ошибку ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string | string[] };
      if (Array.isArray(payload.detail)) message = payload.detail.join("\n");
      else if (payload.detail) message = payload.detail;
    } catch {
      // Keep the status-based message when the server response is not JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export async function login(serviceBaseUrl: string, loginName: string, password: string): Promise<LoginResponse> {
  const result = await requestJson<LoginResponse>(`${serviceBaseUrl}/api/v1/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login: loginName, password }),
  });
  setAccessToken(result.access_token);
  return result;
}

export async function logout(serviceBaseUrl: string): Promise<void> {
  await fetch(`${serviceBaseUrl}/api/v1/auth/logout`, {
    method: "POST", headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  setAccessToken(null);
}

export function getCurrentAccount(serviceBaseUrl: string): Promise<Account> {
  return requestJson(`${serviceBaseUrl}/api/v1/auth/me`);
}

export function getUsers(serviceBaseUrl: string): Promise<Account[]> {
  return requestJson(`${serviceBaseUrl}/api/v1/users`);
}

export function createUser(serviceBaseUrl: string, payload: UserCreate): Promise<Account> {
  return requestJson(`${serviceBaseUrl}/api/v1/users`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
}

export async function deleteUser(serviceBaseUrl: string, accountId: string): Promise<void> {
  const response = await fetch(`${serviceBaseUrl}/api/v1/users/${accountId}`, {
    method: "DELETE", headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new Error("Не удалось удалить пользователя");
}

export function getAvailableTests(serviceBaseUrl: string): Promise<AvailableTest[]> {
  return requestJson(`${serviceBaseUrl}/api/v1/tests`);
}

export function createTestSession(serviceBaseUrl: string, collectionId: string): Promise<TestSession> {
  return requestJson(`${serviceBaseUrl}/api/v1/sessions`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ collection_id: collectionId }),
  });
}

export function getSessions(serviceBaseUrl: string): Promise<TestSession[]> {
  return requestJson(`${serviceBaseUrl}/api/v1/sessions`);
}

export function getSession(serviceBaseUrl: string, sessionId: string, trace = false): Promise<TestSession> {
  return requestJson(`${serviceBaseUrl}/api/v1/sessions/${sessionId}?trace=${trace}`);
}

export function presentNext(serviceBaseUrl: string, sessionId: string): Promise<TestSession> {
  return requestJson(`${serviceBaseUrl}/api/v1/sessions/${sessionId}/present`, { method: "POST" });
}

export function startMainTest(serviceBaseUrl: string, sessionId: string): Promise<TestSession> {
  return requestJson(`${serviceBaseUrl}/api/v1/sessions/${sessionId}/start`, { method: "POST" });
}

export function savePairResponse(serviceBaseUrl: string, sessionId: string, comparisonIndex: number,
  selectedItemId: string | null, reactionTimeMs: number, timedOut = false): Promise<TestSession> {
  return requestJson(`${serviceBaseUrl}/api/v1/sessions/${sessionId}/responses/${comparisonIndex}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_item_id: selectedItemId, reaction_time_ms: reactionTimeMs, timed_out: timedOut }),
  });
}

export async function downloadReport(serviceBaseUrl: string, path: string, filename: string): Promise<void> {
  const response = await fetch(`${serviceBaseUrl}${path}`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  if (!response.ok) throw new Error("Не удалось сформировать отчёт");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

export function getHealth(serviceBaseUrl: string): Promise<HealthResponse> {
  return requestJson(`${serviceBaseUrl}/api/v1/health`);
}

export function getDemoAnalysis(
  serviceBaseUrl: string,
): Promise<SessionAnalysis> {
  return requestJson(`${serviceBaseUrl}/api/v1/analysis/demo`);
}

export function getCollections(serviceBaseUrl: string): Promise<CollectionRecord[]> {
  return requestJson(`${serviceBaseUrl}/api/v1/collections`);
}

export function createCollection(
  serviceBaseUrl: string,
  collection: CollectionWrite,
): Promise<CollectionRecord> {
  return requestJson(`${serviceBaseUrl}/api/v1/collections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collection),
  });
}

export function updateCollection(
  serviceBaseUrl: string,
  collectionId: string,
  collection: CollectionWrite,
): Promise<CollectionRecord> {
  return requestJson(`${serviceBaseUrl}/api/v1/collections/${collectionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collection),
  });
}

export function activateCollection(
  serviceBaseUrl: string,
  collectionId: string,
): Promise<CollectionRecord> {
  return requestJson(
    `${serviceBaseUrl}/api/v1/collections/${collectionId}/activate`,
    { method: "POST" },
  );
}

export function deactivateCollection(
  serviceBaseUrl: string,
  collectionId: string,
): Promise<CollectionRecord> {
  return requestJson(
    `${serviceBaseUrl}/api/v1/collections/${collectionId}/deactivate`,
    { method: "POST" },
  );
}

export function uploadCollectionImage(
  serviceBaseUrl: string,
  collectionId: string,
  rowIndex: number,
  levelIndex: number,
  image: File,
): Promise<CollectionRecord> {
  const body = new FormData();
  body.append("image", image);
  return requestJson(
    `${serviceBaseUrl}/api/v1/collections/${collectionId}/rows/${rowIndex}/levels/${levelIndex}/image`,
    { method: "POST", body },
  );
}

export function mediaUrl(serviceBaseUrl: string, path: string | null): string | null {
  return path ? `${serviceBaseUrl}${path}` : null;
}
