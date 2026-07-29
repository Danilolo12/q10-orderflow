import React, { useState, useEffect, useCallback } from 'react';
import { OrderForm } from './components/OrderForm';
import { OrderList } from './components/OrderList';
import { getOrders } from './services/api';

export const App: React.FC = () => {
  const [orders, setOrders] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchOrderList = useCallback(async () => {
    try {
      const data = await getOrders();
      setOrders(data);
    } catch (err) {
      console.error('Error durante polling de pedidos:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ===========================================================================
  // POLLING AUTOMÁTICO EXIGIDO POR LA PRUEBA (Cada 3.5 segundos)
  // ===========================================================================
  useEffect(() => {
    fetchOrderList();
    const pollingInterval = setInterval(() => {
      fetchOrderList();
    }, 3000);

    return () => clearInterval(pollingInterval);
  }, [fetchOrderList]);

  return (
    <div className="app-container">
      <header className="header">
        <div className="logo-section">
          <div className="logo-icon">Q</div>
          <div className="logo-text">
            <h1>Q10 OrderFlow System</h1>
            <p>Senior Event-Driven Architecture · FastAPI · RabbitMQ · PostgreSQL</p>
          </div>
        </div>
        
        <div className="polling-badge" title="Sincronización en segundo plano activa cada 3 segundos">
          <div className="pulse-circle"></div>
          <span>Live Polling Active (3s)</span>
        </div>
      </header>

      <main className="main-grid">
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
