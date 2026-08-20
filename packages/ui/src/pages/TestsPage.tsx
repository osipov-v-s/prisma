import { useEffect, useState } from "react";

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
              onClick={() => {
                void createTestSession(serviceBaseUrl, test.id)
                  .then(setSession)
                  .catch((caught) => setError(caught.message));
              }}
              type="button"
            >
              Пройти тест
            </button>
          </article>
        ))}
      </section>
    </>
  );
}
