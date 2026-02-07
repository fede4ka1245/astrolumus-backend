import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

export default function PaymentSuccess() {
  const router = useRouter();
  const { session_id, order_id } = router.query;
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');

  useEffect(() => {
    const updateOrderStatus = async () => {
      try {
        // Get saved order from localStorage
        const savedOrder = localStorage.getItem('paymentForm_currentOrder');
        
        if (savedOrder) {
          const order = JSON.parse(savedOrder);
          console.log('📋 Checking order status:', order.id);
          
          // Check payment status
          const response = await fetch(`/api/orders/${order.id}`);
          if (response.ok) {
            const updatedOrder = await response.json();
            console.log('✅ Order status:', updatedOrder.status);
            
            // Update localStorage with latest status
            localStorage.setItem('paymentForm_currentOrder', JSON.stringify(updatedOrder));
            
            if (updatedOrder.status === 'succeeded') {
              setStatus('success');
              // Wait 1 second to show success, then redirect
              setTimeout(() => {
                if (window.opener) {
                  window.opener.location.href = '/payment';
                  window.close();
                } else {
                  window.location.href = '/payment';
                }
              }, 1000);
            } else {
              // Still pending, redirect to payment form
              setTimeout(() => {
                if (window.opener) {
                  window.opener.location.href = '/payment';
                  window.close();
                } else {
                  window.location.href = '/payment';
                }
              }, 1000);
            }
          }
        } else {
          // No saved order, just redirect
          setTimeout(() => {
            if (window.opener) {
              window.opener.location.href = '/';
              window.close();
            } else {
              window.location.href = '/';
            }
          }, 1000);
        }
      } catch (error) {
        console.error('Error updating order status:', error);
        setStatus('error');
        // Redirect anyway after error
        setTimeout(() => {
          window.location.href = '/payment';
        }, 2000);
      }
    };

    updateOrderStatus();
  }, [session_id, order_id]);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      fontFamily: 'Gilroy, sans-serif',
      color: '#fff',
      backgroundColor: '#0a0a0a'
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '60px', marginBottom: '20px' }}>✅</div>
        <h1>Payment Successful!</h1>
        <p style={{ color: '#ABB0B2' }}>Closing window...</p>
      </div>
    </div>
  );
}

