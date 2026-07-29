import React, { useState, useEffect, useCallback } from 'react';
import { OrderForm } from './components/OrderForm';
import { OrderList } from './components/OrderList';
import { getOrders } from './services/api';
import { RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const [orders, setOrders] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchOrderList = useCallback(async () => {
    try {
      const data = await getOrders();
      setOrders(data);
    } catch (err) {
      console.error('Error durante sincronización por polling:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Polling automático exigido cada 3 segundos exactos
  useEffect(() => {
    fetchOrderList();
    const pollingInterval = setInterval(() => {
      fetchOrderList();
    }, 3000);

    return () => clearInterval(pollingInterval);
  }, [fetchOrderList]);

  return (
    <div className="app-wrapper">
      <nav className="top-nav">
        <div className="nav-brand">
          <div className="brand-symbol">Q</div>
          <div className="brand-details">
            <h1>OrderFlow Console</h1>
            <p>Senior Distributed System · FastAPI · RabbitMQ · PostgreSQL 16</p>
          </div>
        </div>
        
        <div className="polling-indicator" title="Intervalo automático activo consultando GET /orders cada 3s">
          <span className="status-dot"></span>
          <span>Live Polling (3s)</span>
          <RefreshCw size={12} className="icon-spin" style={{ opacity: 0.7, marginLeft: '2px' }} />
        </div>
      </nav>

      <main className="dashboard-grid">
        <section>
          <OrderForm onOrderCreated={fetchOrderList} />
        </section>

        <section>
          <OrderList orders={orders} isLoading={isLoading} />
        </section>
      </main>
    </div>
  );
};

export default App;
