import type { NextApiRequest, NextApiResponse } from 'next';

interface Tariff {
  id: number;
  code: string;
  title: string;
  public_description?: string;
  validity_days: number;
  prices: {
    RUB: number;
    BYN: number;
    USD: number;
    EUR: number;
  };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<Tariff[] | { error: string }>) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const backendUrl = process.env.BACKEND_URL;
    console.log('BACKEND_URL:', backendUrl);
    
    if (!backendUrl) {
      throw new Error('BACKEND_URL environment variable is not set');
    }
    
    const lang = req.query.lang as string || 'ru';
    const url = `${backendUrl}/tariffs/public/?lang=${lang}`;
    console.log('Fetching tariffs from:', url);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log('Response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error response:', errorText);
      throw new Error(`Backend returned ${response.status}: ${errorText.substring(0, 200)}`);
    }

    const tariffs: Tariff[] = await response.json();
    console.log('Successfully fetched tariffs:', tariffs.length);
    
    res.setHeader('Cache-Control', 'public, max-age=0');
    res.status(200).json(tariffs);
  } catch (error: any) {
    console.error('Error fetching tariffs:', error.message);
    res.status(500).json({ error: error.message || 'Failed to fetch tariffs' });
  }
}

