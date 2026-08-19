import { mediaUrl } from "../../api";
import type { CollectionCell } from "../../types";

interface ImageCellProps {
  cell: CollectionCell;
  pendingFile?: File;
  serviceBaseUrl: string;
  disabled: boolean;
  onFile(file: File): void;
}

export function ImageCell({
  cell,
  pendingFile,
  serviceBaseUrl,
  disabled,
  onFile,
}: ImageCellProps) {
  const storedUrl = mediaUrl(serviceBaseUrl, cell.image_url);

  function acceptDroppedFile(files: FileList | null) {
    const file = files?.item(0);
    if (file) onFile(file);
  }

  return (
    <label
      className={
        pendingFile
          ? "image-cell has-pending"
          : storedUrl
            ? "image-cell is-filled"
            : "image-cell"
      }
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        if (!disabled) acceptDroppedFile(event.dataTransfer.files);
      }}
    >
      {storedUrl && !pendingFile ? (
        <img src={storedUrl} alt={`Уровень ${cell.level_index}`} />
      ) : (
        <span>
          <strong>{pendingFile ? pendingFile.name : "+"}</strong>
          <small>{pendingFile ? "будет загружено" : "добавить"}</small>
        </span>
      )}
      <input
        accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml"
        disabled={disabled}
        onChange={(event) => acceptDroppedFile(event.target.files)}
        type="file"
      />
    </label>
  );
}
