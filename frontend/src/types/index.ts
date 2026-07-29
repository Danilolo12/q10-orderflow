export interface Product {
  sku: string;
  name: string;
  available_quantity: number;
  price: number;
}

export interface Order {
  id: string;
  customer_name: string;
  sku: string;
  quantity: number;
  status: 'Pending' | 'Confirmed' | 'Rejected' | string;
  created_at: string;
  updated_at: string;
  product?: Product;
}

export interface OrderCreate {
  customer_name: string;
  sku: string;
  quantity: number;
}
