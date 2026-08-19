import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("prismaDesktop", {
  getServiceBaseUrl: () => ipcRenderer.invoke("prisma:get-service-base-url"),
  getRuntimeInfo: () => ipcRenderer.invoke("prisma:get-runtime-info"),
});
