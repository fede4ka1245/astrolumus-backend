import React from 'react';
import {ParsedUrlData, parseHoroscopeUrl} from "@/helpers/horoscopeUrl";
import getOgImage from "@/helpers/getOgImage";
import HoroscopeForm from "@/components/horoscopeForm/HoroscopeForm";

interface Props {
  horoscope?: ParsedUrlData,
  image?: string
}

const HOROSCOPE_PARAMS = ['date', 'name', 'city', 'latitude', 'longitude', 'time'];

const hasHoroscopeParams = (query: Record<string, any>): boolean => {
  return HOROSCOPE_PARAMS.some(param => param in query && query[param]);
};

export const getServerSideProps = async (context: any) => {
  const { query, resolvedUrl } = context;
  
  if (hasHoroscopeParams(query)) {
    const queryString = resolvedUrl.includes('?') ? resolvedUrl.split('?')[1] : '';
    return {
      redirect: {
        destination: `/horoscope${queryString ? '?' + queryString : ''}`,
        permanent: false,
      },
    };
  }
  
  return {
    redirect: {
      destination: '/payment/en',
      permanent: false,
    },
  };
};

const Horoscope = ({ horoscope, image }: Props) => {
  return (
    <div>
      <HoroscopeForm horoscope={horoscope} image={image} />
    </div>
  );
};

export default Horoscope;