import { useEffect, useRef, useState } from "react";

import {
  createTestSession,
  getAvailableTests,
  getSession,
  getSessions,
} from "../api";
import { TestRunner } from "../components/test/TestRunner";
import type { AvailableTest, TestSession } from "../types";

interface TestsPageProps {
  serviceBaseUrl: string;
}

export function TestsPage({ serviceBaseUrl }: TestsPageProps) {
  const [tests, setTests] = useState<AvailableTest[]>([]);
  const [session, setSession] = useState<TestSession | null>(null);
  const [unfinished, setUnfinished] = useState<TestSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [startingTestId, setStartingTestId] = useState<string | null>(null);
  const startingTest = useRef(false);

  useEffect(() => {
    void Promise.all([
      getAvailableTests(serviceBaseUrl),
      getSessions(serviceBaseUrl),
    ])
      .then(([available, history]) => {
        setTests(available);
        setUnfinished(history.filter((item) => item.status !== "completed"));
      })
      .catch((caught) => setError(String(caught)));
  }, [serviceBaseUrl]);

  async function startTest(testId: string) {
    // A ref closes the short gap before React applies the disabled state.
    if (startingTest.current) return;
    startingTest.current = true;
    setStartingTestId(testId);
    setError(null);
    try {
      setSession(await createTestSession(serviceBaseUrl, testId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось начать тест");
    } finally {
      startingTest.current = false;
      setStartingTestId(null);
    }
  }

  if (session) {
    return (
      <TestRunner
        initialSession={session}
        onClose={() => {
          setSession(null);
        }}
        serviceBaseUrl={serviceBaseUrl}
      />
    );
  }

  const resumable = unfinished[0];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Пользовательский режим</span>
          <h1>Доступные тесты</h1>
          <p>Активные исследовательские коллекции.</p>
        </div>
      </div>
      {error && <div className="editor-error">{error}</div>}
      {resumable && (
        <section className="resume-panel">
          <div>
            <strong>Есть незавершённое прохождение</strong>
            <small>
              {resumable.collection_name} · сохранено {resumable.main_completed} из{" "}
              {resumable.main_total}
            </small>
          </div>
          <button
            className="secondary-action"
            onClick={() =>
              void getSession(serviceBaseUrl, resumable.id).then(setSession)
            }
            type="button"
          >
            Продолжить
          </button>
        </section>
      )}
      <section className="test-list">
        {tests.map((test) => (
          <article className="test-card" key={test.id}>
            <span className="status-badge">активен</span>
            <h2>{test.name}</h2>
            <p>
              {test.width} типа · глубина {test.depth} · {test.time_mode}
            </p>
            <button
              className="primary-action"
              disabled={startingTestId !== null}
              onClick={() => void startTest(test.id)}
              type="button"
            >
              {startingTestId === test.id ? "Подготовка…" : "Пройти тест"}
            </button>
          </article>
        ))}
      </section>
    </>
  );
}
