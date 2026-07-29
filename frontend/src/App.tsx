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
      console.error('Error durante sincronización del historial:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Polling automático exigido cada 3 segundos
  useEffect(() => {
    fetchOrderList();
    const pollingInterval = setInterval(() => {
      fetchOrderList();
    }, 3000);

    return () => clearInterval(pollingInterval);
  }, [fetchOrderList]);

  return (
    <div className="app-wrapper">
      <header className="top-nav">
        <div>
          <h1 className="header-title">Panel de Operaciones OrderFlow</h1>
          <p className="header-subtitle">Gestión de pedidos e inventario con verificación asíncrona</p>
        </div>
        
        <div className="sync-badge" title="La tabla de pedidos se sincroniza en tiempo real de forma automática cada 3 segundos">
          <span className="status-dot"></span>
          <span>Sincronización continua activa (3s)</span>
        </div>
      </header>

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
