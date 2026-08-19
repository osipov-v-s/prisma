import { useMemo } from "react";
import { measureTimerResolution } from "../timing/reactionTimer";

export function SettingsPage() {
  const resolution = useMemo(() => measureTimerResolution(), []);
  return <><div className="page-heading"><div><span className="eyebrow">Локальная конфигурация</span><h1>Настройки</h1><p>Диагностика Desktop-среды без изменения научного baseline.</p></div></div><section className="settings-grid"><article className="summary-card"><span>Таймер реакции</span><strong>{resolution == null ? "не определена" : `${resolution.toFixed(4)} мс`}</strong><small>минимальный наблюдавшийся положительный шаг performance.now()</small></article><article className="summary-card"><span>Автосохранение</span><strong>после каждого ответа</strong><small>SQLite-транзакция до следующего предъявления</small></article><article className="summary-card"><span>Аналитика</span><strong>Python Core</strong><small>формулы не дублируются в TypeScript</small></article></section><div className="activation-hints">Измерение показывает разрешение таймера в текущей среде, но само по себе не является метрологической гарантией точности 1 мс.</div></>;
}
