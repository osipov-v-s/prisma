import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { PrismaApp } from "@prisma/ui";
import "@prisma/ui/styles.css";

// Keep renderer failures visible in the desktop log, not only in DevTools.
window.addEventListener("error", (event) => {
  console.error("[prisma-renderer] uncaught error", event.error ?? event.message);
});
window.addEventListener("unhandledrejection", (event) => {
  console.error("[prisma-renderer] unhandled promise rejection", event.reason);
});

function DesktopRoot() {
  return <PrismaApp serviceBaseUrl="" runtimeLabel="Desktop" />;
}

const root = document.getElementById("root");
if (!root) throw new Error("Root element was not found");

createRoot(root).render(
  <StrictMode>
    <DesktopRoot />
  </StrictMode>,
);
