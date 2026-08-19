import { useEffect, useRef, useState } from "react";
import { presentNext, savePairResponse, startMainTest } from "../../api";
import { ResultBars } from "../ResultBars";
import type { Comparison, TestSession } from "../../types";
import { elapsedMilliseconds, reactionNow } from "../../timing/reactionTimer";

interface Props { serviceBaseUrl: string; initialSession: TestSession; onClose(): void; }

export function TestRunner({ serviceBaseUrl, initialSession, onClose }: Props) {
  const [session, setSession] = useState(initialSession);
  const [pair, setPair] = useState<Comparison | null>(null);
  const [loaded, setLoaded] = useState(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadedItems = useRef(new Set<string>());
  const submitted = useRef(false);

  async function loadNext(current = session) {
    if (current.status === "training" || current.status === "in_progress") {
      current = await presentNext(serviceBaseUrl, current.id);
      setSession(current);
    }
    setPair(current.next_comparison);
  }

  useEffect(() => { void loadNext(initialSession).catch(showError); }, []);
  useEffect(() => {
    loadedItems.current.clear(); submitted.current = false; setLoaded(0); setStartedAt(null);
  }, [pair?.presentation_index]);
  useEffect(() => {
    if (loaded === 2) {
      const frame = requestAnimationFrame(() => setStartedAt(reactionNow()));
      return () => cancelAnimationFrame(frame);
    }
  }, [loaded]);
  useEffect(() => {
    if (startedAt == null || session.time_mode !== "timeout_skip" || !session.time_limit_ms) return;
    const timer = setTimeout(() => void submit(null, true), session.time_limit_ms);
    return () => clearTimeout(timer);
  }, [startedAt, pair?.presentation_index]);

  function showError(caught: unknown) {
    setError(caught instanceof Error ? caught.message : "Не удалось сохранить ответ");
  }

  function imageLoaded(itemId: string) {
    loadedItems.current.add(itemId); setLoaded(loadedItems.current.size);
  }

  async function submit(itemId: string | null, timedOut = false) {
    if (!pair || startedAt == null || submitted.current) return;
    submitted.current = true; setSaving(true); setError(null);
    try {
      const reactionTime = elapsedMilliseconds(startedAt);
      let updated = await savePairResponse(serviceBaseUrl, session.id, pair.presentation_index,
                                           itemId, reactionTime, timedOut);
      setSession(updated);
      if (updated.status === "training" || updated.status === "in_progress") {
        updated = await presentNext(serviceBaseUrl, updated.id); setSession(updated);
      }
      setPair(updated.next_comparison);
    } catch (caught) { submitted.current = false; showError(caught); }
    finally { setSaving(false); }
  }

  async function beginMain() {
    try {
      let updated = await startMainTest(serviceBaseUrl, session.id);
      updated = await presentNext(serviceBaseUrl, updated.id);
      setSession(updated); setPair(updated.next_comparison);
    } catch (caught) { showError(caught); }
  }

  if (session.status === "ready") return <section className="runner-card runner-transition">
    <span className="eyebrow">Тренировка завершена</span><h1>Готовы начать основной тест?</h1>
    <p>Дальнейшие ответы войдут в математическую обработку. Выбирайте изображение, которое кажется предпочтительнее.</p>
    <button className="primary-action" onClick={() => void beginMain()} type="button">Начать основной тест</button>
  </section>;

  if (session.status === "completed") return <section className="runner-results">
    <div className="page-heading"><div><span className="eyebrow">Процедура завершена</span><h1>{session.collection_name}</h1><p>Все ответы сохранены, аналитика выполнена Python-ядром.</p></div><button className="secondary-action" onClick={onClose}>К списку тестов</button></div>
    <div className="result-grid">
      <ResultBars title="Только выбор" subtitle="Без временного веса" scores={session.analysis?.choice_only.overall ?? null} />
      <ResultBars title="Выбор + время" subtitle="source_v1" scores={session.analysis?.choice_and_time.overall ?? null} />
    </div>
  </section>;

  const progress = pair?.is_training ? session.training_completed / session.training_total : session.main_completed / session.main_total;
  return <section className="test-runner">
    <div className="runner-top"><div><span className="eyebrow">{pair?.is_training ? "Тренировочный режим" : "Основная процедура"}</span><h2>Выберите одно изображение</h2></div><div className="runner-progress"><span>{pair?.is_training ? `${session.training_completed + 1} / ${session.training_total}` : `${session.main_completed + 1} / ${session.main_total}`}</span><div><i style={{ width: `${progress * 100}%` }} /></div></div></div>
    {error && <div className="editor-error">{error}</div>}
    {pair ? <div className={startedAt == null ? "stimulus-pair is-loading" : "stimulus-pair"}>
      <button disabled={saving || startedAt == null} onClick={() => void submit(pair.left_item_id)} type="button"><img alt="Стимул A" onLoad={() => imageLoaded(pair.left_item_id)} src={`${serviceBaseUrl}${pair.left_image_url}`} /><span>Выбрать</span></button>
      <div className="stimulus-pair__or">или</div>
      <button disabled={saving || startedAt == null} onClick={() => void submit(pair.right_item_id)} type="button"><img alt="Стимул B" onLoad={() => imageLoaded(pair.right_item_id)} src={`${serviceBaseUrl}${pair.right_image_url}`} /><span>Выбрать</span></button>
    </div> : <div className="loading-panel">Подготовка пары…</div>}
    <div className="runner-note">{startedAt == null ? "Изображения загружаются; отсчёт ещё не начался" : session.time_mode === "no_limit" ? "Время измеряется без ограничения" : `Лимит: ${session.time_limit_ms! / 1000} с · режим ${session.time_mode}`}</div>
  </section>;
}
