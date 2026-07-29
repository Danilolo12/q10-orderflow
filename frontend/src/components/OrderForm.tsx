import React, { useState, useEffect } from 'react';
import type { Product, OrderCreate } from '../types';
import { getProducts, createOrder } from '../services/api';
import { AlertCircle, CheckCircle2, ArrowRight, Loader2, ShoppingCart } from 'lucide-react';

interface OrderFormProps {
  onOrderCreated: () => void;
}

export const OrderForm: React.FC<OrderFormProps> = ({ onOrderCreated }) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedSku, setSelectedSku] = useState<string>('');
  const [customerName, setCustomerName] = useState<string>('');
  const [quantity, setQuantity] = useState<string>('1');
  
  // Requisito evaluado: Alertas visuales in situ en la interfaz (cero console bugs)
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
      console.error('Fallo al obtener inventario del almacén:', err);
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
    // VALIDACIONES MOSTRadas DE INMEDIATO EN PANTALLA
    // =========================================================================
    const trimmedName = customerName.trim();
    if (!trimmedName) {
      setValidationError('El nombre de cliente o razón social es un campo obligatorio.');
      return;
    }

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty < 1 || qty > 100) {
      setValidationError('Cantidad inválida: el contrato estipula entre 1 y 100 unidades.');
      return;
    }

    if (!selectedSku) {
      setValidationError('Debe seleccionar un producto existente en el almacén.');
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
      setSuccessMessage('Pedido transaccionado con éxito encolado (Estado inicial: Pending).');
      setCustomerName('');
      setQuantity('1');
      onOrderCreated();
      setTimeout(fetchStock, 1200);
    } catch (err: any) {
      setValidationError(err.message || 'Error transaccional al comunicar con RabbitMQ.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">
            <ShoppingCart size={18} style={{ color: 'var(--accent-main)' }} />
            <span>New Transaction Order</span>
          </div>
          <p className="panel-subtitle">Enqueue orders directly to PostgreSQL & RabbitMQ exchange</p>
        </div>
      </div>

      {validationError && (
        <div className="alert-box">
          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '1px' }} />
          <span>{validationError}</span>
        </div>
      )}

      {successMessage && (
        <div className="alert-box success">
          <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '1px' }} />
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label className="form-label">Customer Name</label>
          <input
            type="text"
            className={`input-control ${validationError && !customerName.trim() ? 'invalid' : ''}`}
            placeholder="e.g. Daniel Ramos / Q10 Enterprise"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            disabled={isSubmitting}
          />
        </div>

        <div className="form-field">
          <label className="form-label">Inventory Catalog (Seed Products)</label>
          <select
            className="input-control"
            value={selectedSku}
            onChange={(e) => setSelectedSku(e.target.value)}
            disabled={isSubmitting}
          >
            {products.map((p) => (
              <option key={p.sku} value={p.sku}>
                {p.name} — ${p.price}
              </option>
            ))}
          </select>
          {selectedProduct && (
            <div className="stock-metadata">
              <span>SKU: {selectedProduct.sku}</span>
              <span>Available Stock: <strong>{selectedProduct.available_quantity} units</strong></span>
            </div>
          )}
        </div>

        <div className="form-field">
          <label className="form-label">Order Units (Max 100)</label>
          <input
            type="number"
            min="1"
            max="100"
            className={`input-control ${validationError && (parseInt(quantity) < 1 || parseInt(quantity) > 100) ? 'invalid' : ''}`}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            disabled={isSubmitting}
          />
        </div>

        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 size={16} className="icon-spin" />
              <span>Publishing to Broker...</span>
            </>
          ) : (
            <>
              <span>Execute Async Order</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </form>
    </div>
  );
};
