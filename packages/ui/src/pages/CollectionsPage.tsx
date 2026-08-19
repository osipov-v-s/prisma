import { useCallback, useEffect, useState } from "react";

import { activateCollection, deactivateCollection, getCollections } from "../api";
import { CollectionCard } from "../components/collections/CollectionCard";
import { CollectionEditor } from "../components/collections/CollectionEditor";
import type { CollectionRecord, HealthResponse } from "../types";

interface CollectionsPageProps {
  health: HealthResponse | null;
  serviceBaseUrl: string;
}

export function CollectionsPage({ health, serviceBaseUrl }: CollectionsPageProps) {
  const [collections, setCollections] = useState<CollectionRecord[]>([]);
  const [editing, setEditing] = useState<CollectionRecord | null | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!health) return;
    setLoading(true);
    try {
      setCollections(await getCollections(serviceBaseUrl));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить коллекции");
    } finally {
      setLoading(false);
    }
  }, [health, serviceBaseUrl]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleActive(collection: CollectionRecord) {
    try {
      const updated = collection.is_active
        ? await deactivateCollection(serviceBaseUrl, collection.id)
        : await activateCollection(serviceBaseUrl, collection.id);
      setCollections((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setError(null);
    } catch (caught) {
      setEditing(collection);
      setError(caught instanceof Error ? caught.message : "Не удалось изменить статус");
    }
  }

  if (editing !== undefined) {
    return (
      <CollectionEditor
        collection={editing}
        key={`${editing?.id ?? "new"}:${editing?.updated_at ?? "draft"}`}
        onClose={() => setEditing(undefined)}
        onSaved={(saved) => {
          setEditing(saved);
          void load();
        }}
        serviceBaseUrl={serviceBaseUrl}
      />
    );
  }

  const activeCount = collections.filter((item) => item.is_active).length;
  const draftCount = collections.length - activeCount;

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Административный режим</span>
          <h1>Коллекции исследований</h1>
          <p>Создание типов, заполнение сетки изображений и управление публикацией.</p>
        </div>
        <div className="page-heading__actions">
          <div className={health ? "service-state is-online" : "service-state"}>
            <span />
            {health ? "SQLite и API подключены" : "Подключение…"}
          </div>
          <button className="primary-action" onClick={() => setEditing(null)} type="button">
            + Новая коллекция
          </button>
        </div>
      </div>

      <section className="summary-grid summary-grid--collections">
        <article className="summary-card"><span>Всего коллекций</span><strong>{collections.length}</strong><small>в локальной базе</small></article>
        <article className="summary-card"><span>Активные</span><strong>{activeCount}</strong><small>видимы пользователю</small></article>
        <article className="summary-card"><span>Черновики</span><strong>{draftCount}</strong><small>можно заполнять постепенно</small></article>
        <article className="summary-card summary-card--version"><span>Хранилище</span><strong>SQLite + SQLAlchemy</strong><small>готово к PostgreSQL</small></article>
      </section>

      {error && <div className="editor-error" role="alert">{error}</div>}
      {loading ? (
        <div className="loading-panel">Загрузка коллекций…</div>
      ) : (
        <section className="collection-list">
          {collections.map((collection) => (
            <CollectionCard
              collection={collection}
              key={collection.id}
              onEdit={() => setEditing(collection)}
              onToggleActive={() => void toggleActive(collection)}
            />
          ))}
        </section>
      )}
    </>
  );
}
