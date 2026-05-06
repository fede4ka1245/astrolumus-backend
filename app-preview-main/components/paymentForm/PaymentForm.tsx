import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Grid, Typography, Alert } from '@mui/material';
import styles from '@/styles/Home.module.scss';
import DarkThemeBackground from '@/components/darkThemeBackground/DarkThemeBackground';
import Input from '@/components/input/Input';
import { useTranslation } from '@/i18n/useTranslation';
import { useLocalStorage } from '@/hooks/useLocalStorage';
import { useSessionStorage } from '@/hooks/useSessionStorage';

type Language = 'en' | 'ru' | 'uk' | 'pl' | 'be';

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

interface PaymentFormProps {
  initialEmail?: string;
  language: Language;
}

interface Order {
  id: string;
  status: string;
  payment_url: string;
  amount: string;
  tariff: number;
  user: number;
  pay_system: string;
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
}

function PaymentForm({ initialEmail = '', language }: PaymentFormProps) {
  const { t } = useTranslation(language);
  
  const [email, setEmail] = useLocalStorage('paymentForm_email', initialEmail || '');
  const [selectedPlan, setSelectedPlan] = useLocalStorage<Tariff | null>('paymentForm_selectedPlan', null);
  const [paymentMethod, setPaymentMethod] = useLocalStorage<'stripe' | 'bepaid'>('paymentForm_paymentMethod', 'stripe');
  const [selectedCurrency, setSelectedCurrency] = useLocalStorage<'BYN' | 'EUR'>('paymentForm_currency', 'EUR');
  const [lastBepaidCurrency, setLastBepaidCurrency] = useLocalStorage<'BYN' | 'EUR'>('paymentForm_lastBepaidCurrency', 'BYN');
  const [currentOrder, setCurrentOrder] = useLocalStorage<Order | null>('paymentForm_currentOrder', null);
  const [timeLeft, setTimeLeft] = useLocalStorage('paymentForm_timeLeft', 900);
  const [isWaitingForPayment, setIsWaitingForPayment] = useSessionStorage('paymentForm_isWaiting', false);
  const [tariffs, setTariffs] = useState<Tariff[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [userExists, setUserExists] = useState(false);
  const [activeTariffCodes, setActiveTariffCodes] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCheckingPayment, setIsCheckingPayment] = useState(false);
  const [isLanguageMenuOpen, setIsLanguageMenuOpen] = useState(false);
  const [isCurrencyMenuOpen, setIsCurrencyMenuOpen] = useState(false);
  
  // Track which order payment window was already opened for
  const lastOpenedOrderId = useRef<string | null>(null);
  
  // Helper function to check if redirect was already done for an order
  const hasRedirectedForOrder = (orderId: string): boolean => {
    if (typeof window === 'undefined') return false;
    try {
      const redirectedOrders = JSON.parse(localStorage.getItem('paymentForm_redirectedOrders') || '[]');
      return redirectedOrders.includes(orderId);
    } catch {
      return false;
    }
  };
  
  // Helper function to mark order as redirected
  const markOrderAsRedirected = (orderId: string): void => {
    if (typeof window === 'undefined') return;
    try {
      const redirectedOrders = JSON.parse(localStorage.getItem('paymentForm_redirectedOrders') || '[]');
      if (!redirectedOrders.includes(orderId)) {
        redirectedOrders.push(orderId);
        localStorage.setItem('paymentForm_redirectedOrders', JSON.stringify(redirectedOrders));
      }
    } catch (error) {
      console.warn('Error saving redirected orders to localStorage:', error);
    }
  };
  
  // Helper function to clear redirected orders (when email changes)
  const clearRedirectedOrders = (): void => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.removeItem('paymentForm_redirectedOrders');
    } catch (error) {
      console.warn('Error clearing redirected orders from localStorage:', error);
    }
  };

  // Force set email from URL if provided and save to localStorage
  useEffect(() => {
    if (initialEmail && typeof window !== 'undefined') {
      console.log('📧 Setting email from URL and saving to localStorage:', initialEmail);
      setEmail(initialEmail);
      // Also save directly to localStorage to ensure it persists
      try {
        localStorage.setItem('paymentForm_email', JSON.stringify(initialEmail));
        // Clear redirected orders when email changes
        clearRedirectedOrders();
      } catch (error) {
        console.warn('Error saving email to localStorage:', error);
      }
    }
  }, [initialEmail]);
  
  // Track previous email to detect changes
  const prevEmailRef = useRef<string>(email);
  const isFirstRender = useRef<boolean>(true);
  
  // Clear redirected orders when email changes manually
  useEffect(() => {
    // Skip on first render to avoid clearing on initial load
    if (isFirstRender.current) {
      isFirstRender.current = false;
      prevEmailRef.current = email;
      return;
    }
    
    // Only clear if email actually changed and previous email was not empty
    if (email && prevEmailRef.current !== email && prevEmailRef.current !== '') {
      console.log('📧 Email changed from', prevEmailRef.current, 'to', email, '- clearing redirected orders');
      clearRedirectedOrders();
    }
    prevEmailRef.current = email;
  }, [email]);

  useEffect(() => {
    fetchTariffs();
  }, [language]);

  // For English language, force stripe as the only payment method
  useEffect(() => {
    if (language === 'en' && paymentMethod !== 'stripe') {
      setPaymentMethod('stripe');
    }
  }, [language]);

  // Convert RUB to BYN and USD to EUR if user had old currencies selected previously (from old localStorage)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    // Check if selectedCurrency is RUB or USD (from old localStorage) and convert
    try {
      const currentCurrency = localStorage.getItem('paymentForm_currency');
      if (currentCurrency) {
        const parsed = JSON.parse(currentCurrency);
        if (parsed === 'RUB') {
          setSelectedCurrency('BYN');
          setLastBepaidCurrency('BYN');
        } else if (parsed === 'USD') {
          setSelectedCurrency('EUR');
          setLastBepaidCurrency('EUR');
        }
      }
      // Check if lastBepaidCurrency is RUB or USD and convert
      const lastCurrency = localStorage.getItem('paymentForm_lastBepaidCurrency');
      if (lastCurrency) {
        const parsed = JSON.parse(lastCurrency);
        if (parsed === 'RUB') {
          setLastBepaidCurrency('BYN');
        } else if (parsed === 'USD') {
          setLastBepaidCurrency('EUR');
        }
      }
    } catch (error) {
      // Ignore errors
    }
  }, []);

  // Auto-switch currency when payment method changes
  useEffect(() => {
    if (paymentMethod === 'stripe') {
      // Stripe: always EUR
      if (selectedCurrency !== 'EUR') {
        // Save current currency as last BePaid currency
        setLastBepaidCurrency(selectedCurrency);
        setSelectedCurrency('EUR');
      }
    } else if (paymentMethod === 'bepaid') {
      // BePaid: restore last selected currency (BYN or EUR)
      // Only restore if we're coming from Stripe (current currency is EUR and we have a saved one)
      if (selectedCurrency === 'EUR' && lastBepaidCurrency !== 'EUR') {
        setSelectedCurrency(lastBepaidCurrency);
      }
    }
  }, [paymentMethod]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (isLanguageMenuOpen && !target.closest('[data-language-selector]')) {
        setIsLanguageMenuOpen(false);
      }
      if (isCurrencyMenuOpen && !target.closest('[data-currency-selector]')) {
        setIsCurrencyMenuOpen(false);
      }
    };

    if (isLanguageMenuOpen || isCurrencyMenuOpen) {
      document.addEventListener('click', handleClickOutside);
    }

    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [isLanguageMenuOpen, isCurrencyMenuOpen]);

  // Timer for payment waiting
  useEffect(() => {
    if (!isWaitingForPayment || timeLeft <= 0) return;

    const interval = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isWaitingForPayment, timeLeft]);

  // Auto-check payment status every 2 seconds
  // Check payment status on mount if there's a saved order
  useEffect(() => {
    if (currentOrder && currentOrder.id) {
      console.log('📋 Found saved order on mount:', currentOrder.id, 'Status:', currentOrder.status);
      
      // If order is already completed (succeeded, cancelled, failed), clear state and show form
      if (currentOrder.status === 'succeeded' || currentOrder.status === 'cancelled' || currentOrder.status === 'failed') {
        console.log('✅ Order already completed, clearing state and showing form');
        clearPaymentState();
        return;
      }
      
      // Check status immediately for pending orders
      checkPaymentStatus();
      // If still waiting, enable waiting mode
      if (currentOrder.status === 'pending') {
        setIsWaitingForPayment(true);
      }
    }
  }, []); // Run only on mount

  useEffect(() => {
    if (!isWaitingForPayment || !currentOrder) return;
    if (currentOrder.status === 'succeeded') return;

    const interval = setInterval(() => {
      checkPaymentStatus();
    }, 2000);

    return () => clearInterval(interval);
  }, [isWaitingForPayment, currentOrder]);

  // Auto-open payment page when entering waiting state (only once per order)
  useEffect(() => {
    if (isWaitingForPayment && currentOrder?.payment_url && currentOrder?.id) {
      // Only open if we haven't opened this order yet (check both ref and localStorage)
      const alreadyRedirected = hasRedirectedForOrder(currentOrder.id);
      if (lastOpenedOrderId.current !== currentOrder.id && !alreadyRedirected) {
        console.log('🚀 Auto-opening payment page:', currentOrder.payment_url);
        window.open(currentOrder.payment_url, '_blank');
        lastOpenedOrderId.current = currentOrder.id;
        markOrderAsRedirected(currentOrder.id);
      } else if (alreadyRedirected) {
        console.log('⏭️ Skipping redirect - already redirected for this order');
      }
    }
  }, [isWaitingForPayment, currentOrder?.payment_url, currentOrder?.id]);

  const fetchTariffs = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/tariffs?lang=${language}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch tariffs: ${response.status}`);
      }
      const data = await response.json();
      setTariffs(data);
      
      // Auto-select first tariff if none selected
      if (data.length > 0 && !selectedPlan) {
        setSelectedPlan(data[0]);
        console.log('🎯 Auto-selected first tariff:', data[0].code);
      }
    } catch (err: any) {
      console.error('Error fetching tariffs:', err);
      setError(err.message || 'Failed to load tariffs');
    } finally {
      setLoading(false);
    }
  };

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const getCurrency = (): 'BYN' | 'EUR' => {
    // Return user-selected currency (already managed by useEffect for payment method changes)
    return selectedCurrency;
  };

  // Format currency display: show "BYN (RUB)" when BYN is selected
  const getCurrencyDisplay = (): string => {
    if (selectedCurrency === 'BYN') {
      return 'BYN (RUB)';
    }
    return selectedCurrency;
  };

  // Format price with RUB equivalent for BYN (using tariff prices)
  const formatPriceWithRUB = (price: number, currency: string, tariff?: Tariff | null): string => {
    if (currency === 'BYN' && tariff?.prices?.RUB) {
      return `${price} ${currency} (~${tariff.prices.RUB} RUB)`;
    }
    return `${price} ${currency}`;
  };

  const checkUserAndLoadTariffs = async () => {
    if (!validateEmail(email)) {
      setError(t('payment.invalidEmail'));
      return;
    }
    
    try {
      setLoading(true);
    setError('');
      
      // Check if user exists and get their active tariffs
      const response = await fetch('/api/check-user-tariffs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      let data;
      try {
        data = await response.json();
      } catch (e) {
        console.error('Failed to parse response:', e);
        throw new Error('Invalid response from server');
      }
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to check user');
      }

      setUserExists(data.user_exist);
      setActiveTariffCodes(data.active_tariff_codes || []);
    } catch (err: any) {
      console.error('Error checking user tariffs:', err);
      setError(err.message || 'Failed to check user');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate all fields
    if (!validateEmail(email)) {
      setError(t('payment.invalidEmail'));
      return;
    }

    if (!selectedPlan) {
      setError(t('payment.selectPlanRequired'));
      return;
    }

    if (activeTariffCodes.includes(selectedPlan.code)) {
      setError(t('payment.tariffAlreadyActive') || 'This tariff is already active');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');

      // For bepaid: use BYN if BYN is selected
      // For stripe: use selected currency
      let currency = selectedCurrency;
      if (paymentMethod === 'bepaid' && selectedCurrency === 'BYN') {
        currency = 'BYN';
      }
      
      const amount = selectedPlan?.prices?.[currency];
      
      console.log('💰 Creating order:', {
        paymentMethod,
        selectedCurrency,
        currency,
        amount,
      }, JSON.stringify({
        email,
        tariff_code: selectedPlan?.code,
        pay_system: paymentMethod,
        amount: amount,
        currency: currency,
      }));
      
      if (!amount || amount <= 0) {
        setError(t('payment.invalidAmount') || `Invalid price for tariff: ${currency}`);
        setIsSubmitting(false);
        return;
      }

      const body = JSON.stringify({
        email,
        tariff_code: selectedPlan?.code,
        pay_system: paymentMethod,
        currency,
        amount,
      });

      console.log('🔵 Request body:', body);

      const response = await fetch('/api/create-order', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body,
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle specific error types from backend
        if (data.error === 'unknown_user') {
          setError(t('payment.unknownUser') || 'User not found. Please check your email.');
        } else if (data.error === 'already_paid') {
          setError(t('payment.paid') || 'This tariff is already paid.');
        } else if (data.error === 'unknown_error') {
          setError(t('payment.unknownError') || 'An error occurred. Please try again later.');
        } else {
          setError(data.message || data.error || 'Payment failed');
        }
        setIsSubmitting(false);
        return;
      }

      console.log('✅ Order created:', data);
      
      // Show payment waiting UI on same page
      setCurrentOrder(data);
      setIsWaitingForPayment(true);
      setTimeLeft(900); // Reset timer
      setSuccess('');
      setError('');
    } catch (err: any) {
      setError(err.message || t('payment.error'));
    } finally {
      setIsSubmitting(false);
    }
  }, [email, selectedPlan, activeTariffCodes, selectedCurrency, paymentMethod, t, setError, setIsSubmitting, setCurrentOrder, setIsWaitingForPayment, setTimeLeft, setSuccess]);

  const checkPaymentStatus = async () => {
    if (!currentOrder) return;
    try {
      setIsCheckingPayment(true);
      console.log(`🔍 Checking payment status for order ${currentOrder.id}...`);
      
      const response = await fetch(`/api/orders/${currentOrder.id}`, {
        method: 'GET',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to check payment');
      }
      
      const data = await response.json();
      console.log(`📊 Order status: ${data.status}`, data);
      setCurrentOrder(data);

      // If payment succeeded, show success message and clear localStorage
      if (data.status === 'succeeded') {
        console.log('✅ Payment succeeded!');
        setSuccess(t('payment.success'));
        
        // Clear localStorage but keep UI state to show success screen
        localStorage.removeItem('paymentForm_currentOrder');
        sessionStorage.removeItem('paymentForm_isWaiting');
        localStorage.removeItem('paymentForm_timeLeft');
        localStorage.removeItem('paymentForm_selectedPlan');
        console.log('🗑️ Cleared localStorage after successful payment');
      }
    } catch (err) {
      console.error('❌ Error checking payment:', err);
    } finally {
      setIsCheckingPayment(false);
    }
  };

  const handleGoToPayment = () => {
    if (currentOrder?.payment_url) {
      window.open(currentOrder.payment_url, '_blank');
    }
  };

  const handleCancelPayment = () => {
    if (confirm(t('payment.cancelConfirm') || 'Are you sure?')) {
      // Clear payment state including localStorage
      setIsWaitingForPayment(false);
      setCurrentOrder(null);
      setTimeLeft(900);
      setError('');
      setSuccess('');
      lastOpenedOrderId.current = null;  // Reset opened order tracking
      
      // Clear localStorage
      localStorage.removeItem('paymentForm_currentOrder');
      sessionStorage.removeItem('paymentForm_isWaiting');
      localStorage.removeItem('paymentForm_timeLeft');
      localStorage.removeItem('paymentForm_selectedPlan');
      console.log('🗑️ Cleared localStorage after cancellation');
    }
  };

  const clearPaymentState = () => {
    setCurrentOrder(null);
    setIsWaitingForPayment(false);
    setTimeLeft(900);
    setSelectedPlan(null);
    setSuccess('');
    setError('');
    setUserExists(false);
    setActiveTariffCodes([]);
    setTariffs([]);
    lastOpenedOrderId.current = null;  // Reset opened order tracking
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const languages = [
    { code: 'ru', name: 'Русский', flag: '🇷🇺' },
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'uk', name: 'Українська', flag: '🇺🇦' },
    { code: 'pl', name: 'Polski', flag: '🇵🇱' },
  ];

  const currentLanguage = languages.find(lang => lang.code === language) || languages[0];

  const handleLanguageChange = (newLang: string) => {
    window.location.href = `/payment/${newLang}`;
  };

  const currency = getCurrency();

  return (
    <Grid display={'flex'} direction={'column'} alignItems={'center'}>
      <header className={styles.header}>
        <h1 className={styles.logo}>AlphaSpace</h1>
      </header>

      <Grid width={'600px'} maxWidth={'100%'} mt={'30px'} ml={2} mr={2} overflow={'hidden'} position={'relative'} borderRadius={'20px'} sx={{ transition: 'all 0.3s ease-in-out' }}>
        <DarkThemeBackground backgroundVariant={'galaxy'}>
          {/* PAYMENT WAITING STATE */}
          {isWaitingForPayment && currentOrder ? (
            <Grid width={'100%'} p={{ xs: 1.5, sm: 2 }} sx={{ minHeight: { xs: '400px', sm: '500px' }, display: 'flex', flexDirection: 'column', transition: 'all 0.3s ease-in-out' }}>
              {/* Header with back arrow */}
              <Grid pt={1} pb={{ xs: 2, sm: 3 }} display={'flex'} alignItems={'center'} gap={{ xs: 1, sm: 2 }} position={'relative'}>
                <button
                  onClick={() => {
                    if (confirm(t('payment.cancelConfirm') || 'Are you sure you want to cancel?')) {
                      setIsWaitingForPayment(false);
                      setCurrentOrder(null);
                      setTimeLeft(900);
                    }
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: 0,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M19 12H5M5 12L12 19M5 12L12 5" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
                <p className={styles.formHeader} style={{ margin: 0, flex: 1 }}>{t('payment.waitingTitle') || 'Waiting for Payment'}</p>
                
                {/* Selectors Container */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {/* Language Selector */}
                  <div style={{ position: 'relative' }} data-language-selector>
                  <button
                    onClick={() => setIsLanguageMenuOpen(!isLanguageMenuOpen)}
                    style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.15)',
                      border: 'none',
                      borderRadius: '12px',
                      padding: '6px 10px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      fontFamily: 'Gilroy',
                      fontSize: 'clamp(12px, 3vw, 14px)',
                      fontWeight: 600,
                      color: '#fff',
                      minWidth: '100px',
                      transition: 'background-color 0.2s ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.25)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.15)'}
                  >
                    <span style={{ fontSize: '18px' }}>{currentLanguage.flag}</span>
                    <span>{currentLanguage.name}</span>
                  </button>

                  {/* Language Dropdown */}
                  {isLanguageMenuOpen && (
                    <div style={{
                      position: 'absolute',
                      top: '100%',
                      right: 0,
                      marginTop: '8px',
                      backgroundColor: '#fff',
                      borderRadius: '12px',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                      overflow: 'hidden',
                      zIndex: 1000,
                      minWidth: '160px',
                    }}>
                      {languages.map((lang) => (
                        <button
                          key={lang.code}
                          onClick={() => {
                            handleLanguageChange(lang.code);
                            setIsLanguageMenuOpen(false);
                          }}
                          style={{
                            width: '100%',
                            padding: '12px 16px',
                            border: 'none',
                            backgroundColor: lang.code === language ? '#F3F4F6' : '#fff',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            fontFamily: 'Gilroy',
                            fontSize: '14px',
                            fontWeight: lang.code === language ? 600 : 400,
                            color: '#1F2937',
                            transition: 'background-color 0.2s ease',
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F3F4F6'}
                          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = lang.code === language ? '#F3F4F6' : '#fff'}
                        >
                          <span style={{ fontSize: '18px' }}>{lang.flag}</span>
                          <span>{lang.name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  </div>

                  {/* Currency Selector - Disabled on waiting screen */}
                  <div style={{ position: 'relative' }} data-currency-selector>
                    <button
                      disabled={true}
                      style={{
                        position: 'absolute',
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        border: 'none',
                        borderRadius: '12px',
                        padding: '8px 12px',
                        cursor: 'not-allowed',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        fontFamily: 'Gilroy',
                        fontSize: '14px',
                        fontWeight: 600,
                        color: '#fff',
                        minWidth: '120px',
                        opacity: 0.5,
                        transition: 'background-color 0.2s ease',
                      }}
                    >
                      <span>{getCurrencyDisplay()}</span>
                    </button>

                    {/* Currency Dropdown - Never shown on waiting screen */}
                    {false && (
                      <div style={{
                        position: 'absolute',
                        top: '100%',
                        right: 0,
                        marginTop: '8px',
                        backgroundColor: '#fff',
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                        overflow: 'hidden',
                        zIndex: 1000,
                        minWidth: '160px',
                      }}>
                        {(['BYN', 'EUR'] as const).map((curr) => (
                          <button
                            key={curr}
                            onClick={() => {
                              setSelectedCurrency(curr);
                              setLastBepaidCurrency(curr);
                              setIsCurrencyMenuOpen(false);
                            }}
                            style={{
                              width: '100%',
                              padding: '12px 16px',
                              border: 'none',
                              backgroundColor: curr === selectedCurrency ? '#F3F4F6' : '#fff',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '10px',
                              fontFamily: 'Gilroy',
                              fontSize: '14px',
                              fontWeight: curr === selectedCurrency ? 600 : 400,
                              color: '#1F2937',
                              transition: 'background-color 0.2s ease',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F3F4F6'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = curr === selectedCurrency ? '#F3F4F6' : '#fff'}
                          >
                            <span>{curr === 'BYN' ? 'BYN (RUB)' : curr}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
            </Grid>

              {/* Status Alert - only show if succeeded */}
              {currentOrder.status === 'succeeded' && (
                <Alert severity="success" sx={{ mt: 2, mb: 2, borderRadius: '16px' }}>
                  {t('payment.success') || 'Payment completed!'}
                </Alert>
              )}

              {/* Order Details */}
              <Grid sx={{ backgroundColor: '#fff', mt: 2, p: { xs: 1.5, sm: 2.5 }, borderRadius: '12px', mb: 2 }}>
                <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '12px', sm: '14px' }, color: '#6B7280', mb: { xs: 1, sm: 2 }, fontWeight: 600 }}>
                  {t('payment.orderDetails') || 'Order Details'}
                </Typography>
                <Grid display={'flex'} justifyContent={'space-between'} mb={1.5}>
                  <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '12px', sm: '14px' }, color: '#6B7280' }}>
                    {t('payment.orderId') || 'Order ID'}:
                  </Typography>
                  <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '12px', sm: '14px' }, color: '#1F2937', fontWeight: 600 }}>
                    {currentOrder.id.substring(0, 8)}...
                  </Typography>
                </Grid>
                <Grid display={'flex'} justifyContent={'space-between'} mb={1.5}>
                  <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '12px', sm: '14px' }, color: '#6B7280' }}>
                    {t('payment.amount') || 'Amount'}:
                  </Typography>
                  <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '12px', sm: '14px' }, color: '#1F2937', fontWeight: 600 }}>
                    {(() => {
                      const orderTariff = currentOrder.tariff ? tariffs.find(t => t.id === currentOrder.tariff) : null;
                      return formatPriceWithRUB(parseFloat(currentOrder.amount), currency, orderTariff || null);
                    })()}
                  </Typography>
                </Grid>
                <Grid display={'flex'} justifyContent={'space-between'}>
                  <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '12px', sm: '14px' }, color: '#6B7280' }}>
                    {t('payment.paymentMethod') || 'Payment Method'}:
                  </Typography>
                  <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '12px', sm: '14px' }, color: '#1F2937', fontWeight: 600 }}>
                    {currentOrder.pay_system === 'stripe' ? t('payment.stripe') : t('payment.bepaid')}
                  </Typography>
                </Grid>
              </Grid>

              {/* Info Note */}
              <Grid pb={{ xs: 2, sm: 3 }}>
                <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '10px', sm: '12px' }, color: '#ABB0B2', textAlign: 'center' }}>
                  {t('payment.waitingNote') || 'We are waiting for payment confirmation. This usually takes a few seconds.'}
                </Typography>
              </Grid>


              {/* Action Buttons */}
              <Grid display={'flex'} direction={'column'} gap={1.5} sx={{ marginTop: 'auto' }}>
                <button
                  onClick={handleGoToPayment}
                  className={styles.button}
                  style={{
                    width: '100%',
                    border: 'none',
                    outline: 'none',
                    backgroundColor: '#7B3FF2',
                  }}
                >
                  <p className={styles.buttonText}>
                    {t('payment.goToPayment') || 'Go to Payment'}
                  </p>
                </button>
              </Grid>
            </Grid>
          ) : (
            /* PAYMENT FORM STATE */
            <form onSubmit={handleSubmit} style={{ width: '100%' }}>
              <Grid width={'100%'} p={2} sx={{ minHeight: '500px', display: 'flex', flexDirection: 'column', transition: 'all 0.3s ease-in-out' }}>
                <Grid pt={1} pb={3} display={'flex'} alignItems={'center'} position={'relative'}>
                  <p className={styles.formHeader} style={{ flex: 1, margin: 0 }}>{t('payment.title')}</p>
                  
                  {/* Selectors Container */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {/* Language Selector */}
                    <div style={{ position: 'relative' }} data-language-selector>
                    <button
                      type="button"
                      onClick={() => setIsLanguageMenuOpen(!isLanguageMenuOpen)}
                      style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                        border: 'none',
                        borderRadius: '12px',
                        padding: '6px 10px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        fontFamily: 'Gilroy',
                        fontSize: 'clamp(12px, 3vw, 14px)',
                        fontWeight: 600,
                        color: '#fff',
                        minWidth: '100px',
                        transition: 'background-color 0.2s ease',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.25)'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.15)'}
                    >
                      <span style={{ fontSize: '18px' }}>{currentLanguage.flag}</span>
                      <span>{currentLanguage.name}</span>
                    </button>

                    {/* Language Dropdown */}
                    {isLanguageMenuOpen && (
                      <div style={{
                        position: 'absolute',
                        top: '100%',
                        right: 0,
                        marginTop: '8px',
                        backgroundColor: '#fff',
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                        overflow: 'hidden',
                        zIndex: 1000,
                        minWidth: '160px',
                      }}>
                        {languages.map((lang) => (
                          <button
                            key={lang.code}
                            type="button"
                            onClick={() => {
                              handleLanguageChange(lang.code);
                              setIsLanguageMenuOpen(false);
                            }}
                            style={{
                              width: '100%',
                              padding: '12px 16px',
                              border: 'none',
                              backgroundColor: lang.code === language ? '#F3F4F6' : '#fff',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '10px',
                              fontFamily: 'Gilroy',
                              fontSize: '14px',
                              fontWeight: lang.code === language ? 600 : 400,
                              color: '#1F2937',
                              transition: 'background-color 0.2s ease',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F3F4F6'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = lang.code === language ? '#F3F4F6' : '#fff'}
                          >
                            <span style={{ fontSize: '18px' }}>{lang.flag}</span>
                            <span>{lang.name}</span>
                          </button>
                        ))}
                      </div>
                    )}
                    </div>

                    {/* Currency Selector */}
                    <div style={{ position: 'relative' }} data-currency-selector>
                      <button
                        type="button"
                        onClick={() => setIsCurrencyMenuOpen(!isCurrencyMenuOpen)}
                        disabled={paymentMethod === 'stripe'}
                        style={{
                          position: 'absolute',
                          backgroundColor: paymentMethod === 'stripe' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(255, 255, 255, 0.15)',
                          border: 'none',
                          borderRadius: '12px',
                          padding: '8px 12px',
                          cursor: paymentMethod === 'stripe' ? 'not-allowed' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px',
                          fontFamily: 'Gilroy',
                          fontSize: '14px',
                          fontWeight: 600,
                          color: '#fff',
                          minWidth: '120px',
                          opacity: paymentMethod === 'stripe' ? 0.5 : 1,
                          transition: 'background-color 0.2s ease',
                        }}
                        onMouseEnter={(e) => {
                          if (paymentMethod !== 'stripe') {
                            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.25)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (paymentMethod !== 'stripe') {
                            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.15)';
                          }
                        }}
                      >
                        <span>{getCurrencyDisplay()}</span>
                      </button>

                      {/* Currency Dropdown */}
                      {isCurrencyMenuOpen && paymentMethod === 'bepaid' && (
                        <div style={{
                          position: 'absolute',
                          top: '100%',
                          right: 0,
                          marginTop: '8px',
                          backgroundColor: '#fff',
                          borderRadius: '12px',
                          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                          overflow: 'hidden',
                          zIndex: 1000,
                          minWidth: '160px',
                        }}>
                          {(['BYN', 'EUR'] as const).map((curr) => (
                            <button
                              key={curr}
                              type="button"
                              onClick={() => {
                                setSelectedCurrency(curr);
                                setLastBepaidCurrency(curr);
                                setIsCurrencyMenuOpen(false);
                              }}
                              style={{
                                width: '100%',
                                padding: '12px 16px',
                                border: 'none',
                                backgroundColor: curr === selectedCurrency ? '#F3F4F6' : '#fff',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px',
                                fontFamily: 'Gilroy',
                                fontSize: '14px',
                                fontWeight: curr === selectedCurrency ? 600 : 400,
                                color: '#1F2937',
                                transition: 'background-color 0.2s ease',
                              }}
                              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F3F4F6'}
                              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = curr === selectedCurrency ? '#F3F4F6' : '#fff'}
                            >
                              <span>{curr === 'BYN' ? 'BYN (RUB)' : curr}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
            </Grid>

                {/* Email Section */}
              <Grid pb={{ xs: 2, sm: 3 }}>
                <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '14px', sm: '16px' }, color: '#fff', mb: { xs: 1, sm: 1.5 }, fontWeight: 600 }}>
                  {t('payment.emailPlaceholder')}
                </Typography>
                  <Input
                    placeholder={t('payment.emailPlaceholder')}
                    value={email}
                  onChange={setEmail}
                  type="email"
                  />
                </Grid>

              {/* Tariffs Section */}
              {tariffs.length > 0 && (
                <Grid pb={{ xs: 2, sm: 3 }}>
                  <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '14px', sm: '16px' }, color: '#fff', mb: { xs: 1, sm: 1.5 }, fontWeight: 600 }}>
                    {t('payment.selectPlan')}
                  </Typography>
                    <Grid display={'flex'} direction={'column'} gap={1}>
                    {tariffs.map((tariff) => {
                      const isActive = activeTariffCodes.includes(tariff.code);
                      const isSelected = selectedPlan?.id === tariff.id;
                      
                      return (
                        <div
                          key={tariff.id}
                          onClick={() => !isActive && setSelectedPlan(tariff)}
                          style={{
                            padding: 'clamp(12px, 3vw, 16px)',
                            border: isSelected ? '2px solid #7B3FF2' : '2px solid transparent',
                            borderRadius: '12px',
                            cursor: isActive ? 'not-allowed' : 'pointer',
                            transition: 'all 0.3s',
                            backgroundColor: isActive ? 'rgba(255, 167, 38, 0.15)' : '#fff',
                            opacity: isActive ? 0.7 : 1,
                            position: 'relative',
                          }}
                        >
                          <div style={{ display: 'flex', gap: 'clamp(8px, 2vw, 12px)', alignItems: 'flex-start' }}>
                            {/* Radio indicator */}
                            <div style={{
                              width: '20px',
                              height: '20px',
                              borderRadius: '50%',
                              border: isSelected ? '2px solid #7B3FF2' : '2px solid #D1D5DB',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              flexShrink: 0,
                              marginTop: '2px',
                              backgroundColor: '#fff',
                            }}>
                              {isSelected && (
                                <div style={{
                                  width: '10px',
                                  height: '10px',
                                  borderRadius: '50%',
                                  backgroundColor: '#7B3FF2',
                                }}></div>
                              )}
                            </div>
                            
                            <div style={{ flex: 1 }}>
                              <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '14px', sm: '16px' }, color: '#1F2937', fontWeight: 600, mb: 0.5 }}
                                dangerouslySetInnerHTML={{ __html: tariff.title }}
                              />
                              {tariff.public_description && (
                                <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '11px', sm: '13px' }, color: '#6B7280', mb: 0.5, lineHeight: 1.4 }}
                                  dangerouslySetInnerHTML={{ __html: tariff.public_description }}
                                />
                              )}
                              <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '12px', sm: '14px' }, color: '#6B7280' }}>
                                {formatPriceWithRUB(tariff.prices[currency], currency, tariff)} · {t('payment.validity', { days: tariff.validity_days })}
                              </Typography>
                            </div>
                            
                            {isActive && (
                              <Typography sx={{ fontFamily: 'Gilroy', fontSize: '12px', color: '#4CAF50', fontWeight: 600 }}>
                                ✓ {t('payment.paid') || 'Paid'}
                              </Typography>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    </Grid>
                </Grid>
              )}

              {/* Payment Method Section */}
              <Grid pb={{ xs: 2, sm: 3 }}>
                  <Typography sx={{ fontFamily: 'Gilroy', fontSize: { xs: '14px', sm: '16px' }, color: '#fff', mb: { xs: 1, sm: 1.5 }, fontWeight: 600 }}>
                    {t('payment.paymentMethod')}
                  </Typography>
                  <Grid display={'flex'} direction={'row'} gap={{ xs: 1, sm: 2 }}>
                    {[
                      { id: 'stripe', label: t('payment.stripe'), description: t('payment.stripeDescription') },
                      ...(language !== 'en' ? [{ id: 'bepaid', label: t('payment.bepaid'), description: t('payment.bepaidDescription') }] : []),
                    ].map((method) => (
                      <div
                        key={method.id}
                        onClick={() => setPaymentMethod(method.id as 'stripe' | 'bepaid')}
                        style={{
                          padding: 'clamp(12px, 3vw, 16px)',
                          border: paymentMethod === method.id ? '2px solid #7B3FF2' : '2px solid transparent',
                          borderRadius: '12px',
                          cursor: 'pointer',
                          transition: 'all 0.3s',
                          backgroundColor: '#fff',
                          flex: 1,
                          display: 'flex',
                          flexDirection: 'column',
                        }}
                      >
                        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                          {/* Radio indicator */}
                          <div style={{
                            width: '20px',
                            height: '20px',
                            borderRadius: '50%',
                            border: paymentMethod === method.id ? '2px solid #7B3FF2' : '2px solid #D1D5DB',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                            marginTop: '2px',
                            backgroundColor: '#fff',
                          }}>
                            {paymentMethod === method.id && (
                              <div style={{
                                width: '10px',
                                height: '10px',
                                borderRadius: '50%',
                                backgroundColor: '#7B3FF2',
                              }}></div>
                            )}
                          </div>
                          
                          <Typography sx={{ fontFamily: 'Gilroy', fontSize: '16px', color: '#1F2937', fontWeight: 600 }}>
                            {method.label}
                          </Typography>
                        </div>
                        
                        <Typography sx={{ fontFamily: 'Gilroy', fontSize: '13px', color: '#6B7280', lineHeight: 1.4, mt: 'auto', pt: 1.5, pl: '32px', whiteSpace: 'pre-line' }}>
                          {method.description}
                        </Typography>
                      </div>
                    ))}
                  </Grid>
                </Grid>

              {error && <Alert severity="error" sx={{ mb: 2, borderRadius: '16px' }}>{error}</Alert>}
              <Grid pt={2} sx={{ marginTop: 'auto' }}>
                <button
                  type="submit"
                  className={styles.button}
                  style={{ 
                    width: '100%', 
                    opacity: isSubmitting || loading ? 0.5 : 1, 
                    cursor: isSubmitting || loading ? 'not-allowed' : 'pointer',
                    border: 'none',
                    outline: 'none',
                    backgroundColor: '#7B3FF2',
                    position: 'relative',
                  }}
                  disabled={isSubmitting || loading}
                >
                  <p className={styles.buttonText} style={{ position: 'relative', zIndex: 1 }}>
                    {isSubmitting || loading 
                      ? t('payment.processing') 
                      : selectedPlan 
                        ? `${t('payment.pay')} ${formatPriceWithRUB(selectedPlan.prices[currency], currency, selectedPlan)}`
                        : t('payment.pay')
                    }
                  </p>
                  {(isSubmitting || loading) && (
                    <div style={{
                      position: 'absolute',
                      right: '20px',
                      top: '50%',
                      marginTop: '-8px',
                      width: '16px',
                      height: '16px',
                      border: '2px solid rgba(255, 255, 255, 0.3)',
                      borderTop: '2px solid #FFFFFF',
                      borderRadius: '50%',
                      animation: 'spin 0.8s linear infinite',
                    }} />
                  )}
                </button>
                </Grid>

                {/* Load tariffs when email is valid */}
                {email && tariffs.length === 0 && (
                  <Grid pt={2}>
                    <button
                      type="button"
                    className={styles.button}
                      onClick={() => checkUserAndLoadTariffs()}
                      style={{ 
                        width: '100%',
                        position: 'relative',
                        opacity: loading ? 0.5 : 1,
                        cursor: loading ? 'not-allowed' : 'pointer',
                      }}
                      disabled={loading}
                  >
                      <p className={styles.buttonText} style={{ position: 'relative', zIndex: 1 }}>
                        {t('payment.continue')}
                      </p>
                      {loading && (
                        <div style={{
                          position: 'absolute',
                          right: '20px',
                          top: '50%',
                          marginTop: '-8px',
                          width: '16px',
                          height: '16px',
                          border: '2px solid rgba(255, 255, 255, 0.3)',
                          borderTop: '2px solid #FFFFFF',
                          borderRadius: '50%',
                          animation: 'spin 0.8s linear infinite',
                        }} />
                      )}
                    </button>
                </Grid>
            )}
          </Grid>
            </form>
          )}
        </DarkThemeBackground>
      </Grid>

      {/* Support button - outside form container */}
      {isWaitingForPayment && currentOrder && (
        <Grid mt={2} width={'600px'} maxWidth={'100%'} ml={2} mr={2}>
          <a
            href="https://t.me/DeepSkySchoolBot"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'block',
              width: '100%',
              textDecoration: 'none',
            }}
          >
            <button
              type="button"
              className={styles.button}
              style={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
              }}
            >
              <p className={styles.buttonText}>
                {t('payment.contactSupport') || 'Написать в поддержку'}
              </p>
            </button>
          </a>
        </Grid>
      )}
    </Grid>
  );
}

export default PaymentForm;

