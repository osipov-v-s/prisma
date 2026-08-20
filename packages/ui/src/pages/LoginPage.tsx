import { type FormEvent, useState } from "react";
import { login } from "../api";
import type { Account } from "../types";

interface Props {
  serviceBaseUrl: string;
  connected: boolean;
  connectionError: string | null;
  onLogin(account: Account): void;
}

export function LoginPage({ serviceBaseUrl, connected, connectionError, onLogin }: Props) {
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError(null);
    try { onLogin((await login(serviceBaseUrl, loginName, password)).account); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Не удалось войти"); }
    finally { setLoading(false); }
  }

  return <div className="login-screen">
    <form className="login-card" onSubmit={(event) => void submit(event)}>
      <div className="login-brand"><span className="brand__placeholder">П</span><div><strong>ПРИЗМА</strong><small>исследование предпочтений</small></div></div>
      <h1>Вход в систему</h1>
      <p>Введите учётные данные участника или администратора.</p>
      <label className="field"><span>Логин</span><input autoFocus value={loginName} onChange={(event) => setLoginName(event.target.value)} /></label>
      <label className="field"><span>Пароль</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      {error && <div className="editor-error">{error}</div>}
      {!connected && connectionError && (
        <div className="editor-error">Локальный сервис недоступен: {connectionError}</div>
      )}
      <button className="primary-action" disabled={!connected || loading} type="submit">
        {!connected ? "Подключение к сервису…" : loading ? "Вход…" : "Войти"}
      </button>
      <small className="login-hint">Демонстрация: admin / admin123 или user / user1234</small>
    </form>
  </div>;
}
