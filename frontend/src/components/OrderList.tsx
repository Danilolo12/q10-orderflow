import React from 'react';
import type { Order } from '../types';
import { 
  CheckCircle2, 
  Clock, 
  XCircle, 
  AlertTriangle, 
  Package, 
  Loader2 
} from 'lucide-react';

interface OrderListProps {
  orders: Order[];
  isLoading: boolean;
}

interface StatusConfig {
  label: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  styleClass: string;
}

// Arquitectura declarativa de UI - Cero switches ni emojis harcodeados
const STATUS_REGISTRY: Record<string, StatusConfig> = {
  Confirmed: {
    label: 'Confirmed',
    icon: CheckCircle2,
    styleClass: 'status-pill-confirmed',
  },
  Pending: {
    label: 'Processing In Queue',
    icon: Clock,
    styleClass: 'status-pill-pending',
  },
  Rejected: {
    label: 'Stock Rejected',
    icon: XCircle,
    styleClass: 'status-pill-rejected',
  },
  Default: {
    label: 'Broker Offline',
    icon: AlertTriangle,
    styleClass: 'status-pill-failed',
  },
};

export const OrderList: React.FC<OrderListProps> = ({ orders, isLoading }) => {
  const getStatusPresentation = (status: string): StatusConfig => {
    return STATUS_REGISTRY[status] || STATUS_REGISTRY.Default;
  };

  const formatTimestamp = (isoDate: string): string => {
    try {
      const date = new Date(isoDate);
      return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoDate;
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">
            <span>Order Processing Feed</span>
          </div>
          <p className="panel-subtitle">Real-time status tracking powered by RabbitMQ & PostgreSQL</p>
        </div>
        <div className="badge-count">
          {orders.length} {orders.length === 1 ? 'transaction' : 'transactions'}
        </div>
      </div>

      {isLoading && orders.length === 0 ? (
        <div className="empty-state-box">
          <Loader2 size={24} className="icon-spin" style={{ color: 'var(--text-secondary)' }} />
          <p style={{ marginTop: '12px' }}>Connecting to Orders API & synchronizing feed...</p>
        </div>
      ) : orders.length === 0 ? (
        <div className="empty-state-box">
          <Package size={36} style={{ color: 'var(--border-focus)', marginBottom: '8px' }} />
          <p>No transactions recorded yet.</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
            Submit an order from the left panel to witness synchronous validation and async RabbitMQ worker resolution.
          </p>
        </div>
      ) : (
        <div className="order-list-stack">
          {orders.map((order) => {
            const { label, icon: IconComponent, styleClass } = getStatusPresentation(order.status);

            return (
              <div key={order.id} className="order-card">
                <div className="order-card-header">
                  <div>
                    <div className="customer-name">{order.customer_name}</div>
                    <div className="order-uuid">UUID: {order.id}</div>
                  </div>
                  
                  <div className={`status-pill ${styleClass}`}>
                    <IconComponent size={14} />
                    <span>{label}</span>
                  </div>
                </div>

                <div className="order-card-grid">
                  <div className="metric-item">
                    <span className="metric-label">SKU Target</span>
                    <span className="metric-value">{order.sku}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">Units</span>
                    <span className="metric-value">{order.quantity}</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-label">Last State Sync</span>
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
