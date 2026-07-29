import React from 'react';
import type { Order } from '../types';

interface OrderListProps {
  orders: Order[];
  isLoading: boolean;
}

export const OrderList: React.FC<OrderListProps> = ({ orders, isLoading }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Confirmed':
        return '✓ Confirmed';
      case 'Pending':
        return '⏳ Pending...';
      case 'Rejected':
        return '✕ Rejected';
      default:
        return `⚠️ ${status}`;
    }
  };

  const getStatusClass = (status: string) => {
    if (status.startsWith('Failed')) return 'Failed';
    return status;
  };

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' +
             date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="glass-card" style={{ minHeight: '600px' }}>
      <div className="orders-header">
        <div>
          <h2 className="section-title">⚡ Flujo de Pedidos en Vivo</h2>
          <p className="section-subtitle">Sincronización mediante Polling (3.5s interval)</p>
        </div>
        <div className="order-count">
          Total registros: <strong>{orders.length}</strong>
        </div>
      </div>

      {isLoading && orders.length === 0 ? (
        <div className="empty-state">
          <div className="spinner" style={{ margin: '0 auto 1rem', width: '32px', height: '32px', borderWidth: '4px' }}></div>
          <p>Conectando con FastAPI y cargando transacciones...</p>
        </div>
      ) : orders.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📂</div>
          <p>Aún no hay pedidos creados.</p>
          <p style={{ fontSize: '0.85rem', marginTop: '6px' }}>
            Genera tu primer pedido en el formulario izquierdo para ver al worker de inventario actuar en milisegundos.
          </p>
        </div>
      ) : (
        <div className="orders-grid">
          {orders.map((order) => (
            <div key={order.id} className={`order-item status-${getStatusClass(order.status)}`}>
              <div className="order-main-info">
                <div className="customer-info">
                  <h3>{order.customer_name}</h3>
                  <div className="order-id">ID: {order.id}</div>
                </div>
                <div className={`status-badge ${getStatusClass(order.status)}`}>
                  {getStatusIcon(order.status)}
                </div>
              </div>

              <div className="order-details">
                <div className="detail-cell">
                  <span className="detail-label">Producto (SKU)</span>
                  <span className="detail-value">{order.sku}</span>
                </div>
                <div className="detail-cell">
                  <span className="detail-label">Cantidad</span>
                  <span className="detail-value">{order.quantity} {order.quantity === 1 ? 'unidad' : 'unidades'}</span>
                </div>
                <div className="detail-cell">
                  <span className="detail-label">Última actualización</span>
                  <span className="detail-value">{formatTime(order.updated_at || order.created_at)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
