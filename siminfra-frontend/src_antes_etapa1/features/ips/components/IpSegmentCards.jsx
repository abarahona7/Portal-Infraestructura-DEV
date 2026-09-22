import {
  Network,
  CheckCircle2,
  LockKeyhole
} from 'lucide-react';

import {
  IP_SEGMENTS,
  getIpSegmentStats,
} from '../../../utils/ipHelpers';

import './IpSegmentCards.css';

export default function IpSegmentCards({
  ips = [],
  selectedSegment,
  onSelectSegment,
}) {
  return (
    <section className="ip-segments-section">
      <div className="ip-segments-heading">
        <div>
          <span className="ip-segments-eyebrow">
            Segmentos de red
          </span>

          <h2>
            Selecciona un segmento
          </h2>
        </div>

        {selectedSegment && (
          <button
            type="button"
            className="ip-segments-clear"
            onClick={() =>
              onSelectSegment('')
            }
          >
            Ver todos
          </button>
        )}
      </div>

      <div className="ip-segments-grid">
        {IP_SEGMENTS.map((segment) => {
          const stats =
            getIpSegmentStats(
              ips,
              segment.id
            );

          const isSelected =
            selectedSegment ===
            segment.id;

          return (
            <button
              key={segment.id}
              type="button"
              className={`ip-segment-card ${
                isSelected
                  ? 'ip-segment-card-selected'
                  : ''
              }`}
              onClick={() =>
                onSelectSegment(
                  isSelected
                    ? ''
                    : segment.id
                )
              }
            >
              <div className="ip-segment-card-top">
                <div className="ip-segment-icon">
                  <Network size={20} />
                </div>

                <div className="ip-segment-total">
                  {stats.total}
                  <span>
                    IP{stats.total === 1
                      ? ''
                      : 's'}
                  </span>
                </div>
              </div>

              <div className="ip-segment-main">
                <strong>
                  {segment.label}
                </strong>

                <span>
                  {segment.network}
                </span>
              </div>

              <div className="ip-segment-stats">
                <div className="ip-segment-stat">
                  <CheckCircle2
                    size={14}
                  />

                  <span>
                    {stats.libres} libres
                  </span>
                </div>

                <div className="ip-segment-stat">
                  <LockKeyhole
                    size={14}
                  />

                  <span>
                    {stats.reservadas}
                    {' '}
                    reservadas
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}