import { beforeEach, describe, expect, it, vi } from 'vitest';
import { exportToExcel } from './excelExport';

const captured = vi.hoisted(() => ({ workbook: null, fileName: null }));

vi.mock('xlsx', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    writeFile: (workbook, fileName) => {
      captured.workbook = workbook;
      captured.fileName = fileName;
    },
  };
});

describe('Exportación Excel', () => {
  beforeEach(() => {
    captured.workbook = null;
    captured.fileName = null;
  });

  it('conserva columnas, filas y acentos en la hoja generada', async () => {
    await exportToExcel({
      rows: [{ nombre: 'Álvaro Muñoz', departamento: 'Tecnología' }],
      columns: [
        { key: 'nombre', header: 'Nombre' },
        { key: 'departamento', header: 'Área' },
      ],
      fileName: 'usuarios / QA',
      sheetName: 'Usuarios',
    });

    expect(captured.workbook.SheetNames).toEqual(['Usuarios']);
    const sheet = captured.workbook.Sheets.Usuarios;
    expect(sheet.A1.v).toBe('Nombre');
    expect(sheet.B1.v).toBe('Área');
    expect(sheet.A2.v).toBe('Álvaro Muñoz');
    expect(sheet.B2.v).toBe('Tecnología');
    expect(captured.fileName).toMatch(/^usuarios_-_QA_\d{4}-\d{2}-\d{2}\.xlsx$/);
  });

  it('evita descargar una hoja sin registros', async () => {
    await expect(exportToExcel({
      rows: [], columns: [{ key: 'nombre', header: 'Nombre' }],
    })).rejects.toThrow('No existen registros para exportar.');
    expect(captured.workbook).toBeNull();
  });
});
