// Total of a cart line in cents: unit price times quantity, minus a percentage discount.
export function lineTotal(unitCents, quantity, discountPercent = 0) {
  const gross = unitCents * quantity;
  return Math.round(gross * (1 - discountPercent / 100));
}
