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
  const [selected, setSelected] = useState<AvailableTest | null>(null);
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
          setSelected(null);
        }}
        serviceBaseUrl={serviceBaseUrl}
      />
    );
  }

  if (selected) {
    return (
      <Instruction
        error={error}
        onBack={() => setSelected(null)}
        onStart={() => {
          void createTestSession(serviceBaseUrl, selected.id)
            .then(setSession)
            .catch((caught) => setError(caught.message));
        }}
        test={selected}
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
              onClick={() => setSelected(test)}
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

interface InstructionProps {
  test: AvailableTest;
  error: string | null;
  onBack(): void;
  onStart(): void;
}

function Instruction({ test, error, onBack, onStart }: InstructionProps) {
  const comparisonCount = (test.depth * test.width * (test.width - 1)) / 2;
  const timeLabel =
    test.time_mode === "no_limit" ? "без лимита" : `${test.time_limit_ms! / 1000} с`;

  return (
    <section className="instruction-card">
      <span className="eyebrow">Инструкция</span>
      <h1>{test.name}</h1>
      <p>
        В каждой паре выберите изображение, которое вам ближе. Правильных и
        неправильных ответов нет. Сначала будут три тренировочных сравнения;
        они не входят в расчёт.
      </p>
      <dl>
        <div><dt>Типов</dt><dd>{test.width}</dd></div>
        <div><dt>Изображений каждого типа</dt><dd>{test.depth}</dd></div>
        <div><dt>Сравнений</dt><dd>{comparisonCount}</dd></div>
        <div><dt>Время</dt><dd>{timeLabel}</dd></div>
      </dl>
      {error && <div className="editor-error">{error}</div>}
      <div className="editor-actions">
        <button className="secondary-action" onClick={onBack} type="button">Назад</button>
        <button className="primary-action" onClick={onStart} type="button">
          Перейти к тренировке
        </button>
      </div>
    </section>
  );
}
