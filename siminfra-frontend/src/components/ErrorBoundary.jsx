import { Component } from 'react';

import { setAccessToken } from '../api/client';


export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch() {
    setAccessToken(null);
    try {
      sessionStorage.removeItem('portal-infra-ti-tab-session-active');
    } catch {
      // La pantalla segura sigue disponible sin sessionStorage.
    }
  }

  render() {
    if (!this.state.failed) {
      return this.props.children;
    }

    return (
      <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '24px', background: '#f5f8fc' }}>
        <section style={{ maxWidth: '460px', padding: '28px', border: '1px solid #d7e1ef', borderRadius: '14px', background: '#fff', boxShadow: '0 12px 30px rgba(15, 35, 65, 0.08)' }}>
          <h1 style={{ margin: '0 0 10px', fontSize: '22px', color: '#10213f' }}>No fue posible mostrar el portal</h1>
          <p style={{ margin: '0 0 20px', color: '#526581', lineHeight: 1.5 }}>
            La sesión local se cerró para proteger la información. Recarga la página e inicia sesión nuevamente.
          </p>
          <button type="button" onClick={() => window.location.reload()} style={{ border: 0, borderRadius: '8px', padding: '10px 16px', background: '#2563eb', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>
            Recargar portal
          </button>
        </section>
      </main>
    );
  }
}
