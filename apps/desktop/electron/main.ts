import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { app, BrowserWindow, ipcMain } from "electron";


const SERVICE_HOST = "127.0.0.1";
const SERVICE_PORT = 8765;
const SERVICE_BASE_URL = `http://${SERVICE_HOST}:${SERVICE_PORT}`;
const moduleDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(moduleDirectory, "../../../..");
const isSmokeTest = process.env.PRISMA_SMOKE_TEST === "1";

let mainWindow: BrowserWindow | null = null;
let serviceProcess: ChildProcess | null = null;

function findPythonExecutable(): string {
  if (process.env.PRISMA_PYTHON) return process.env.PRISMA_PYTHON;

  const workspacePython = path.join(
    repositoryRoot,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  if (existsSync(workspacePython)) return workspacePython;
  return process.platform === "win32" ? "python" : "python3";
}

function packagedServiceExecutable(): string {
  return path.join(process.resourcesPath, "service", "prisma-service.exe");
}

function startLocalService(): void {
  if (serviceProcess) return;

  // The renderer never starts processes itself. Electron owns the local service
  // lifecycle and exposes only its fixed loopback URL through the preload bridge.
  const executable = app.isPackaged ? packagedServiceExecutable() : findPythonExecutable();
  const arguments_ = app.isPackaged ? [] : [
      "-m",
      "uvicorn",
      "prisma_service.main:app",
      "--app-dir",
      path.join(repositoryRoot, "apps/service"),
      "--host",
      SERVICE_HOST,
      "--port",
      String(SERVICE_PORT),
    ];
  const dataRoot = path.join(app.getPath("userData"), "data");
  serviceProcess = spawn(
    executable,
    arguments_,
    {
      cwd: repositoryRoot,
      env: { ...process.env, PYTHONUNBUFFERED: "1", PRISMA_DATA_ROOT: dataRoot },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );

  serviceProcess.stdout?.on("data", (data: Buffer) => {
    console.info(`[prisma-service] ${data.toString().trim()}`);
  });
  serviceProcess.stderr?.on("data", (data: Buffer) => {
    console.info(`[prisma-service] ${data.toString().trim()}`);
  });
  serviceProcess.once("exit", () => {
    serviceProcess = null;
  });
}

function stopLocalService(): void {
  if (!serviceProcess || serviceProcess.killed) return;
  serviceProcess.kill();
  serviceProcess = null;
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1080,
    minHeight: 720,
    show: false,
    backgroundColor: "#f4f6f9",
    title: "ПРИЗМА Desktop",
    webPreferences: {
      // Keep the shared React UI browser-compatible for later reuse by PRISMA Web.
      preload: path.join(moduleDirectory, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => {
    if (!isSmokeTest) mainWindow?.show();
  });
  mainWindow.webContents.once("did-finish-load", () => {
    console.info("[prisma-desktop] renderer loaded");
    if (isSmokeTest) setTimeout(() => app.quit(), 1_500);
  });
  mainWindow.webContents.once(
    "did-fail-load",
    (_event, errorCode, errorDescription) => {
      console.error(`[prisma-desktop] renderer failed: ${errorCode} ${errorDescription}`);
      process.exitCode = 1;
      if (isSmokeTest) app.quit();
    },
  );
  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  const developmentUrl = process.env.VITE_DEV_SERVER_URL;
  if (developmentUrl) {
    void mainWindow.loadURL(developmentUrl);
  } else {
    void mainWindow.loadFile(
      path.join(moduleDirectory, "../renderer/index.html"),
    );
  }
}

ipcMain.handle("prisma:get-service-base-url", () => SERVICE_BASE_URL);
ipcMain.handle("prisma:get-runtime-info", () => ({
  platform: process.platform,
  version: app.getVersion(),
}));

app.whenReady().then(() => {
  if (process.env.PRISMA_SKIP_SERVICE_START !== "1") startLocalService();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", stopLocalService);
