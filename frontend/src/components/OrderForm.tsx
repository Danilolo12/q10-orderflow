import { useState, useEffect } from 'react';
import type { Product, OrderCreate } from '../types';
import { getProducts, createOrder } from '../services/api';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface Props {
  onOrderCreated: () => void;
}

export function OrderForm({ onOrderCreated }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [sku, setSku] = useState('');
  const [name, setName] = useState('');
  const [qty, setQty] = useState('1');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    getProducts().then((data) => {
      setProducts(data);
      if (data.length > 0) setSku(data[0].sku);
    }).catch(() => {});
  }, []);

  const selected = products.find((p) => p.sku === sku);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const trimmed = name.trim();
    if (!trimmed) {
      setError('Ingresa el nombre del cliente.');
      return;
    }

    const quantity = parseInt(qty, 10);
    if (isNaN(quantity) || quantity < 1 || quantity > 100) {
      setError('La cantidad debe estar entre 1 y 100.');
      return;
    }

    if (!sku) {
      setError('Selecciona un producto del catálogo.');
      return;
    }

    try {
      setSending(true);
      const payload: OrderCreate = { customer_name: trimmed, sku, quantity };
      await createOrder(payload);
      setSuccess('Pedido registrado. Procesando reserva de inventario...');
      setName('');
      setQty('1');
      onOrderCreated();
      // Refrescar stock tras breve espera para ver descuento
      setTimeout(() => {
        getProducts().then(setProducts).catch(() => {});
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Error al comunicar con el servidor.');
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="card">
      <div className="card-head">
        <h2>Nuevo pedido</h2>
      </div>
      <div className="card-body">
        {error && (
          <div className="feedback error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="feedback success">
            <CheckCircle2 size={16} />
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="customer">Cliente</label>
            <input
              id="customer"
              type="text"
              placeholder="Nombre o razón social"
              className={error && !name.trim() ? 'has-error' : ''}
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={sending}
            />
          </div>

          <div className="field">
            <label htmlFor="product">Producto</label>
            <select
              id="product"
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              disabled={sending}
            >
              {products.map((p) => (
                <option key={p.sku} value={p.sku}>
                  {p.name} — ${p.price}
                </option>
              ))}
            </select>
            {selected && (
              <div className="hint">
                <span>{selected.sku}</span>
                <span><strong>{selected.available_quantity}</strong> disponibles</span>
              </div>
            )}
          </div>

          <div className="field">
            <label htmlFor="quantity">Cantidad</label>
            <input
              id="quantity"
              type="number"
              min="1"
              max="100"
              className={error && (parseInt(qty) < 1 || parseInt(qty) > 100) ? 'has-error' : ''}
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              disabled={sending}
            />
          </div>

          <button type="submit" className="btn-submit" disabled={sending}>
            {sending ? 'Registrando pedido...' : 'Crear pedido'}
          </button>
        </form>
      </div>
    </div>
  );
}
