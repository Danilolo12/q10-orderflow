import React from 'react';
import type { Order } from '../types';
import { CheckCircle2, Clock, XCircle, AlertTriangle } from 'lucide-react';

interface OrderListProps {
  orders: Order[];
  isLoading: boolean;
}

interface StatusConfig {
  label: string;
  icon: React.ComponentType<{ size?: number }>;
  className: string;
}

// Mapeo en español natural y profesional para la operación
const STATUS_CONFIG: Record<string, StatusConfig> = {
  Confirmed: {
    label: 'Confirmado',
    icon: CheckCircle2,
    className: 'status-confirmed',
  },
  Pending: {
    label: 'Reservando en almacén...',
    icon: Clock,
    className: 'status-pending',
  },
  Rejected: {
    label: 'Rechazado (Sin stock)',
    icon: XCircle,
    className: 'status-rejected',
  },
  Default: {
    label: 'Fallo de comunicación',
    icon: AlertTriangle,
    className: 'status-failed',
  },
};

export const OrderList: React.FC<OrderListProps> = ({ orders, isLoading }) => {
  const getStatusPresentation = (status: string): StatusConfig => {
    return STATUS_CONFIG[status] || STATUS_CONFIG.Default;
  };

  const formatTimestamp = (isoDate: string): string => {
    try {
      const date = new Date(isoDate);
      return date.toLocaleTimeString('es-ES', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoDate;
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Monitor de Pedidos en Vivo</h2>
          <p className="panel-subtitle">Registro transaccional y actualización asíncrona de estados</p>
        </div>
        <div className="badge-count">
          {orders.length} {orders.length === 1 ? 'registro' : 'registros'}
        </div>
      </div>

      {isLoading && orders.length === 0 ? (
        <div className="empty-state-box">
          <p>Conectando con el servidor y verificando historial...</p>
        </div>
      ) : orders.length === 0 ? (
        <div className="empty-state-box">
          <p style={{ fontWeight: 500, color: 'var(--text-main)' }}>Aún no hay pedidos en el sistema</p>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-tertiary)', marginTop: '6px' }}>
            Completa el formulario de la izquierda para registrar un nuevo pedido y ver la respuesta en tiempo real.
          </p>
        </div>
      ) : (
        <div className="order-list-stack">
          {orders.map((order) => {
            const { label, icon: IconComponent, className } = getStatusPresentation(order.status);

            return (
              <div key={order.id} className="order-card">
                <div className="order-card-header">
                  <div>
                    <div className="customer-name">{order.customer_name}</div>
                    <div className="order-id">ID: {order.id}</div>
                  </div>
                  
                  <div className={`status-pill ${className}`}>
                    <IconComponent size={14} />
                    <span>{label}</span>
                  </div>
                </div>

                <div className="order-card-footer">
                  <div className="metric-box">
                    <span className="metric-label">Producto</span>
                    <span className="metric-value" style={{ fontFamily: 'var(--font-mono)' }}>{order.sku}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-label">Unidades</span>
                    <span className="metric-value">{order.quantity}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-label">Última actualización</span>
                    <span className="metric-value">{formatTimestamp(order.updated_at || order.created_at)}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
