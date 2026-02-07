import type { NextApiRequest, NextApiResponse } from 'next';

interface Order {
  id: string;
  status: string;
  payment_url: string;
  payment_id: string;
  amount: string;
  tariff: number;
  user: number;
  pay_system: string;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<Order | { error: string }>) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { id } = req.query;

    if (!id || typeof id !== 'string') {
      return res.status(400).json({ error: 'Order ID is required' });
    }

    const backendUrl = process.env.BACKEND_URL;

    if (!backendUrl) {
      console.error('BACKEND_URL environment variable is not set');
      return res.status(500).json({ error: 'Backend URL not configured' });
    }

    console.log(`Fetching order ${id} from backend`);
    const response = await fetch(`${backendUrl}/payments/orders/${id}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      console.error('Backend error:', error);
      throw new Error(error.detail || `Backend returned ${response.status}`);
    }

    const data = await response.json();
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.status(200).json(data);
  } catch (error: any) {
    console.error('Error fetching order:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch order' });
  }
}

