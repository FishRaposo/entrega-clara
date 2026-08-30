export type MarketConfig = {
  id: string;
  locale: string;
  currency: string;
  timezone: string;
  paymentMethods: readonly string[];
  privacyRegime: string;
  location: {
    label: string;
    countryCode: string;
    addressFormat: string;
  };
};

export const brazilMarket: MarketConfig = {
  id: "br",
  locale: "pt-BR",
  currency: "BRL",
  timezone: "America/Sao_Paulo",
  paymentMethods: ["pix", "card", "wallet"],
  privacyRegime: "LGPD",
  location: {
    label: "Área central de São Paulo, SP",
    countryCode: "BR",
    addressFormat: "bairro, cidade, UF",
  },
};

export const internationalMarket: MarketConfig = {
  id: "ca",
  locale: "en-CA",
  currency: "CAD",
  timezone: "America/Toronto",
  paymentMethods: ["card", "wallet"],
  privacyRegime: "Applicable Canadian privacy law",
  location: {
    label: "Downtown Toronto, ON",
    countryCode: "CA",
    addressFormat: "street, city, province, postal code",
  },
};
