import type { NextApiRequest, NextApiResponse } from 'next';

interface OrderStatus {
  id: string;
  status: 'pending' | 'succeeded' | 'failed' | 'canceled';
  amount: string;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<OrderStatus | { error: string }>) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { order_id } = req.query;

    if (!order_id || typeof order_id !== 'string') {
      return res.status(400).json({ error: 'Missing order_id' });
    }

    const backendUrl = process.env.BACKEND_URL;
    if (!backendUrl) {
      throw new Error('BACKEND_URL environment variable is not set');
    }

    const response = await fetch(`${backendUrl}/payments/orders/${order_id}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return res.status(404).json({ error: 'Order not found' });
      }
      throw new Error(`Backend returned ${response.status}`);
    }

    const order: OrderStatus = await response.json();
    res.status(200).json(order);
  } catch (error: any) {
    console.error('Error checking order:', error);
    res.status(500).json({ error: 'Failed to check order status' });
  }
}

