import { ChevronLeft, ChevronRight } from 'lucide-react';

import './Pagination.css';


export default function Pagination({
  page = 1,
  totalPages = 1,
  count = 0,
  pageSize = 50,
  onPageChange,
}) {
  if (count <= pageSize || totalPages <= 1) {
    return null;
  }

  const firstItem = ((page - 1) * pageSize) + 1;
  const lastItem = Math.min(page * pageSize, count);

  return (
    <nav className="portal-pagination" aria-label="Paginación de resultados">
      <span className="portal-pagination-summary">
        Mostrando {firstItem}–{lastItem} de {count}
      </span>

      <div className="portal-pagination-controls">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft size={17} aria-hidden="true" />
          Anterior
        </button>

        <span className="portal-pagination-page">
          Página {page} de {totalPages}
        </span>

        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          Siguiente
          <ChevronRight size={17} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
