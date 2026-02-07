import React from 'react';
import PaymentForm from '@/components/paymentForm/PaymentForm';

interface Props {
  lang: string;
}

export const getServerSideProps = async (context: any) => {
  const { lang } = context.params;
  const { email } = context.query;

  const validLanguages = ['en', 'ru', 'uk', 'pl', 'be'];
  if (!validLanguages.includes(lang)) {
    return {
      notFound: true,
    };
  }

  return {
    props: {
      lang,
      initialEmail: email || '',
    },
  };
};

const PaymentPage = ({ lang, initialEmail }: Props & { initialEmail: string }) => {
  return <PaymentForm initialEmail={initialEmail} language={lang} />;
};

export default PaymentPage;


