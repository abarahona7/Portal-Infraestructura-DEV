"""Tipos válidos para cada sección de Equipos."""

EQUIPMENT_CATEGORY_TYPES = {
    'Notebook': frozenset({'Notebook'}),
    'Celular': frozenset({'Celular'}),
    'Tablet': frozenset({'Tablet'}),
    'Mac': frozenset({'Mac'}),
    'BAM / Router': frozenset({'BAM / Router'}),
    'PERIFERICOS': frozenset({
        'Monitor', 'Adaptador', 'Audífonos', 'Teclado',
        'Mouse', 'Docking', 'Otro Periférico',
    }),
}
