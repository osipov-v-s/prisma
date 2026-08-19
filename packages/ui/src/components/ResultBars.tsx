import type { RankedScore } from "../types";

interface ResultBarsProps {
  title: string;
  subtitle: string;
  scores: RankedScore[] | null;
}

export function ResultBars({ title, subtitle, scores }: ResultBarsProps) {
  return (
    <section className="result-card">
      <div className="result-card__heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className="result-card__sum">Σ 100%</span>
      </div>
      {scores ? (
        <div className="score-list">
          {scores.map((score) => (
            <div className="score-row" key={String(score.type_id)}>
              <div className="score-row__label">
                <span>{score.type_name}</span>
                <strong>{score.percent.toFixed(1)}%</strong>
              </div>
              <div className="score-row__track">
                <span style={{ width: `${Math.max(score.percent, 1)}%` }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-state">Расчёт не сформировал итоговые проценты.</p>
      )}
    </section>
  );
}
