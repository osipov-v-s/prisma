import { useEffect, useRef, useState } from "react";
import { presentNext, savePairResponse } from "../../api";
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
  const [reloadVersion, setReloadVersion] = useState(0);
  const loadedItems = useRef(new Set<string>());
  const activePresentation = useRef<number | null>(null);
  const initialLoad = useRef<Promise<TestSession> | null>(null);
  const submitted = useRef(false);

  function displayPair(nextPair: Comparison | null) {
    // Reset readiness before React mounts possibly cached images for the pair.
    activePresentation.current = nextPair?.presentation_index ?? null;
    loadedItems.current.clear();
    submitted.current = false;
    setLoaded(0);
    setStartedAt(null);
    setError(null);
    setPair(nextPair);
  }

  async function prepareNext(current: TestSession) {
    if (current.status === "in_progress") {
      current = await presentNext(serviceBaseUrl, current.id);
    }
    return current;
  }

  useEffect(() => {
    // React StrictMode replays effects in development. Reuse one request so the
    // same cached images cannot be displayed and then reset a second time.
    let active = true;
    initialLoad.current ??= prepareNext(initialSession);
    void initialLoad.current
      .then((current) => {
        if (!active) return;
        setSession(current);
        displayPair(current.next_comparison);
      })
      .catch((caught) => { if (active) showError(caught); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    const presentationIndex = pair?.presentation_index;
    if (loaded !== 2 || presentationIndex == null) return;
    const frame = requestAnimationFrame(() => {
      if (activePresentation.current === presentationIndex) setStartedAt(reactionNow());
    });
    return () => cancelAnimationFrame(frame);
  }, [loaded, pair?.presentation_index]);
  useEffect(() => {
    if (startedAt == null || session.time_mode !== "timeout_skip" || !session.time_limit_ms) return;
    const timer = setTimeout(() => void submit(null, true), session.time_limit_ms);
    return () => clearTimeout(timer);
  }, [startedAt, pair?.presentation_index]);

  function showError(caught: unknown) {
    console.error("[prisma-ui] test runner operation failed", caught);
    setError(caught instanceof Error ? caught.message : "Не удалось сохранить ответ");
  }

  function imageLoaded(presentationIndex: number, itemId: string) {
    if (activePresentation.current !== presentationIndex) return;
    loadedItems.current.add(itemId);
    setLoaded(loadedItems.current.size);
  }

  function imageFailed(presentationIndex: number, itemId: string, imageUrl: string) {
    if (activePresentation.current !== presentationIndex) return;
    console.error("[prisma-ui] stimulus image failed", {
      presentationIndex, itemId, imageUrl,
    });
    setStartedAt(null);
    setError(`Не удалось загрузить изображение пары № ${presentationIndex}.`);
  }

  function retryImages() {
    if (!pair) return;
    activePresentation.current = pair.presentation_index;
    loadedItems.current.clear();
    setLoaded(0);
    setStartedAt(null);
    setError(null);
    setReloadVersion((current) => current + 1);
  }

  async function submit(itemId: string | null, timedOut = false) {
    if (!pair || startedAt == null || submitted.current) return;
    submitted.current = true; setSaving(true); setError(null);
    try {
      const reactionTime = elapsedMilliseconds(startedAt);
      let updated = await savePairResponse(serviceBaseUrl, session.id, pair.presentation_index,
                                           itemId, reactionTime, timedOut);
      setSession(updated);
      if (updated.status === "in_progress") {
        updated = await presentNext(serviceBaseUrl, updated.id); setSession(updated);
      }
      displayPair(updated.next_comparison);
    } catch (caught) { submitted.current = false; showError(caught); }
    finally { setSaving(false); }
  }

  if (session.status === "completed") return <section className="runner-results">
    <div className="page-heading"><div><span className="eyebrow">Процедура завершена</span><h1>{session.collection_name}</h1><p>Все ответы сохранены, аналитика выполнена Python-ядром.</p></div><button className="secondary-action" onClick={onClose}>К списку тестов</button></div>
    <div className="result-grid">
      <ResultBars title="Только выбор" subtitle="Без временного веса" scores={session.analysis?.choice_only.overall ?? null} />
      <ResultBars title="Выбор + время" subtitle="source_v1" scores={session.analysis?.choice_and_time.overall ?? null} />
    </div>
  </section>;

  const progress = session.main_total ? session.main_completed / session.main_total : 0;
  return <section className="test-runner">
    <div className="runner-top"><div><span className="eyebrow">Основная процедура</span><h2>Выберите одно изображение</h2></div><div className="runner-progress"><span>{`${session.main_completed + 1} / ${session.main_total}`}</span><div><i style={{ width: `${progress * 100}%` }} /></div></div></div>
    {error && <div className="editor-error runner-error">
      <span>{error}</span>
      {pair && startedAt == null && (
        <button className="text-action" onClick={retryImages} type="button">Повторить загрузку</button>
      )}
    </div>}
    {pair ? <div className={startedAt == null ? "stimulus-pair is-loading" : "stimulus-pair"}>
      <button disabled={saving || startedAt == null} onClick={() => void submit(pair.left_item_id)} type="button"><img alt="Стимул A" key={`${pair.presentation_index}:${pair.left_item_id}:${reloadVersion}`} onError={() => imageFailed(pair.presentation_index, pair.left_item_id, pair.left_image_url)} onLoad={() => imageLoaded(pair.presentation_index, pair.left_item_id)} src={`${serviceBaseUrl}${pair.left_image_url}?v=${reloadVersion}`} /><span>Выбрать</span></button>
      <div className="stimulus-pair__or">или</div>
      <button disabled={saving || startedAt == null} onClick={() => void submit(pair.right_item_id)} type="button"><img alt="Стимул B" key={`${pair.presentation_index}:${pair.right_item_id}:${reloadVersion}`} onError={() => imageFailed(pair.presentation_index, pair.right_item_id, pair.right_image_url)} onLoad={() => imageLoaded(pair.presentation_index, pair.right_item_id)} src={`${serviceBaseUrl}${pair.right_image_url}?v=${reloadVersion}`} /><span>Выбрать</span></button>
    </div> : <div className="loading-panel">Подготовка пары…</div>}
    <div className="runner-note">{startedAt == null ? "Изображения загружаются; отсчёт ещё не начался" : session.time_mode === "no_limit" ? "Время измеряется без ограничения" : `Лимит: ${session.time_limit_ms! / 1000} с · режим ${session.time_mode}`}</div>
  </section>;
}
