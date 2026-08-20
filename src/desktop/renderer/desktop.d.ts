export {};

declare global {
  interface Window {
    prismaDesktop?: {
      invoke<T>(method: string, params?: Record<string, unknown>): Promise<T>;
      getRuntimeInfo(): Promise<{ platform: string; version: string }>;
    };
  }
}
