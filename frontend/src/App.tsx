import { useState, useEffect, useCallback } from 'react';
import { OrderForm } from './components/OrderForm';
import { OrderList } from './components/OrderList';
import { getOrders } from './services/api';
import type { Order } from './types';

export default function App() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchOrders = useCallback(async () => {
    try {
      const data = await getOrders();
      setOrders(data);
    } catch {
      // Silenciar errores durante polling
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 3000);
    return () => clearInterval(interval);
  }, [fetchOrders]);

  const totalOrders = orders.length;
  const confirmed = orders.filter(o => o.status === 'Confirmed').length;
  const pending = orders.filter(o => o.status === 'Pending').length;
  const rejected = orders.filter(o => o.status === 'Rejected' || o.status.startsWith('Failed')).length;

  return (
    <div>
      <header className="topbar">
        <div className="topbar-left">
          <span className="topbar-title">OrderFlow</span>
          <span className="topbar-sep">/</span>
          <span className="topbar-section">Panel de operaciones</span>
        </div>
        <div className="sync-indicator">
          <span className="sync-dot" />
          <span>Sincronización cada 3s</span>
        </div>
      </header>

      <div className="main-content">
        <div className="page-header">
          <h2>Gestión de pedidos</h2>
          <p>Crea pedidos y monitorea su resolución asíncrona en tiempo real</p>
        </div>

        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-label">Total pedidos</div>
            <div className="stat-value">{totalOrders}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Confirmados</div>
            <div className="stat-value green">{confirmed}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">En proceso</div>
            <div className="stat-value amber">{pending}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Rechazados</div>
            <div className="stat-value red">{rejected}</div>
          </div>
        </div>

        <div className="grid-layout">
          <OrderForm onOrderCreated={fetchOrders} />
          <OrderList orders={orders} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}
