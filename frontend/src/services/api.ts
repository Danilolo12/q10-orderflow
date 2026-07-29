import type { Order, OrderCreate, Product } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function getProducts(): Promise<Product[]> {
  const response = await fetch(`${API_URL}/products`);
  if (!response.ok) {
    throw new Error('Error al consultar inventario en el servidor');
  }
  return response.json();
}

export async function getOrders(): Promise<Order[]> {
  const response = await fetch(`${API_URL}/orders`);
  if (!response.ok) {
    throw new Error('Error de red al consultar el listado de pedidos');
  }
  return response.json();
}

export async function createOrder(data: OrderCreate): Promise<Order> {
  const response = await fetch(`${API_URL}/orders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const errorMessage = errData.detail || 'Fallo interno en el sistema de pedidos (RabbitMQ inalcanzable)';
    throw new Error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
  }

  return response.json();
}
