export {};

declare global {
  interface Window {
    prismaDesktop?: {
      getServiceBaseUrl(): Promise<string>;
      getRuntimeInfo(): Promise<{ platform: string; version: string }>;
    };
  }
}
