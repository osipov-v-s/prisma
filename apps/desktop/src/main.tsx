import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

import { PrismaApp } from "@prisma/ui";
import "@prisma/ui/styles.css";

const DEFAULT_SERVICE_URL = "http://127.0.0.1:8765";

function DesktopRoot() {
  const [serviceBaseUrl, setServiceBaseUrl] = useState(DEFAULT_SERVICE_URL);

  useEffect(() => {
    if (window.prismaDesktop) {
      void window.prismaDesktop.getServiceBaseUrl().then(setServiceBaseUrl);
    }
  }, []);

  return <PrismaApp serviceBaseUrl={serviceBaseUrl} runtimeLabel="Desktop" />;
}

const root = document.getElementById("root");
if (!root) throw new Error("Root element was not found");

createRoot(root).render(
  <StrictMode>
    <DesktopRoot />
  </StrictMode>,
);
