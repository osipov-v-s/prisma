import { type FormEvent, useEffect, useState } from "react";
import { createUser, deleteUser, getUsers } from "../api";
import type { Account, UserCreate } from "../types";

interface Props { serviceBaseUrl: string; currentAccount: Account; }
const empty: UserCreate = { login: "", password: "", last_name: "", first_name: "", patronymic: "", roles: ["USER"] };

export function UsersPage({ serviceBaseUrl, currentAccount }: Props) {
  const [users, setUsers] = useState<Account[]>([]);
  const [form, setForm] = useState<UserCreate>(empty);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = () => getUsers(serviceBaseUrl).then(setUsers).catch((caught) => setError(caught.message));
  useEffect(() => { void load(); }, [serviceBaseUrl]);
  async function submit(event: FormEvent) { event.preventDefault(); try { await createUser(serviceBaseUrl, form); setForm(empty); setCreating(false); await load(); } catch (caught) { setError(caught instanceof Error ? caught.message : "Ошибка"); } }
  async function remove(user: Account) { if (!window.confirm(`Удалить ${user.full_name} и все связанные данные?`)) return; try { await deleteUser(serviceBaseUrl, user.id); await load(); } catch (caught) { setError(caught instanceof Error ? caught.message : "Ошибка"); } }
  return <><div className="page-heading"><div><span className="eyebrow">Административный режим</span><h1>Пользователи</h1><p>Учётные записи участников и роли доступа.</p></div><button className="primary-action" onClick={() => setCreating(true)}>+ Новый пользователь</button></div>{error && <div className="editor-error">{error}</div>}
  {creating && <form className="user-form" onSubmit={(event) => void submit(event)}><label className="field"><span>Фамилия</span><input required value={form.last_name} onChange={(e) => setForm({...form,last_name:e.target.value})}/></label><label className="field"><span>Имя</span><input required value={form.first_name} onChange={(e) => setForm({...form,first_name:e.target.value})}/></label><label className="field"><span>Отчество</span><input value={form.patronymic} onChange={(e) => setForm({...form,patronymic:e.target.value})}/></label><label className="field"><span>Логин</span><input required value={form.login} onChange={(e) => setForm({...form,login:e.target.value})}/></label><label className="field"><span>Начальный пароль</span><input minLength={8} required type="password" value={form.password} onChange={(e) => setForm({...form,password:e.target.value})}/></label><label className="field"><span>Роль</span><select value={form.roles[0]} onChange={(e) => setForm({...form,roles:[e.target.value]})}><option value="USER">USER</option><option value="ADMIN">ADMIN</option></select></label><div className="editor-actions"><button className="text-action" onClick={() => setCreating(false)} type="button">Отмена</button><button className="primary-action" type="submit">Создать</button></div></form>}
  <div className="trace-table-wrap"><table className="data-table"><thead><tr><th>ФИО</th><th>Логин</th><th>Роли</th><th>Статус</th><th /></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td>{user.full_name}</td><td>{user.login}</td><td>{user.roles.join(", ")}</td><td>{user.is_active ? "активен" : "отключён"}</td><td><button className="text-action danger" disabled={user.id === currentAccount.id} onClick={() => void remove(user)}>Удалить</button></td></tr>)}</tbody></table></div></>;
}
