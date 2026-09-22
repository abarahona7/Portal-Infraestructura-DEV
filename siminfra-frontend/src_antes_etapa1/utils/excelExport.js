import * as XLSX from 'xlsx';

const sanitizeFileName = (value) => {
  return String(value || 'exportacion')
    .trim()
    .replace(/[<>:"/\\|?*]/g, '-')
    .replace(/\s+/g, '_');
};

const getColumnWidth = (
  rows,
  key,
  header
) => {
  const values = rows.map((row) => {
    const value = row[key];

    if (value === null || value === undefined) {
      return '';
    }

    return String(value);
  });

  const maxLength = Math.max(
    String(header).length,
    ...values.map((value) => value.length)
  );

  return {
    wch: Math.min(
      Math.max(maxLength + 2, 12),
      45
    )
  };
};

export const exportToExcel = ({
  rows = [],
  columns = [],
  fileName = 'exportacion',
  sheetName = 'Datos',
}) => {
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new Error(
      'No existen registros para exportar.'
    );
  }

  if (
    !Array.isArray(columns) ||
    columns.length === 0
  ) {
    throw new Error(
      'No se definieron columnas para la exportación.'
    );
  }

  const formattedRows = rows.map((row) => {
    const result = {};

    columns.forEach((column) => {
      const value =
        typeof column.value === 'function'
          ? column.value(row)
          : row[column.key];

      result[column.header] =
        value === null ||
        value === undefined ||
        value === ''
          ? ''
          : value;
    });

    return result;
  });

  const worksheet = XLSX.utils.json_to_sheet(
    formattedRows
  );

  worksheet['!cols'] = columns.map(
    (column) => {
      const normalizedRows = rows.map((row) => ({
        [column.key]:
          typeof column.value === 'function'
            ? column.value(row)
            : row[column.key]
      }));

      return getColumnWidth(
        normalizedRows,
        column.key,
        column.header
      );
    }
  );

  const workbook = XLSX.utils.book_new();

  XLSX.utils.book_append_sheet(
    workbook,
    worksheet,
    sheetName.substring(0, 31)
  );

  const today = new Date()
    .toISOString()
    .slice(0, 10);

  XLSX.writeFile(
    workbook,
    `${sanitizeFileName(fileName)}_${today}.xlsx`
  );
};