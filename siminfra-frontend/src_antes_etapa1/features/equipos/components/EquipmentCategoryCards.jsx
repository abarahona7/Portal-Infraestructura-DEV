import {
  Laptop,
  Smartphone,
  Tablet,
  Monitor,
  Wifi,
  Keyboard,
} from 'lucide-react';

import './EquipmentCategoryCards.css';

const PERIPHERAL_TYPES = [
  'Monitor',
  'Adaptador',
  'Audífonos',
  'Teclado',
  'Mouse',
  'Docking',
  'Otro Periférico',
];

export default function EquipmentCategoryCards({
  equipos = [],
  selectedCategory,
  onSelectCategory,
  formatEquipmentType,
}) {
  const categories = [
    {
      value: 'Notebook',
      label: 'Notebook',
      description: 'Equipos portátiles de distintas marcas y modelos.',
      icon: Laptop,
    },
    {
      value: 'Celular',
      label: 'Celular',
      description: 'Smartphones corporativos.',
      icon: Smartphone,
    },
    {
      value: 'Tablet',
      label: 'Tablet',
      description: 'Tablets y dispositivos móviles.',
      icon: Tablet,
    },
    {
      value: 'Mac',
      label: 'Mac',
      description: 'Equipos Apple y estaciones de trabajo.',
      icon: Monitor,
    },
    {
      value: 'BAM / Router',
      label: 'BAM / Router',
      description: 'Equipos de conectividad y red.',
      icon: Wifi,
    },
    {
      value: 'PERIFERICOS',
      label: 'Periféricos',
      description: 'Monitores, adaptadores, audífonos y accesorios.',
      icon: Keyboard,
    },
  ];

  const getCategoryCount = (category) => {
    if (category === 'PERIFERICOS') {
      return equipos.filter((equipo) => {
        const tipo = formatEquipmentType(equipo.tipo);

        return PERIPHERAL_TYPES.includes(tipo);
      }).length;
    }

    return equipos.filter((equipo) => {
      const tipo = formatEquipmentType(equipo.tipo);

      return tipo === category;
    }).length;
  };

  return (
    <section className="equipment-category-section">
      <div className="equipment-category-heading">
        <div>
          <h2>Selecciona una categoría para ver los equipos</h2>

          <p>
            Organiza y administra los equipos de Infraestructura TI
            según su tipo.
          </p>
        </div>

        {selectedCategory && (
          <button
            type="button"
            className="equipment-category-show-all"
            onClick={() => onSelectCategory('')}
          >
            Ocultar resultados
          </button>
        )}
      </div>

      <div className="equipment-category-grid">
        {categories.map((category) => {
          const Icon = category.icon;
          const count = getCategoryCount(category.value);
          const active =
            selectedCategory === category.value;

          return (
            <button
              key={category.value}
              type="button"
              className={`equipment-category-card ${
                active ? 'is-active' : ''
              }`}
              onClick={() =>
                onSelectCategory(category.value)
              }
            >
              <div className="equipment-category-icon">
                <Icon size={25} />
              </div>

              <div className="equipment-category-content">
                <span className="equipment-category-name">
                  {category.label}
                </span>

                <div className="equipment-category-count">
                  <strong>{count}</strong>
                  <span>
                    {count === 1 ? ' equipo' : ' equipos'}
                  </span>
                </div>

                <p>{category.description}</p>
              </div>

              <span className="equipment-category-action">
                Ver equipos →
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}