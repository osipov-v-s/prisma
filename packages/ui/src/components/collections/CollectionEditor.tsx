import { useMemo, useState } from "react";

import {
  activateCollection,
  createCollection,
  updateCollection,
  uploadCollectionImage,
} from "../../api";
import type {
  CollectionCell,
  CollectionRecord,
  CollectionWrite,
  TimeMode,
} from "../../types";
import { ImageCell } from "./ImageCell";

interface CollectionEditorProps {
  collection: CollectionRecord | null;
  serviceBaseUrl: string;
  onClose(): void;
  onSaved(collection: CollectionRecord): void;
}

const DEPTH_OPTIONS = [1, 3, 5, 7, 9];

function emptyCell(levelIndex: number): CollectionCell {
  return {
    item_id: null,
    level_index: levelIndex,
    image_path: null,
    image_url: null,
  };
}

export function CollectionEditor({
  collection,
  serviceBaseUrl,
  onClose,
  onSaved,
}: CollectionEditorProps) {
  const [name, setName] = useState(collection?.name ?? "Новая коллекция");
  const [width, setWidth] = useState(collection?.width ?? 4);
  const [depth, setDepth] = useState(collection?.depth ?? 5);
  const [timeMode, setTimeMode] = useState<TimeMode>(
    collection?.time_mode ?? "timeout_mark",
  );
  const [timeLimit, setTimeLimit] = useState(collection?.time_limit_ms ?? 5000);
  const [typeNames, setTypeNames] = useState<string[]>(
    Array.from({ length: collection?.width ?? 4 }, (_, index) =>
      collection?.rows[index]?.type_name ?? "",
    ),
  );
  const [pendingFiles, setPendingFiles] = useState<Map<string, File>>(new Map());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cells = useMemo(
    () =>
      Array.from({ length: width }, (_, rowIndex) =>
        Array.from({ length: depth }, (_, levelIndex) =>
          collection?.rows[rowIndex]?.cells[levelIndex] ?? emptyCell(levelIndex + 1),
        ),
      ),
    [collection, depth, width],
  );

  function changeWidth(nextWidth: number) {
    setWidth(nextWidth);
    setTypeNames((current) =>
      Array.from({ length: nextWidth }, (_, index) => current[index] ?? ""),
    );
  }

  function payload(): CollectionWrite {
    return {
      name: name.trim() || "Без названия",
      width,
      depth,
      time_mode: timeMode,
      time_limit_ms: timeMode === "no_limit" ? null : timeLimit,
      rows: typeNames.map((typeName, index) => ({
        row_index: index + 1,
        type_name: typeName,
      })),
    };
  }

  async function save(activateAfterSave = false) {
    setSaving(true);
    setError(null);
    try {
      let saved = collection
        ? await updateCollection(serviceBaseUrl, collection.id, payload())
        : await createCollection(serviceBaseUrl, payload());

      // Configuration is saved first because image slots require persisted types.
      for (const [key, file] of pendingFiles) {
        const [rowIndex, levelIndex] = key.split(":").map(Number);
        if (!rowIndex || !levelIndex) continue;
        saved = await uploadCollectionImage(
          serviceBaseUrl,
          saved.id,
          rowIndex,
          levelIndex,
          file,
        );
      }
      if (activateAfterSave) {
        saved = await activateCollection(serviceBaseUrl, saved.id);
      }
      setPendingFiles(new Map());
      onSaved(saved);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось сохранить коллекцию");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="editor-panel">
      <div className="editor-panel__header">
        <div>
          <span className="eyebrow">Редактор коллекции</span>
          <h1>{collection ? collection.name : "Новая коллекция"}</h1>
          <p>Черновик можно сохранить неполным. Активация требует заполнить всю сетку.</p>
        </div>
        <button className="text-action" onClick={onClose} type="button">Закрыть</button>
      </div>

      <div className="editor-settings">
        <label className="field field--wide">
          <span>Название</span>
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="field">
          <span>Количество типов</span>
          <input
            max={20}
            min={2}
            onChange={(event) => changeWidth(Number(event.target.value))}
            type="number"
            value={width}
          />
        </label>
        <label className="field">
          <span>Изображений на тип</span>
          <select value={depth} onChange={(event) => setDepth(Number(event.target.value))}>
            {DEPTH_OPTIONS.map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Режим времени</span>
          <select value={timeMode} onChange={(event) => setTimeMode(event.target.value as TimeMode)}>
            <option value="timeout_skip">Автопропуск</option>
            <option value="timeout_mark">Отметить превышение</option>
            <option value="no_limit">Без ограничения</option>
          </select>
        </label>
        <label className="field">
          <span>Лимит, мс</span>
          <input
            disabled={timeMode === "no_limit"}
            min={1}
            onChange={(event) => setTimeLimit(Number(event.target.value))}
            type="number"
            value={timeLimit}
          />
        </label>
      </div>

      <div className="stimulus-grid-wrap">
        <div
          className="stimulus-grid"
          style={{ gridTemplateColumns: `220px repeat(${depth}, minmax(112px, 1fr))` }}
        >
          <div className="stimulus-grid__corner">Тип / уровень</div>
          {Array.from({ length: depth }, (_, index) => (
            <div className="stimulus-grid__level" key={index}>Уровень {index + 1}</div>
          ))}
          {Array.from({ length: width }, (_, rowIndex) => (
            <div className="stimulus-grid__row" key={rowIndex}>
              <label className="type-field">
                <span>Строка {rowIndex + 1}</span>
                <input
                  onChange={(event) =>
                    setTypeNames((current) =>
                      current.map((value, index) =>
                        index === rowIndex ? event.target.value : value,
                      ),
                    )
                  }
                  placeholder="Например, Врач"
                  value={typeNames[rowIndex] ?? ""}
                />
              </label>
              {cells[rowIndex]?.map((cell) => {
                const key = `${rowIndex + 1}:${cell.level_index}`;
                return (
                  <ImageCell
                    cell={cell}
                    disabled={!typeNames[rowIndex]?.trim()}
                    key={key}
                    onFile={(file) =>
                      setPendingFiles((current) => new Map(current).set(key, file))
                    }
                    pendingFile={pendingFiles.get(key)}
                    serviceBaseUrl={serviceBaseUrl}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {error && <div className="editor-error" role="alert">{error}</div>}
      {collection && !collection.activation.can_activate && (
        <div className="activation-hints">
          <strong>До активации:</strong>
          {collection.activation.errors.map((message) => <span key={message}>{message}</span>)}
        </div>
      )}

      <div className="editor-actions">
        <button className="secondary-action" disabled={saving} onClick={() => void save()} type="button">
          {saving ? "Сохранение…" : "Сохранить черновик"}
        </button>
        <button className="primary-action" disabled={saving || depth < 5} onClick={() => void save(true)} type="button">
          Сохранить и активировать
        </button>
      </div>
    </section>
  );
}
