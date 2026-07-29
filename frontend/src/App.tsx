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
      // Silenciar errores de red durante polling
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 3000);
    return () => clearInterval(interval);
  }, [fetchOrders]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-left">
          <span className="topbar-title">OrderFlow</span>
          <span className="topbar-separator">/</span>
          <span className="topbar-section">Panel de operaciones</span>
        </div>
        <div className="sync-indicator">
          <span className="sync-dot" />
          <span>Sincronización cada 3s</span>
        </div>
      </header>

      <div className="main-content">
        <div className="grid-layout">
          <OrderForm onOrderCreated={fetchOrders} />
          <OrderList orders={orders} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}
