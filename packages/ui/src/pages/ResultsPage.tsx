import { useEffect, useMemo, useState } from "react";
import { downloadReport, getSession, getSessions } from "../api";
import { ResultBars } from "../components/ResultBars";
import type { Account, TestSession } from "../types";

interface Props { serviceBaseUrl: string; account: Account; }

export function ResultsPage({ serviceBaseUrl, account }: Props) {
  const [sessions, setSessions] = useState<TestSession[]>([]);
  const [detail, setDetail] = useState<TestSession | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const isAdmin = account.roles.includes("ADMIN");
  useEffect(() => { void getSessions(serviceBaseUrl).then(setSessions).catch((caught) => setError(caught.message)); }, [serviceBaseUrl]);
  const filtered = useMemo(() => sessions.filter((item) => {
    const text = `${item.user_name} ${item.collection_name}`.toLocaleLowerCase();
    return text.includes(query.toLocaleLowerCase()) && (!status || item.status === status);
  }), [sessions, query, status]);

  if (detail) {
    const consistency = detail.analysis?.choice_only.consistency;
    return <><div className="page-heading"><div><span className="eyebrow">Подробности прохождения</span><h1>{detail.collection_name}</h1><p>{detail.user_name} · {new Date(detail.started_at).toLocaleString("ru-RU")}</p></div><div className="page-heading__actions"><button className="secondary-action" onClick={() => void downloadReport(serviceBaseUrl, `/api/v1/sessions/${detail.id}/report.pdf`, `prisma-${detail.id}.pdf`)}>PDF</button><button className="secondary-action" onClick={() => void downloadReport(serviceBaseUrl, `/api/v1/sessions/${detail.id}/report.xlsx`, `prisma-${detail.id}.xlsx`)}>XLSX</button><button className="text-action" onClick={() => setDetail(null)}>Назад</button></div></div>
      <section className="session-facts"><span>Статус <strong>{detail.status}</strong></span><span>Seed <strong>{detail.random_seed}</strong></span><span>Покрытие <strong>{Math.round((detail.analysis?.choice_only.coverage ?? 0) * 100)}%</strong></span><span>Согласованность <strong>{consistency?.zeta == null ? "не применимо" : consistency.zeta.toFixed(3)}</strong></span></section>
      <div className="result-grid"><ResultBars title="Только выбор" subtitle="Без временного веса" scores={detail.analysis?.choice_only.overall ?? null} /><ResultBars title="Выбор + время" subtitle="source_v1" scores={detail.analysis?.choice_and_time.overall ?? null} /></div>
      <section className="trace-table-wrap"><h2>Исходные сравнения</h2><table className="data-table"><thead><tr><th>№</th><th>Уровень</th><th>Тип A</th><th>Тип B</th><th>Выбранный тип</th><th>Время, мс</th><th>Лимит</th><th>Статус</th></tr></thead><tbody>{detail.comparisons?.filter((item) => !item.is_training).map((item) => <tr key={item.presentation_index}><td>{item.presentation_index}</td><td>{item.level_index}</td><td>{item.left_type_name}</td><td>{item.right_type_name}</td><td>{item.selected_type_name ?? "—"}</td><td>{item.reaction_time_ms?.toFixed(2) ?? "—"}</td><td>{item.exceeded_time_limit ? "превышен" : "—"}</td><td>{item.status}</td></tr>)}</tbody></table></section></>;
  }

  return <><div className="page-heading"><div><span className="eyebrow">{isAdmin ? "Административный режим" : "Личная история"}</span><h1>{isAdmin ? "Результаты и отчёты" : "Мои результаты"}</h1><p>Все прохождения сохраняются как отдельная история.</p></div>{isAdmin && <button className="primary-action" onClick={() => void downloadReport(serviceBaseUrl, "/api/v1/admin/sessions.xlsx", "prisma-research-export.xlsx")}>Научная выгрузка XLSX</button>}</div>
  <div className="result-filters"><input placeholder="Пользователь или коллекция" value={query} onChange={(event) => setQuery(event.target.value)} /><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Все статусы</option><option value="completed">Завершён</option><option value="in_progress">В процессе</option><option value="training">Тренировка</option></select></div>
  {error && <div className="editor-error">{error}</div>}
  <div className="trace-table-wrap"><table className="data-table"><thead><tr>{isAdmin && <th>ФИО</th>}<th>Коллекция</th><th>Дата</th><th>Choice only</th><th>Choice + time</th><th>Согласованность</th><th>Статус</th><th /></tr></thead><tbody>{filtered.map((item) => { const first = item.analysis?.choice_only.overall?.[0]; const timed = item.analysis?.choice_and_time.overall?.[0]; const zeta = item.analysis?.choice_only.consistency?.zeta; return <tr key={item.id}>{isAdmin && <td>{item.user_name}</td>}<td>{item.collection_name}</td><td>{new Date(item.started_at).toLocaleDateString("ru-RU")}</td><td>{first ? `${first.type_name}: ${first.percent.toFixed(1)}%` : "—"}</td><td>{timed ? `${timed.type_name}: ${timed.percent.toFixed(1)}%` : "—"}</td><td>{zeta == null ? "—" : zeta.toFixed(2)}</td><td>{item.status}</td><td><button className="text-action" onClick={() => void getSession(serviceBaseUrl, item.id, true).then(setDetail)}>Открыть</button></td></tr>; })}</tbody></table></div></>;
}
