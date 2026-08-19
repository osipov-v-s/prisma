import {
  ChartIcon,
  GridIcon,
  SettingsIcon,
  UsersIcon,
} from "../Icons";
import type { Account } from "../../types";

export type AppSection = "collections" | "tests" | "results" | "users" | "settings";

interface AppHeaderProps {
  activeSection: AppSection;
  runtimeLabel: string;
  onNavigate(section: AppSection): void;
  account: Account;
  onLogout(): void;
}

const adminNavigation = [
  { id: "collections" as const, label: "Коллекции", icon: GridIcon },
  { id: "results" as const, label: "Результаты", icon: ChartIcon },
  { id: "users" as const, label: "Пользователи", icon: UsersIcon },
  { id: "settings" as const, label: "Настройки", icon: SettingsIcon },
];
const userNavigation = [
  { id: "tests" as const, label: "Доступные тесты", icon: GridIcon },
  { id: "results" as const, label: "Мои результаты", icon: ChartIcon },
];

export function AppHeader({
  activeSection,
  runtimeLabel,
  onNavigate,
  account,
  onLogout,
}: AppHeaderProps) {
  const navigation = account.roles.includes("ADMIN") ? adminNavigation : userNavigation;
  return (
    <header className="topbar">
      <div className="brand" aria-label="ПРИЗМА">
        <span className="brand__placeholder">П</span>
        <span>
          <strong>ПРИЗМА</strong>
          <small>исследование предпочтений</small>
        </span>
      </div>
      <nav className="main-nav" aria-label="Основная навигация">
        {navigation.map(({ id, label, icon: Icon }) => (
          <button
            className={
              activeSection === id ? "main-nav__item is-active" : "main-nav__item"
            }
            key={id}
            onClick={() => onNavigate(id)}
            type="button"
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="profile-chip">
        <span className="profile-chip__avatar">{account.full_name.slice(0, 1)}</span>
        <span>
          <strong>{account.full_name}</strong>
          <small>{account.roles.join(" · ")} · {runtimeLabel}</small>
        </span>
        <button className="profile-chip__logout" onClick={onLogout} type="button">Выйти</button>
      </div>
    </header>
  );
}
