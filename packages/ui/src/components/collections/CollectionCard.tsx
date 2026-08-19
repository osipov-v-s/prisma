import type { CollectionRecord } from "../../types";

interface CollectionCardProps {
  collection: CollectionRecord;
  onEdit(): void;
  onToggleActive(): void;
}

export function CollectionCard({
  collection,
  onEdit,
  onToggleActive,
}: CollectionCardProps) {
  const filled = collection.rows.reduce(
    (total, row) => total + row.cells.filter((cell) => cell.image_path).length,
    0,
  );
  const total = collection.width * collection.depth;

  return (
    <article className="database-collection-card">
      <div className="database-collection-card__top">
        <span className={collection.is_active ? "status-badge" : "status-badge is-draft"}>
          {collection.is_active ? "Активна" : "Черновик"}
        </span>
        <span className="collection-id">{collection.id.slice(0, 12)}</span>
      </div>
      <h2>{collection.name}</h2>
      <p>
        {collection.width} типа · {collection.depth} изображений на тип · {filled}/{total} ячеек
      </p>
      <div className="collection-progress">
        <span style={{ width: `${total ? (filled / total) * 100 : 0}%` }} />
      </div>
      <div className="database-collection-card__actions">
        <button className="secondary-action" onClick={onEdit} type="button">
          Открыть редактор
        </button>
        <button className="text-action" onClick={onToggleActive} type="button">
          {collection.is_active ? "Деактивировать" : "Активировать"}
        </button>
      </div>
    </article>
  );
}
