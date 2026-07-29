import React, { useState, useEffect } from 'react';
import type { Product, OrderCreate } from '../types';
import { getProducts, createOrder } from '../services/api';

interface OrderFormProps {
  onOrderCreated: () => void;
}

export const OrderForm: React.FC<OrderFormProps> = ({ onOrderCreated }) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedSku, setSelectedSku] = useState<string>('');
  const [customerName, setCustomerName] = useState<string>('');
  const [quantity, setQuantity] = useState<string>('1');
  
  // Exigencia del test: Errores mostrados VISUALMENTE EN PANTALLA, no solo consola
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchStock = async () => {
    try {
      const data = await getProducts();
      setProducts(data);
      if (data.length > 0 && !selectedSku) {
        setSelectedSku(data[0].sku);
      }
    } catch (err) {
      console.error('No se pudo cargar el catálogo:', err);
    }
  };

  useEffect(() => {
    fetchStock();
  }, []);

  const selectedProduct = products.find(p => p.sku === selectedSku);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    setSuccessMessage(null);

    // =========================================================================
    // VALIDACIONES VISIBLEMENTE MOSTRADAS EN PANTALLA
    // =========================================================================
    const trimmedName = customerName.trim();
    if (!trimmedName) {
      setValidationError('El nombre del cliente no puede estar vacío.');
      return;
    }

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty < 1 || qty > 100) {
      setValidationError('Cantidad no válida: El pedido debe solicitar entre 1 y 100 unidades.');
      return;
    }

    if (!selectedSku) {
      setValidationError('Debe seleccionar un producto del catálogo.');
      return;
    }

    try {
      setIsSubmitting(true);
      const payload: OrderCreate = {
        customer_name: trimmedName,
        sku: selectedSku,
        quantity: qty,
      };

      await createOrder(payload);
      setSuccessMessage('Pedido transaccional encolado a RabbitMQ (Estado: Pending)');
      setCustomerName('');
      setQuantity('1');
      onOrderCreated();
      // Actualizar stocks exhibidos luego de 1 segundo para ver el reflejo del worker
      setTimeout(fetchStock, 1200);
    } catch (err: any) {
      setValidationError(err.message || 'Error en el servidor al encolar el pedido.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-card">
      <h2 className="section-title">📦 Nuevo Pedido</h2>
      <p className="section-subtitle">Cree pedidos asíncronos encolados por RabbitMQ</p>

      {/* RENDERIZADO DIARIO REAL DE ERRORES DE VALIDACIÓN EN PANTALLA */}
      {validationError && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span><strong>Error:</strong> {validationError}</span>
        </div>
      )}

      {successMessage && (
        <div className="error-banner" style={{ backgroundColor: 'rgba(16, 185, 129, 0.15)', borderColor: 'rgba(16, 185, 129, 0.4)', color: '#6ee7b7' }}>
          <span className="error-icon">✨</span>
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-group">
          <label className="form-label">Cliente o Razón Social</label>
          <input
            type="text"
            className={`form-input ${validationError && !customerName.trim() ? 'has-error' : ''}`}
            placeholder="ej. Daniel Ramos / Empresa Q10"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            disabled={isSubmitting}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Producto del Catálogo</label>
          <select
            className="form-select"
            value={selectedSku}
            onChange={(e) => setSelectedSku(e.target.value)}
            disabled={isSubmitting}
          >
            {products.map((p) => (
              <option key={p.sku} value={p.sku}>
                {p.name} — ${p.price} (Stock: {p.available_quantity})
              </option>
            ))}
          </select>
          {selectedProduct && (
            <div className="stock-pill">
              Stock actual disponible: {selectedProduct.available_quantity} unidades
            </div>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">Cantidad (Máximo 100)</label>
          <input
            type="number"
            min="1"
            max="100"
            className={`form-input ${validationError && (parseInt(quantity) < 1 || parseInt(quantity) > 100) ? 'has-error' : ''}`}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            disabled={isSubmitting}
          />
        </div>

        <button type="submit" className="submit-btn" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <div className="spinner"></div>
              <span>Encolando a RabbitMQ...</span>
            </>
          ) : (
            <>
              <span>Generar Pedido Senior</span>
              <span>→</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};
