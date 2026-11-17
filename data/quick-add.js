/* Quick-add popup for catalog and homepage product cards. No product details page navigation. */
(() => {
  'use strict';
  const catalog = window.STINKOS_CATALOG;
  const pricing = window.STINKO_PRICING;
  if (!catalog || !pricing) return;

  const style = document.createElement('style');
  style.textContent = [
    '.stinko-quickadd{border:3px solid #111;padding:0;width:min(540px,calc(100vw - 28px));max-height:90vh;overflow:auto;color:#111;background:#fff;box-shadow:8px 8px 0 #111;font-family:Nunito,Arial,sans-serif}',
    '.stinko-quickadd::backdrop{background:rgba(0,0,0,.56)}',
    '.stinko-quickadd-panel{padding:22px}',
    '.stinko-quickadd-heading{display:flex;justify-content:space-between;gap:16px;align-items:start;margin-bottom:15px}',
    '.stinko-quickadd h2{font:900 1.5rem/1.2 Nunito,Arial,sans-serif;text-transform:uppercase;margin:0}',
    '.stinko-quickadd-close{flex:none;width:36px;height:36px;border:2px solid #111;background:#fff;color:#111;font-size:24px;cursor:pointer}',
    '.stinko-quickadd-product{display:flex;align-items:center;gap:15px;margin:0 0 20px}',
    '.stinko-quickadd-product img{height:96px;width:96px;object-fit:contain;background:#f5f5f5;flex:none}',
    '.stinko-quickadd-price{font-weight:900;font-size:1.25rem}',
    '.stinko-quickadd label{display:block;font-weight:900;margin:0 0 15px}',
    '.stinko-quickadd label span{display:block;margin-bottom:6px}',
    '.stinko-quickadd select,.stinko-quickadd input{border:2px solid #111;border-radius:0;background:white;color:#111;min-height:44px;padding:8px;width:100%;font:800 1rem Nunito,Arial,sans-serif}',
    '.stinko-quickadd-quantity{max-width:120px}',
    '.stinko-quickadd-submit{width:100%;border:3px solid #111;background:#a6ed36;color:#111;font:1.25rem Knewave,Nunito,sans-serif;padding:12px;cursor:pointer}',
    '.stinko-quickadd-submit:disabled{opacity:.48;cursor:not-allowed}',
    '.stinko-quickadd-footer{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-top:14px}',
    '.stinko-quickadd-footer a{font-weight:900;text-decoration:underline;color:#111}',
    '.stinko-quickadd-feedback{font-size:.9rem;font-weight:800;min-height:1.3em;margin:10px 0 0}'
  ].join('\n');
  document.head.appendChild(style);

  const dialog = document.createElement('dialog');
  dialog.className = 'stinko-quickadd';
  dialog.setAttribute('aria-label', 'Choose product options');
  dialog.innerHTML = '<div class="stinko-quickadd-panel"><div class="stinko-quickadd-heading"><h2 id="stinko-qa-name"></h2><button class="stinko-quickadd-close" type="button" aria-label="Close quick add">×</button></div><div class="stinko-quickadd-product"><img id="stinko-qa-photo" alt=""><div class="stinko-quickadd-price" id="stinko-qa-price"></div></div><div id="stinko-qa-fields"></div><label><span>Quantity</span><input class="stinko-quickadd-quantity" id="stinko-qa-qty" type="number" min="1" max="99" value="1" step="1"></label><button id="stinko-qa-add" class="stinko-quickadd-submit" type="button" disabled>ADD TO CART</button><p class="stinko-quickadd-feedback" id="stinko-qa-feedback" role="status"></p><div class="stinko-quickadd-footer"><a id="stinko-qa-details" href="#">View product details</a><button class="stinko-quickadd-close" type="button">Continue browsing</button></div></div>';
  document.body.appendChild(dialog);

  const el = id => dialog.querySelector('#' + id);
  const name = el('stinko-qa-name');
  const img = el('stinko-qa-photo');
  const price = el('stinko-qa-price');
  const fields = el('stinko-qa-fields');
  const qty = el('stinko-qa-qty');
  const add = el('stinko-qa-add');
  const feedback = el('stinko-qa-feedback');
  const details = el('stinko-qa-details');
  let product = null, selectedSize = '', selectedOption = '';

  dialog.querySelectorAll('.stinko-quickadd-close').forEach(button => button.addEventListener('click', () => dialog.close()));
  dialog.addEventListener('click', event => {if (event.target === dialog) dialog.close();});

  function field(label, items, onChange) {
    const wrapper = document.createElement('label');
    const caption = document.createElement('span');
    caption.textContent = label;
    const select = document.createElement('select');
    select.setAttribute('aria-label', label);
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Choose ' + label.toLowerCase();
    select.appendChild(placeholder);
    items.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.value;
      opt.textContent = item.label + (item.available ? '' : ' (Out of stock)');
      opt.disabled = !item.available;
      select.appendChild(opt);
    });
    select.addEventListener('change', () => {onChange(select.value);update();});
    wrapper.append(caption, select);
    fields.appendChild(wrapper);
  }

  function selectedPrice() {
    return pricing.priceFor(catalog, product, selectedSize, selectedOption);
  }
  function update() {
    const selected = selectedPrice();
    const first = pricing.startingPrice(catalog, product);
    price.textContent = selected !== null ? pricing.money(selected) : first !== null ? 'From ' + pricing.money(first) : 'Price not set';
    const amount = Number(qty.value);
    add.disabled = selected === null || !Number.isInteger(amount) || amount < 1 || amount > 99;
    feedback.textContent = selected === null ? 'Select available options to see the final price.' : '';
  }
  qty.addEventListener('input', update);

  function open(productId) {
    product = (catalog.products || []).find(p => p.product_id === productId);
    if (!product) return;
    selectedSize = '';
    selectedOption = '';
    fields.replaceChildren();
    name.textContent = product.title || 'Product';
    details.href = 'product.html?slug=' + encodeURIComponent(product.slug || product.product_id);
    qty.value = '1';
    feedback.textContent = '';
    const photo = (product.images || [])[0] || '';
    const imagePath = photo.replace(/^images\/products\//, 'images/cards/').replace(/\.(?:jpe?g|png)$/i, '.webp');
    img.src = imagePath;
    img.alt = product.image_alt_text || product.title || '';
    const sizes = pricing.sizeOptions(product);
    field('Size', sizes.map(size => ({value:size.size_id,label:size.label || size.size_id,available:!!size.available})), value => {selectedSize = value;});
    const materials = pricing.materialOptions(product);
    if (materials.length) {
      const isDecal = product.product_type === 'decal';
      field(isDecal ? 'Color / finish' : 'Finish', materials.map(material => ({
        value:pricing.optionKey(product,material),
        label:isDecal ? [material.color,material.finish].filter(Boolean).join(' / ') : material.name,
        available:!!material.available
      })), value => {selectedOption = value;});
    }
    update();
    dialog.showModal();
  }

  add.addEventListener('click', () => {
    const unitPrice = selectedPrice();
    const amount = Number(qty.value);
    if (!product || unitPrice === null || !Number.isInteger(amount) || amount < 1 || amount > 99) return;
    let cart = [];
    try {cart = JSON.parse(localStorage.getItem('stinkos_preview_cart') || '[]');} catch {}
    const variantKey = [product.product_id, selectedSize, selectedOption].join('|');
    const old = cart.find(item => item.variant_key === variantKey);
    if (old) old.quantity += amount;
    else cart.push({variant_key:variantKey,product_id:product.product_id,slug:product.slug,title:product.title,size_id:selectedSize,option_id:selectedOption,price:unitPrice,quantity:amount,preorder:false});
    localStorage.setItem('stinkos_preview_cart', JSON.stringify(cart));
    const count = cart.reduce((sum,item) => sum + Number(item.quantity || 0),0);
    document.querySelectorAll('.cart-btn').forEach(button => {button.textContent = 'CART (' + count + ')';});
    feedback.textContent = amount + ' added to cart.';
    add.textContent = 'ADDED TO CART';
    add.disabled = true;
    setTimeout(() => {if (dialog.open) dialog.close(); add.textContent = 'ADD TO CART';}, 650);
  });

  document.addEventListener('click', event => {
    const button = event.target.closest('.shop-card-action,.product-hover-action');
    if (!button || button.disabled || !/add to cart/i.test(button.textContent || '')) return;
    const id = button.dataset.product || button.closest('.product-card')?.dataset.productId;
    if (!id) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    open(decodeURIComponent(id));
  }, true);
  document.addEventListener('keydown', event => {
    const button = event.target.closest('.product-hover-action');
    if (!button || !['Enter',' '].includes(event.key) || !/add to cart/i.test(button.textContent || '')) return;
    const id = button.closest('.product-card')?.dataset.productId;
    if (!id) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    open(id);
  }, true);
})();