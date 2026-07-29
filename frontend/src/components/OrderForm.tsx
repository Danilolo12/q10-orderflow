import React, { useState, useEffect } from 'react';
import type { Product, OrderCreate } from '../types';
import { getProducts, createOrder } from '../services/api';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface OrderFormProps {
  onOrderCreated: () => void;
}

export const OrderForm: React.FC<OrderFormProps> = ({ onOrderCreated }) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedSku, setSelectedSku] = useState<string>('');
  const [customerName, setCustomerName] = useState<string>('');
  const [quantity, setQuantity] = useState<string>('1');
  
  // Requisito evaluable: mostrar el error visible en pantalla y no en consola
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
      console.error('Error al cargar productos del catálogo:', err);
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
    // VALIDACIÓN DE INTERFAZ EXIGIDA POR EL CLIENTE
    // =========================================================================
    const trimmedName = customerName.trim();
    if (!trimmedName) {
      setValidationError('Por favor ingresa el nombre del cliente para continuar.');
      return;
    }

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty < 1 || qty > 100) {
      setValidationError('La cantidad solicitada debe ser un valor entre 1 y 100 unidades.');
      return;
    }

    if (!selectedSku) {
      setValidationError('Debes seleccionar un producto válido del catálogo.');
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
      setSuccessMessage('Pedido registrado con éxito. Procesando reserva de stock...');
      setCustomerName('');
      setQuantity('1');
      onOrderCreated();
      setTimeout(fetchStock, 1500);
    } catch (err: any) {
      setValidationError(err.message || 'Error en la comunicación con el servidor al crear el pedido.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Registrar Nuevo Pedido</h2>
          <p className="panel-subtitle">Selecciona el producto y especifica las unidades a solicitar</p>
        </div>
      </div>

      {validationError && (
        <div className="alert-box">
          <AlertCircle size={17} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span>{validationError}</span>
        </div>
      )}

      {successMessage && (
        <div className="alert-box success">
          <CheckCircle2 size={17} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label className="form-label">Nombre del cliente o razón social</label>
          <input
            type="text"
            className={`input-control ${validationError && !customerName.trim() ? 'invalid' : ''}`}
            placeholder="Ej. Daniel Ramos"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            disabled={isSubmitting}
          />
        </div>

        <div className="form-field">
          <label className="form-label">Producto disponible</label>
          <select
            className="input-control"
            value={selectedSku}
            onChange={(e) => setSelectedSku(e.target.value)}
            disabled={isSubmitting}
          >
            {products.map((p) => (
              <option key={p.sku} value={p.sku}>
                {p.name} — ${p.price} USD
              </option>
            ))}
          </select>
          {selectedProduct && (
            <div className="stock-info">
              <span>Código: {selectedProduct.sku}</span>
              <span>En almacén: <strong>{selectedProduct.available_quantity} disponibles</strong></span>
            </div>
          )}
        </div>

        <div className="form-field">
          <label className="form-label">Cantidad a solicitar</label>
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
          {isSubmitting ? 'Enviando pedido al sistema...' : 'Registrar Pedido'}
        </button>
      </form>
    </div>
  );
};
