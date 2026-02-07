import type { NextApiRequest, NextApiResponse } from 'next';

interface CreateOrderRequest {
  email: string;
  tariff_code: string;
  pay_system: 'stripe' | 'bepaid';
  amount: number;
  currency: string;
}

interface Order {
  id: string;
  status: string;
  payment_url: string;
  payment_id: string;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<Order | { error: string }>) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { email, tariff_code, pay_system, amount, currency } = req.body as CreateOrderRequest;

    if (!email || !tariff_code || !pay_system || !amount || !currency) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    let accessToken = null;

    const backendUrl = process.env.BACKEND_URL;
    const backendToken = process.env.BACKEND_API_TOKEN;
    
    if (!backendUrl) {
      throw new Error('BACKEND_URL environment variable is not set');
    }
    if (!backendToken) {
      throw new Error('BACKEND_API_TOKEN environment variable is not set');
    }

    const checkUserResponse = await fetch(`${backendUrl}/tariffs/check-user-exist/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        token: backendToken,
      }),
    });

    if (!checkUserResponse.ok) {
      throw new Error('Failed to check user existence');
    }

    const userCheckData = await checkUserResponse.json();

    if (!userCheckData.user_exist) {
      console.log(`Creating guest order for ${email}`);
    }

    // Ensure amount is valid
    if (amount <= 0) {
      throw new Error('Invalid amount: must be greater than 0');
    }

    console.log(`💰 Creating order - Currency: ${currency}, Amount: ${amount}, Pay system: ${pay_system}`);

    const orderResponse = await fetch(`${backendUrl}/payments/orders/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify({
        email,
        tariff_code,
        pay_system,
        amount: Math.round(amount * 100) / 100,  // Ensure 2 decimal places
        currency,  // Pass currency to Django backend
      }),
    });

    if (!orderResponse.ok) {
      const error = await orderResponse.json();
      throw new Error(error.error || 'Failed to create order');
    }

    const order: Order = await orderResponse.json();

    res.status(201).json(order);
  } catch (error: any) {
    console.error('Error creating order:', error);
    res.status(500).json({ error: error.message || 'Failed to create order' });
  }
}

