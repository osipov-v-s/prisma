/** Electron lifecycle, safe media protocol, and one IPC-to-Python bridge. */

import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

import { app, BrowserWindow, ipcMain, net, protocol } from "electron";


const moduleDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(moduleDirectory, "../../../..");
const isSmokeTest = process.env.PRISMA_SMOKE_TEST === "1";

protocol.registerSchemesAsPrivileged([
  { scheme: "prisma-media", privileges: { secure: true, standard: true, supportFetchAPI: true } },
]);

let mainWindow: BrowserWindow | null = null;
let worker: PythonWorker | null = null;

class PythonWorker {
  private process: ChildProcessWithoutNullStreams;
  private buffer = "";
  private nextId = 1;
  private pending = new Map<number, { resolve(value: unknown): void; reject(error: Error): void }>();

  constructor(dataRoot: string) {
    const command = workerCommand();
    this.process = spawn(command.executable, command.arguments, {
      cwd: repositoryRoot,
      env: { ...process.env, PYTHONUNBUFFERED: "1", PRISMA_DATA_ROOT: dataRoot },
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.process.stdout.on("data", (chunk: Buffer) => this.read(chunk.toString("utf8")));
    this.process.stderr.on("data", (chunk: Buffer) => console.info(chunk.toString().trim()));
    this.process.once("exit", () => this.rejectAll(new Error("Python worker завершил работу.")));
  }

  request(method: string, params: Record<string, unknown>): Promise<unknown> {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.process.stdin.write(`${JSON.stringify({ id, method, params })}\n`);
    });
  }

  stop(): void {
    this.process.kill();
  }

  private read(chunk: string): void {
    this.buffer += chunk;
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop() ?? "";
    for (const line of lines) if (line.trim()) this.resolveLine(line);
  }

  private resolveLine(line: string): void {
    const response = JSON.parse(line) as { id: number; result?: unknown; error?: string };
    const request = this.pending.get(response.id);
    if (!request) return;
    this.pending.delete(response.id);
    if (response.error) request.reject(new Error(response.error));
    else request.resolve(response.result);
  }

  private rejectAll(error: Error): void {
    for (const request of this.pending.values()) request.reject(error);
    this.pending.clear();
  }
}

function workerCommand(): { executable: string; arguments: string[] } {
  if (app.isPackaged) {
    const filename = process.platform === "win32" ? "prisma-worker.exe" : "prisma-worker";
    return { executable: path.join(process.resourcesPath, "worker", filename), arguments: [] };
  }
  const workspacePython = path.join(
    repositoryRoot, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  const executable = process.env.PRISMA_PYTHON || (existsSync(workspacePython) ? workspacePython : "python");
  return { executable, arguments: ["-m", "src.worker"] };
}

function registerMediaProtocol(dataRoot: string): void {
  const mediaRoot = path.resolve(dataRoot, "collections");
  protocol.handle("prisma-media", (request) => {
    const url = new URL(request.url);
    const relativePath = decodeURIComponent(url.pathname).replace(/^[/\\]+/, "");
    const resolved = path.resolve(mediaRoot, relativePath);
    if (!resolved.startsWith(`${mediaRoot}${path.sep}`)) return new Response("Forbidden", { status: 403 });
    return net.fetch(pathToFileURL(resolved).toString());
  });
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440, height: 940, minWidth: 1080, minHeight: 720, show: false,
    backgroundColor: "#f4f6f9", title: "ПРИЗМА Desktop",
    webPreferences: {
      preload: path.join(moduleDirectory, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.once("ready-to-show", () => { if (!isSmokeTest) mainWindow?.show(); });
  mainWindow.webContents.once("did-finish-load", () => {
    console.info("[prisma-desktop] renderer loaded");
    if (isSmokeTest) setTimeout(() => app.quit(), 1_500);
  });
  mainWindow.on("closed", () => { mainWindow = null; });
  const developmentUrl = process.env.VITE_DEV_SERVER_URL;
  if (developmentUrl) void mainWindow.loadURL(developmentUrl);
  else void mainWindow.loadFile(path.join(moduleDirectory, "../renderer/index.html"));
}

ipcMain.handle("prisma:invoke", (_event, method: string, params: Record<string, unknown>) => {
  if (!worker) throw new Error("Python worker ещё не запущен.");
  return worker.request(method, params);
});
ipcMain.handle("prisma:get-runtime-info", () => ({ platform: process.platform, version: app.getVersion() }));

app.whenReady().then(() => {
  const dataRoot = path.join(app.getPath("userData"), "data");
  registerMediaProtocol(dataRoot);
  worker = new PythonWorker(dataRoot);
  createWindow();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("before-quit", () => { worker?.stop(); worker = null; });
