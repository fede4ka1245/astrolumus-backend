import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function PaymentRedirect() {
  const router = useRouter();

  useEffect(() => {
    const detectLanguage = () => {
      // Try to get language from browser
      const browserLang = navigator.language.toLowerCase();
      
      // Map browser languages to supported languages
      let lang = 'en'; // Default
      
      if (browserLang.startsWith('ru')) {
        lang = 'ru';
      } else if (browserLang.startsWith('uk')) {
        lang = 'uk';
      } else if (browserLang.startsWith('pl')) {
        lang = 'pl';
      } else if (browserLang.startsWith('be')) {
        lang = 'be';
      }
      
      console.log('🌍 Detected language:', browserLang, '→', lang);
      
      // Preserve query parameters (like email) during redirect
      const queryString = router.asPath.includes('?') ? router.asPath.split('?')[1] : '';
      const redirectUrl = queryString ? `/payment/${lang}?${queryString}` : `/payment/${lang}`;
      
      // Redirect to language-specific page
      router.replace(redirectUrl);
    };

    detectLanguage();
  }, [router]);

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
        <div style={{ fontSize: '40px', marginBottom: '20px' }}>🌍</div>
        <p style={{ color: '#ABB0B2' }}>Detecting language...</p>
      </div>
    </div>
  );
}

