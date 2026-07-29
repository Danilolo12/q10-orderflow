import type { Order } from '../types';
import { CheckCircle2, Clock, XCircle, AlertTriangle } from 'lucide-react';

interface Props {
  orders: Order[];
  isLoading: boolean;
}

const STATUS_MAP: Record<string, { label: string; icon: typeof CheckCircle2; css: string }> = {
  Confirmed: { label: 'Confirmado', icon: CheckCircle2, css: 'badge-confirmed' },
  Pending:   { label: 'En proceso', icon: Clock,        css: 'badge-pending' },
  Rejected:  { label: 'Rechazado',  icon: XCircle,      css: 'badge-rejected' },
};

const FALLBACK = { label: 'Error', icon: AlertTriangle, css: 'badge-failed' };

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('es-CO', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    });
  } catch {
    return iso;
  }
}

function shortId(id: string): string {
  return id.split('-')[0] || id;
}

export function OrderList({ orders, isLoading }: Props) {
  return (
    <div className="card">
      <div className="card-head">
        <h2>Historial de pedidos</h2>
        <span className="count">{orders.length}</span>
      </div>

      {isLoading && orders.length === 0 ? (
        <div className="card-body">
          <div className="empty-state">
            <p>Cargando pedidos...</p>
          </div>
        </div>
      ) : orders.length === 0 ? (
        <div className="card-body">
          <div className="empty-state">
            <p>Sin pedidos registrados</p>
            <p>Crea un pedido desde el formulario para verlo reflejado aquí en tiempo real.</p>
          </div>
        </div>
      ) : (
        <table className="orders-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Cliente</th>
              <th>Producto</th>
              <th style={{ textAlign: 'center' }}>Cant.</th>
              <th>Estado</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => {
              const st = STATUS_MAP[order.status] || FALLBACK;
              const Icon = st.icon;
              return (
                <tr key={order.id}>
                  <td className="col-id">{shortId(order.id)}</td>
                  <td className="col-customer">{order.customer_name}</td>
                  <td>{order.sku}</td>
                  <td className="col-qty">{order.quantity}</td>
                  <td>
                    <span className={`badge ${st.css}`}>
                      <Icon size={13} />
                      {st.label}
                    </span>
                  </td>
                  <td>{formatTime(order.updated_at || order.created_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
