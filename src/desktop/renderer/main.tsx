import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { PrismaApp } from "@prisma/ui";
import "@prisma/ui/styles.css";

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
