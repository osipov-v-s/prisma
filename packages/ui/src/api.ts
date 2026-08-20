/** Typed renderer calls sent directly through Electron IPC; no HTTP or fetch. */

import type {
  Account,
  AvailableTest,
  CollectionRecord,
  CollectionWrite,
  HealthResponse,
  LoginResponse,
  TestSession,
  UserCreate,
} from "./types";


let accessToken: string | null = null;

function invoke<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
  if (!window.prismaDesktop) {
    return Promise.reject(new Error("Desktop IPC bridge недоступен."));
  }
  return window.prismaDesktop.invoke<T>(method, params);
}

function authenticated<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
  return invoke<T>(method, { ...params, token: accessToken });
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export async function login(
  _serviceBaseUrl: string,
  loginName: string,
  password: string,
): Promise<LoginResponse> {
  const result = await invoke<LoginResponse>("auth.login", { login: loginName, password });
  setAccessToken(result.access_token);
  return result;
}

export async function logout(_serviceBaseUrl: string): Promise<void> {
  await invoke("auth.logout", { token: accessToken });
  setAccessToken(null);
}

export function getHealth(_serviceBaseUrl: string): Promise<HealthResponse> {
  return invoke("health");
}

export function getCurrentAccount(_serviceBaseUrl: string): Promise<Account> {
  return authenticated("auth.me");
}

export function getUsers(_serviceBaseUrl: string): Promise<Account[]> {
  return authenticated("users.list");
}

export function createUser(_serviceBaseUrl: string, data: UserCreate): Promise<Account> {
  return authenticated("users.create", { data });
}

export function deleteUser(_serviceBaseUrl: string, accountId: string): Promise<void> {
  return authenticated("users.delete", { account_id: accountId });
}

export function getCollections(_serviceBaseUrl: string): Promise<CollectionRecord[]> {
  return authenticated("collections.list");
}

export function createCollection(
  _serviceBaseUrl: string,
  data: CollectionWrite,
): Promise<CollectionRecord> {
  return authenticated("collections.create", { data });
}

export function updateCollection(
  _serviceBaseUrl: string,
  collectionId: string,
  data: CollectionWrite,
): Promise<CollectionRecord> {
  return authenticated("collections.update", { collection_id: collectionId, data });
}

export function activateCollection(
  _serviceBaseUrl: string,
  collectionId: string,
): Promise<CollectionRecord> {
  return authenticated("collections.activate", { collection_id: collectionId });
}

export function deactivateCollection(
  _serviceBaseUrl: string,
  collectionId: string,
): Promise<CollectionRecord> {
  return authenticated("collections.deactivate", { collection_id: collectionId });
}

export async function uploadCollectionImage(
  _serviceBaseUrl: string,
  collectionId: string,
  rowIndex: number,
  levelIndex: number,
  image: File,
): Promise<CollectionRecord> {
  return authenticated("collections.upload", {
    collection_id: collectionId,
    row_index: rowIndex,
    level_index: levelIndex,
    content_type: image.type,
    content_base64: await fileAsBase64(image),
  });
}

export function getAvailableTests(_serviceBaseUrl: string): Promise<AvailableTest[]> {
  return authenticated("tests.list");
}

export function createTestSession(
  _serviceBaseUrl: string,
  collectionId: string,
): Promise<TestSession> {
  return authenticated("sessions.create", { collection_id: collectionId });
}

export function getSessions(_serviceBaseUrl: string): Promise<TestSession[]> {
  return authenticated("sessions.list");
}

export function getSession(
  _serviceBaseUrl: string,
  sessionId: string,
  trace = false,
): Promise<TestSession> {
  return authenticated("sessions.get", { session_id: sessionId, trace });
}

export function presentNext(_serviceBaseUrl: string, sessionId: string): Promise<TestSession> {
  return authenticated("sessions.present", { session_id: sessionId });
}

export function startMainTest(_serviceBaseUrl: string, sessionId: string): Promise<TestSession> {
  return authenticated("sessions.start", { session_id: sessionId });
}

export function savePairResponse(
  _serviceBaseUrl: string,
  sessionId: string,
  presentationIndex: number,
  selectedItemId: string | null,
  reactionTimeMs: number,
  timedOut = false,
): Promise<TestSession> {
  return authenticated("sessions.respond", {
    session_id: sessionId,
    presentation_index: presentationIndex,
    data: { selected_item_id: selectedItemId, reaction_time_ms: reactionTimeMs, timed_out: timedOut },
  });
}

export async function downloadReport(
  _serviceBaseUrl: string,
  path: string,
  filename: string,
): Promise<void> {
  const method = path.endsWith("report.pdf")
    ? "reports.pdf"
    : path.includes("/admin/") ? "reports.admin_xlsx" : "reports.xlsx";
  const sessionId = path.match(/sessions\/([^/]+)/)?.[1];
  const content = await authenticated<string>(method, { session_id: sessionId });
  saveBase64(content, filename);
}

export function mediaUrl(_serviceBaseUrl: string, path: string | null): string | null {
  return path;
}

function fileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Не удалось прочитать изображение."));
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.readAsDataURL(file);
  });
}

function saveBase64(content: string, filename: string): void {
  const binary = atob(content);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes]));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}
