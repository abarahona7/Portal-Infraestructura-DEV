"""Controles estructurales para libros XLSX procesados por comandos internos."""

from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, is_zipfile

from django.conf import settings


def validate_xlsx_file(path):
    path = Path(path)
    try:
        absolute = path.absolute()
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError('No fue posible validar el archivo XLSX.') from exc

    if absolute != resolved or path.is_symlink():
        raise ValueError('No se permiten enlaces simbólicos como archivo de importación.')
    if resolved.suffix.lower() != '.xlsx' or not resolved.is_file():
        raise ValueError('El archivo de importación debe ser un XLSX regular.')
    if resolved.stat().st_size > settings.PORTAL_IMPORT_MAX_FILE_BYTES:
        raise ValueError('El archivo XLSX supera el tamaño máximo permitido.')
    if not is_zipfile(resolved):
        raise ValueError('El contenido del archivo no corresponde a un XLSX válido.')

    total_uncompressed = 0
    try:
        with ZipFile(resolved) as archive:
            members = archive.infolist()
            if len(members) > settings.PORTAL_IMPORT_MAX_ZIP_MEMBERS:
                raise ValueError('El XLSX contiene demasiados archivos internos.')
            for member in members:
                member_path = PurePosixPath(member.filename)
                if member_path.is_absolute() or '..' in member_path.parts:
                    raise ValueError('El XLSX contiene una ruta interna no permitida.')
                if member.flag_bits & 0x1:
                    raise ValueError('No se permiten archivos XLSX cifrados.')
                total_uncompressed += member.file_size
                if total_uncompressed > settings.PORTAL_IMPORT_MAX_UNCOMPRESSED_BYTES:
                    raise ValueError('El contenido descomprimido del XLSX supera el límite.')
    except BadZipFile as exc:
        raise ValueError('El contenido del archivo no corresponde a un XLSX válido.') from exc

    return resolved


def validate_workbook_dimensions(workbook):
    for sheet in workbook.worksheets:
        if sheet.max_row > settings.PORTAL_IMPORT_MAX_ROWS:
            raise ValueError(
                f'La hoja {sheet.title} supera el máximo de filas permitido.'
            )
        if sheet.max_column > settings.PORTAL_IMPORT_MAX_COLUMNS:
            raise ValueError(
                f'La hoja {sheet.title} supera el máximo de columnas permitido.'
            )
