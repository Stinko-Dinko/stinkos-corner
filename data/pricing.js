/* Stinko's Corner: single pricing lookup for catalog-backed storefront pages.
   Prices come only from Price Entry (via pricing_rules) or an explicit
   Products.price_override. No inferred prices or zero-dollar fallbacks. */
window.STINKO_PRICING = (() => {
  const numeric = (v) => typeof v === 'number' && Number.isFinite(v);
  const money = (v) => numeric(v) ? new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD'
  }).format(v) : null;
  const sizeOptions = (p) => (p.size_options || []).filter(o => o && o.size_id);
  const materialOptions = (p) => p.product_type === 'decal'
    ? (p.vinyl_options || [])
    : ['sticker', 'sticker sheet', 'sticker multi-pack'].includes(p.product_type)
      ? (p.finish_options || []) : [];
  const optionKey = (p, o) => p.product_type === 'decal' ? o.vinyl_option_id : o.finish_id;
  function priceFor(catalog, p, sizeId, optionId) {
    if (!p || !sizeId) return null;
    const size = sizeOptions(p).find(o => o.size_id === sizeId);
    if (!size || !size.available) return null;
    const options = materialOptions(p);
    let tier = 'Standard';
    if (options.length) {
      const option = options.find(o => optionKey(p, o) === optionId);
      if (!option || !option.available) return null;
      tier = option.pricing_tier;
    }
    if (numeric(p.price_override)) return p.price_override;
    const rule = (catalog?.pricing_rules || []).find(r =>
      r.product_type === p.product_type && r.size_id === sizeId && r.pricing_tier === tier
    );
    return rule && numeric(rule.price) ? rule.price : null;
  }
  function startingPrice(catalog, p) {
    if (!p) return null;
    if (numeric(p.price_override)) return p.price_override;
    if (numeric(p.starting_price)) return p.starting_price;
    const prices = [];
    const options = materialOptions(p);
    for (const size of sizeOptions(p)) {
      if (!size.available) continue;
      if (options.length) {
        for (const opt of options) {
          if (!opt.available) continue;
          const n = priceFor(catalog, p, size.size_id, optionKey(p, opt));
          if (numeric(n)) prices.push(n);
        }
      } else {
        const n = priceFor(catalog, p, size.size_id, null);
        if (numeric(n)) prices.push(n);
      }
    }
    return prices.length ? Math.min(...prices) : null;
  }
  function listPrice(catalog, p) {
    const min = startingPrice(catalog, p);
    if (!numeric(min)) return 'Price not set';
    const max = p.price_max;
    return (numeric(max) && max > min ? 'From ' : '') + money(min);
  }
  return { money, sizeOptions, materialOptions, optionKey, priceFor, startingPrice, listPrice };
})();
