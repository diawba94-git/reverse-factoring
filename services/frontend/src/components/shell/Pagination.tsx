type PaginationProps = {
  page: number;
  perPage: number;
  total: number;
  onPageChange: (page: number) => void;
  onPerPageChange: (perPage: number) => void;
};

function pageNumbers(current: number, totalPages: number): (number | "...")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  const set = new Set(
    [1, 2, 3, totalPages - 1, totalPages, current - 1, current, current + 1].filter((p) => p >= 1 && p <= totalPages),
  );
  const sorted = [...set].sort((a, b) => a - b);
  const result: (number | "...")[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) result.push("...");
    result.push(p);
  });
  return result;
}

export function Pagination({ page, perPage, total, onPageChange, onPerPageChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const debut = total === 0 ? 0 : (page - 1) * perPage + 1;
  const fin = Math.min(page * perPage, total);

  return (
    <div className="pagination">
      <span>
        Affichage {debut}-{fin} sur {total}
      </span>
      <div className="pages">
        <button className="page-btn" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          ‹
        </button>
        {pageNumbers(page, totalPages).map((p, i) =>
          p === "..." ? (
            <span className="page-ellipsis" key={`ellipsis-${i}`}>
              …
            </span>
          ) : (
            <button
              key={p}
              className={`page-btn ${p === page ? "active" : ""}`}
              onClick={() => onPageChange(p)}
            >
              {p}
            </button>
          ),
        )}
        <button className="page-btn" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          ›
        </button>
      </div>
      <select className="per-page-select" value={perPage} onChange={(e) => onPerPageChange(Number(e.target.value))}>
        <option value={10}>10 / page</option>
        <option value={25}>25 / page</option>
        <option value={50}>50 / page</option>
      </select>
    </div>
  );
}
