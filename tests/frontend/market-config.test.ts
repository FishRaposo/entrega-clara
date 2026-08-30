import { brazilMarket, internationalMarket } from "../../app/web/src/lib/market-config";

test("Brazil is the default market configuration", () => {
  expect(brazilMarket.locale).toBe("pt-BR");
  expect(brazilMarket.currency).toBe("BRL");
  expect(brazilMarket.paymentMethods).toContain("pix");
  expect(brazilMarket.location.label).toBe("Área central de São Paulo, SP");
});

test("Toronto configuration is internally coherent for Canada", () => {
  expect(internationalMarket.id).toBe("ca");
  expect(internationalMarket.locale).toBe("en-CA");
  expect(internationalMarket.currency).toBe("CAD");
  expect(internationalMarket.paymentMethods).not.toContain("pix");
  expect(internationalMarket.privacyRegime).toBe("Applicable Canadian privacy law");
  expect(internationalMarket.location.label).toBe("Downtown Toronto, ON");
  expect(internationalMarket.location.countryCode).toBe("CA");
  expect(internationalMarket.location.addressFormat).toBe("street, city, province, postal code");
  expect(internationalMarket.timezone).toBe("America/Toronto");
});
