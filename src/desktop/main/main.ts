/** Electron lifecycle, safe media protocol, and one IPC-to-Python bridge. */

import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { appendFileSync, createWriteStream, existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

import { app, BrowserWindow, ipcMain, net, protocol } from "electron";
import { verifyRunnerFlow } from "./runner-smoke.js";


const moduleDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(moduleDirectory, "../../../..");
const isSmokeTest = process.env.PRISMA_SMOKE_TEST === "1";
const isRunnerSmokeTest = process.env.PRISMA_RUNNER_SMOKE_TEST === "1";
const isAutomatedTest = isSmokeTest || isRunnerSmokeTest;

protocol.registerSchemesAsPrivileged([
  { scheme: "prisma-media", privileges: { secure: true, standard: true, supportFetchAPI: true } },
]);

let mainWindow: BrowserWindow | null = null;
let worker: PythonWorker | null = null;
let desktopLogPath: string | null = null;

function traceIpc(method: string): boolean {
  return method === "health" || method.startsWith("sessions.");
}

function logDesktop(source: string, message: string): void {
  const line = `${new Date().toISOString()} [${source}] ${message}\n`;
  console.info(line.trim());
  if (desktopLogPath) appendFileSync(desktopLogPath, line, "utf8");
}

class PythonWorker {
  private process: ChildProcessWithoutNullStreams;
  private buffer = "";
  private nextId = 1;
  private pending = new Map<number, {
    method: string;
    startedAt: number;
    resolve(value: unknown): void;
    reject(error: Error): void;
    timeout: ReturnType<typeof setTimeout>;
  }>();

  constructor(dataRoot: string) {
    const command = workerCommand();
    mkdirSync(dataRoot, { recursive: true });
    const workerLog = createWriteStream(path.join(dataRoot, "worker.log"), { flags: "a" });
    logDesktop("worker", `starting ${command.executable}`);
    this.process = spawn(command.executable, command.arguments, {
      cwd: app.isPackaged ? path.dirname(command.executable) : repositoryRoot,
      env: { ...process.env, PYTHONUNBUFFERED: "1", PRISMA_DATA_ROOT: dataRoot },
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.process.stdout.on("data", (chunk: Buffer) => this.read(chunk.toString("utf8")));
    this.process.stderr.on("data", (chunk: Buffer) => {
      workerLog.write(chunk);
      const message = chunk.toString().trim();
      if (message) logDesktop("worker:stderr", message);
    });
    this.process.once("spawn", () => logDesktop("worker", `started, pid=${this.process.pid}`));
    this.process.once("error", (error) => {
      logDesktop("worker", `start failed: ${error.message}`);
      this.rejectAll(error);
    });
    this.process.once("exit", (code, signal) => {
      const message = `exited, code=${String(code)}, signal=${String(signal)}`;
      logDesktop("worker", message);
      this.rejectAll(new Error(`Python worker завершил работу: ${message}`));
    });
  }

  request(method: string, params: Record<string, unknown>): Promise<unknown> {
    const id = this.nextId++;
    const startedAt = Date.now();
    if (traceIpc(method)) logDesktop("ipc", `${method} #${id} requested`);
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id);
        logDesktop("ipc", `${method} #${id} timed out after 15000 ms`);
        reject(new Error(`Python worker не ответил на ${method} за 15 секунд.`));
      }, 15_000);
      this.pending.set(id, { method, startedAt, resolve, reject, timeout });
      this.process.stdin.write(`${JSON.stringify({ id, method, params })}\n`, (error) => {
        if (error) this.rejectRequest(id, error);
      });
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
    let response: { id: number; result?: unknown; error?: string };
    try {
      response = JSON.parse(line) as typeof response;
    } catch (error) {
      logDesktop("worker", `invalid protocol response: ${String(error)}`);
      this.rejectAll(new Error("Python worker вернул некорректный ответ."));
      return;
    }
    const request = this.pending.get(response.id);
    if (!request) return;
    this.pending.delete(response.id);
    clearTimeout(request.timeout);
    const elapsed = Date.now() - request.startedAt;
    if (traceIpc(request.method)) {
      logDesktop("ipc", `${request.method} #${response.id} answered in ${elapsed} ms`);
    }
    if (response.error) request.reject(new Error(response.error));
    else request.resolve(response.result);
  }

  private rejectRequest(id: number, error: Error): void {
    const request = this.pending.get(id);
    if (!request) return;
    this.pending.delete(id);
    clearTimeout(request.timeout);
    logDesktop("ipc", `${request.method} #${id} write failed: ${error.message}`);
    request.reject(error);
  }

  private rejectAll(error: Error): void {
    for (const request of this.pending.values()) {
      clearTimeout(request.timeout);
      request.reject(error);
    }
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
      // CommonJS is required for a sandboxed preload in the packaged app.
      preload: path.join(moduleDirectory, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.once("ready-to-show", () => { if (!isAutomatedTest) mainWindow?.show(); });
  mainWindow.webContents.once("did-finish-load", async () => {
    logDesktop("main", "renderer loaded");
    if (isRunnerSmokeTest) await verifyPackagedRunner();
    else if (isSmokeTest) await verifyPackagedBridge();
  });
  mainWindow.webContents.on("console-message", (details) => {
    logDesktop(
      `renderer:${details.level}`,
      `${details.message} (${details.sourceId}:${details.lineNumber})`,
    );
  });
  mainWindow.webContents.on("preload-error", (_event, preloadPath, error) => {
    logDesktop("preload", `${preloadPath}: ${error.stack || error.message}`);
  });
  mainWindow.webContents.on("render-process-gone", (_event, details) => {
    logDesktop("renderer", `process gone: ${details.reason}, code ${details.exitCode}`);
  });
  mainWindow.on("closed", () => { mainWindow = null; });
  const developmentUrl = process.env.VITE_DEV_SERVER_URL;
  if (developmentUrl) void mainWindow.loadURL(developmentUrl);
  else void mainWindow.loadFile(path.join(moduleDirectory, "../renderer/index.html"));
}

async function verifyPackagedRunner(): Promise<void> {
  try {
    if (!mainWindow) throw new Error("renderer window is unavailable");
    await verifyRunnerFlow(mainWindow);
    logDesktop("smoke", "runner pair-transition smoke test passed");
    app.exit(0);
  } catch (error) {
    logDesktop("smoke", `runner pair-transition smoke test failed: ${String(error)}`);
    app.exit(1);
  }
}

async function verifyPackagedBridge(): Promise<void> {
  try {
    const result = await mainWindow?.webContents.executeJavaScript(
      'window.prismaDesktop.invoke("health", {})',
    ) as { status?: string } | undefined;
    if (result?.status !== "ok") throw new Error("health вернул некорректный результат");
    logDesktop("smoke", "IPC smoke test passed");
    app.exit(0);
  } catch (error) {
    logDesktop("smoke", `IPC smoke test failed: ${String(error)}`);
    app.exit(1);
  }
}

ipcMain.handle("prisma:invoke", (_event, method: string, params: Record<string, unknown>) => {
  if (!worker) throw new Error("Python worker ещё не запущен.");
  return worker.request(method, params);
});
ipcMain.handle("prisma:get-runtime-info", () => ({ platform: process.platform, version: app.getVersion() }));

const primaryInstance = isAutomatedTest || app.requestSingleInstanceLock();
if (!primaryInstance) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (!mainWindow) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  });
  app.whenReady().then(() => {
    const dataRoot = process.env.PRISMA_DATA_ROOT || path.join(app.getPath("userData"), "data");
    mkdirSync(dataRoot, { recursive: true });
    desktopLogPath = path.join(dataRoot, "desktop.log");
    registerMediaProtocol(dataRoot);
    worker = new PythonWorker(dataRoot);
    createWindow();
    app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
  });
}

app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("before-quit", () => { worker?.stop(); worker = null; });
