/** Safe CommonJS bridge exposed to the sandboxed renderer. */

const { contextBridge, ipcRenderer } = require("electron") as typeof import("electron");

contextBridge.exposeInMainWorld("prismaDesktop", {
  invoke: (method: string, params: Record<string, unknown> = {}) =>
    ipcRenderer.invoke("prisma:invoke", method, params),
  getRuntimeInfo: () => ipcRenderer.invoke("prisma:get-runtime-info"),
});
