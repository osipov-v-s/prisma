import { useEffect, useState } from "react";

import { getHealth, logout } from "./api";
import { AppFooter } from "./components/layout/AppFooter";
import { AppHeader, type AppSection } from "./components/layout/AppHeader";
import { CollectionsPage } from "./pages/CollectionsPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { ResultsPage } from "./pages/ResultsPage";
import { LoginPage } from "./pages/LoginPage";
import { TestsPage } from "./pages/TestsPage";
import { UsersPage } from "./pages/UsersPage";
import { SettingsPage } from "./pages/SettingsPage";
import type { Account } from "./types";
import type { HealthResponse } from "./types";

interface PrismaAppProps {
  serviceBaseUrl: string;
  runtimeLabel?: string;
}

export function PrismaApp({
  serviceBaseUrl,
  runtimeLabel = "Desktop",
}: PrismaAppProps) {
  const [section, setSection] = useState<AppSection>("collections");
  const [account, setAccount] = useState<Account | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let active = true;
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function connect() {
      attempts += 1;
      try {
        const response = await getHealth(serviceBaseUrl);
        if (active) setHealth(response);
      } catch {
        if (active && attempts < 30) timer = setTimeout(connect, 500);
      }
    }

    void connect();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [serviceBaseUrl]);

  if (!account) {
    return <LoginPage connected={Boolean(health)} onLogin={(loggedIn) => {
      setAccount(loggedIn); setSection(loggedIn.roles.includes("ADMIN") ? "collections" : "tests");
    }} serviceBaseUrl={serviceBaseUrl} />;
  }

  return (
    <div className="app-shell">
      <AppHeader
        activeSection={section}
        onNavigate={setSection}
        runtimeLabel={runtimeLabel}
        account={account}
        onLogout={() => void logout(serviceBaseUrl).finally(() => setAccount(null))}
      />
      <main className="workspace">
        {section === "collections" && (
          <CollectionsPage health={health} serviceBaseUrl={serviceBaseUrl} />
        )}
        {section === "tests" && <TestsPage serviceBaseUrl={serviceBaseUrl} />}
        {section === "results" && <ResultsPage account={account} serviceBaseUrl={serviceBaseUrl} />}
        {section === "users" && <UsersPage currentAccount={account} serviceBaseUrl={serviceBaseUrl} />}
        {section === "settings" && <SettingsPage />}
      </main>
      <AppFooter />
    </div>
  );
}
