import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("prismaDesktop", {
  invoke: (method: string, params: Record<string, unknown> = {}) =>
    ipcRenderer.invoke("prisma:invoke", method, params),
  getRuntimeInfo: () => ipcRenderer.invoke("prisma:get-runtime-info"),
});
