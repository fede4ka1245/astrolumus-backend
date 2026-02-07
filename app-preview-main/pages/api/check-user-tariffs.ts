import type { NextApiRequest, NextApiResponse } from 'next';

interface UserTariffCheck {
  user_exist: boolean;
  active_tariff_codes: string[];
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<UserTariffCheck | { error: string }>) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({ error: 'Email is required' });
    }

    const backendUrl = process.env.BACKEND_URL;
    const backendToken = process.env.BACKEND_API_TOKEN;
    
    console.log('Checking user tariffs with URL:', backendUrl);
    
    if (!backendUrl) {
      throw new Error('BACKEND_URL environment variable is not set. Please set BACKEND_URL in root .env file');
    }
    if (!backendToken) {
      throw new Error('BACKEND_API_TOKEN environment variable is not set. Please set BACKEND_API_TOKEN in root .env file');
    }

    const checkUrl = `${backendUrl}/tariffs/check-user-exist/`;
    console.log('Sending request to:', checkUrl);
    console.log('With email:', email);
    
    const response = await fetch(checkUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        token: backendToken,
      }),
    });

    console.log('Backend response status:', response.status);

    let data: any;
    try {
      data = await response.json();
    } catch (e) {
      const text = await response.text();
      console.error('Backend error (raw text):', text);
      throw new Error(`Backend returned ${response.status}: ${text.substring(0, 200)}`);
    }

    if (!response.ok) {
      console.error('Backend error response:', data);
      throw new Error(`Backend returned ${response.status}: ${data.detail || data.error || JSON.stringify(data)}`);
    }

    console.log('Success response:', data);
    res.status(200).json(data);
  } catch (error: any) {
    console.error('Error checking user tariffs:', error.message);
    res.status(500).json({ error: error.message || 'Failed to check user tariffs' });
  }
}

