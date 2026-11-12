/* Workbook-controlled site navigation. Existing styles and cursor are unchanged. */
(() => {
 'use strict';
 const catalog=window.STINKOS_CATALOG||window.STINKO_CATALOG||{};
 const review=new URLSearchParams(location.search).get('preview')==='1';
 const reviewUrl=href=>{if(!review)return href;const u=new URL(href,location.href);if(u.origin!==location.origin)return href;u.searchParams.set('preview','1');return u.pathname.split('/').pop()+u.search+u.hash};
 const home=/(?:^|\/)index\.html$/.test(location.pathname)||location.pathname.endsWith('/');
 const homeSection=id=>(home?'':'index.html')+'#'+id;
 const paths={
  'new arrivals':'new-arrivals.html','shop all new':'new-arrivals.html',
  'shop all':'shop-all.html','shop all collections':'shop-all.html',
  'sticker packs':'sticker-packs.html','limited editions':'limited-editions.html',
  'pre-orders':'pre-orders.html','coming soon':homeSection('coming-soon'),
  'collections':homeSection('collections'),'characters':homeSection('characters'),
  'about stinko\'s corner':'about.html','wholesale':'wholesale.html',
  'stockists':'stockists.html','press':'press.html','faq':'faq.html',
  'shipping':'shipping.html','returns':'returns.html',
  'shipping & returns':'shipping-returns.html','contact':'contact.html',
  'accessibility':'accessibility.html','privacy policy':'privacy.html',
  'terms':'terms.html','home':'index.html','cart':'cart.html'
 };
 document.querySelectorAll('.logo a').forEach(a=>a.href='index.html');
 document.querySelectorAll('.cart-btn').forEach(a=>a.href='cart.html');
 document.querySelectorAll('a[href]').forEach(a=>{
  if(a.closest('.stinko-footer-socials,.social-post-grid,.dropdown-menu'))return;
  if(a.closest('.product-card,.shop-card')||a.classList.contains('cart-btn'))return;
  const key=a.textContent.trim().replace(/\s+/g,' ').toLowerCase();
  if(paths[key])a.setAttribute('href',paths[key]);
 });
 const groups=[...document.querySelectorAll('header nav > ul > li')];
 const ordered=(arr,field)=>(arr||[]).filter(x=>x.active).sort((a,b)=>(Number(a[field])||9999)-(Number(b[field])||9999));
 const categories=ordered(catalog.categories,'display_order');
 const collections=ordered(catalog.collections,'homepage_position');
 const characters=ordered(catalog.characters,'homepage_position');
 const buildMenu=(group,items,createUrl)=>{
  const ul=group?.querySelector('.dropdown-menu');if(!ul)return;
  ul.replaceChildren();
  for(const item of items){
   const li=document.createElement('li'),a=document.createElement('a');
   a.textContent=item.name;a.href=createUrl(item);li.appendChild(a);ul.appendChild(li);
  }
  if(!items.length)ul.style.display='none';
  else ul.style.removeProperty('display');
 };
 if(groups.length>=4){
  const first=groups[0].querySelector('a');if(first){first.textContent='New Arrivals';first.href='new-arrivals.html'}
  buildMenu(groups[0],[],()=> '');
  const shop=groups[1].querySelector('a');if(shop){shop.textContent='Shop All';shop.href='shop-all.html'}
  buildMenu(groups[1],categories,item=>'category.html?id='+encodeURIComponent(item.slug||item.category_id));
  const col=groups[2].querySelector('a');if(col){col.textContent='Collections';col.href=homeSection('collections')}
  buildMenu(groups[2],collections,item=>'collection.html?collection='+encodeURIComponent(item.slug||item.collection_id));
  const ch=groups[3].querySelector('a');if(ch){ch.textContent='Characters';ch.href=homeSection('characters')}
  buildMenu(groups[3],characters,item=>'character.html?id='+encodeURIComponent(item.slug||item.character_id));
 }
 // Exactly three workbook-assigned homepage collection slots. No invented replacements.
 const positions=collections.filter(x=>[1,2,3].includes(Number(x.homepage_position)));
 document.querySelectorAll('#collections .collection-card').forEach((card,i)=>{
  const col=positions[i],a=card.querySelector('.collection-btn');if(!col)return;
  const url='collection.html?collection='+encodeURIComponent(col.slug||col.collection_id);
  if(a)a.href=url;
  const frame=card.querySelector('.burst-frame');if(frame){frame.style.cursor='pointer';frame.tabIndex=0;frame.setAttribute('role','link');frame.setAttribute('aria-label','Shop '+col.name);frame.onclick=()=>location.assign(reviewUrl(url));frame.onkeydown=e=>{if(e.key==='Enter')location.assign(reviewUrl(url))}}
 });
 const byCharacter=ch=>(catalog.products||[]).filter(p=>p.active===true&&p.status!=='Draft'&&p.character_id===ch.character_id);
 document.querySelectorAll('#characters .character-card').forEach((card,i)=>{
  const key=card.dataset.characterId||characters[i]?.character_id;
  const ch=characters.find(x=>x.character_id===key||x.slug===key);if(!ch)return;
  const matches=byCharacter(ch);
  // A single actual product goes to its detail page. Otherwise open that character's shopping page.
  const url=matches.length===1?'product.html?slug='+encodeURIComponent(matches[0].slug||matches[0].product_id):'character.html?id='+encodeURIComponent(ch.slug||ch.character_id);
  card.setAttribute('role','link');card.tabIndex=0;card.setAttribute('aria-label','Shop '+ch.name);
  card.onclick=e=>{if(e.target.closest('button,a'))return;location.assign(reviewUrl(url))};
  card.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();location.assign(reviewUrl(url))}};
 });
 // These cards are bound to products by the homepage catalog script.
 document.querySelectorAll('a.product-card[data-product-slug]').forEach(a=>{
  const slug=a.dataset.productSlug;if(slug)a.href='product.html?slug='+encodeURIComponent(slug);
 });
 // Quick add never guesses a variant. Single priced variant adds one; multi-variant items open details.
 const pricing=window.STINKO_PRICING;
 function uniqueReadyVariant(product){
  if(!pricing)return null;
  const sizes=pricing.sizeOptions(product).filter(o=>o.available);
  const options=pricing.materialOptions(product).filter(o=>o.available);
  const pairs=[];
  for(const s of sizes)for(const o of (options.length?options:[null])){
   const oid=o?pricing.optionKey(product,o):null;
   const price=pricing.priceFor(catalog,product,s.size_id,oid);
   if(price!==null)pairs.push({size:s.size_id,option:oid,price});
   if(pairs.length>1)return null;
  }
  return pairs.length===1?pairs[0]:null;
 }
 function quickAdd(product,variant){
  let cart=[];try{cart=JSON.parse(localStorage.getItem('stinkos_preview_cart')||'[]')}catch{}
  const k=[product.product_id,variant.size,variant.option].join('|');
  const item=cart.find(x=>x.variant_key===k);
  if(item)item.quantity+=1;
  else cart.push({variant_key:k,product_id:product.product_id,slug:product.slug,title:product.title,size_id:variant.size,option_id:variant.option,price:variant.price,quantity:1,preorder:false});
  localStorage.setItem('stinkos_preview_cart',JSON.stringify(cart));
  document.querySelectorAll('.cart-btn').forEach(a=>a.textContent='CART ('+cart.reduce((n,x)=>n+Number(x.quantity||0),0)+')');
 }
 let count=0;try{const cart=JSON.parse(localStorage.getItem('stinkos_preview_cart')||'[]');count=cart.reduce((n,x)=>n+Number(x.quantity||0),0)}catch{}
 document.querySelectorAll('.cart-btn').forEach(a=>a.textContent='CART ('+count+')');
 // Shared quick-add action. No price or variant is guessed when unavailable.
 const dialog=document.createElement('dialog');
 dialog.id='stinko-quick-add-dialog';
 dialog.setAttribute('aria-label','Choose product options');
 dialog.style.cssText='border:4px solid #111;background:#fff;color:#111;padding:28px;box-shadow:9px 9px 0 #111;max-width:min(530px,92vw);font:800 16px Nunito,sans-serif';
 dialog.innerHTML='<form method="dialog"><button value="cancel" aria-label="Close" style="float:right;cursor:pointer;background:#111;color:white;border:0;padding:7px 13px">✕</button><h2 id="stinko-quick-title" style="font:28px Knewave,cursive;margin:0 38px 16px 0"></h2><p id="stinko-quick-note" style="margin-bottom:12px"></p><div id="stinko-quick-controls" style="display:grid;gap:14px"></div><button type="button" id="stinko-quick-confirm" style="margin-top:18px;border:3px solid #111;background:#9df028;font:20px Knewave,cursive;padding:12px 20px;cursor:pointer">ADD TO CART</button></form>';
 document.body.appendChild(dialog);
 const selector=(label,opts)=>{
  const wrap=document.createElement('label');wrap.style.cssText='display:grid;gap:5px';wrap.textContent=label;
  const select=document.createElement('select');select.style.cssText='width:100%;border:3px solid #111;padding:10px;background:#fff';
  for(const x of opts){const o=document.createElement('option');o.value=x.id;o.textContent=x.label;select.appendChild(o)}
  wrap.appendChild(select);return {wrap,select};
 };
 let chosenProduct=null;
 const quickTitle=dialog.querySelector('#stinko-quick-title');
 const note=dialog.querySelector('#stinko-quick-note');
 const controls=dialog.querySelector('#stinko-quick-controls');
 const confirm=dialog.querySelector('#stinko-quick-confirm');
 function openQuick(product){
  if(!product||!product.active||product.status==='Draft')return;
  chosenProduct=product;quickTitle.textContent=product.title;controls.replaceChildren();
  const sizes=pricing?.sizeOptions(product).filter(o=>o.available)||[];
  const materials=pricing?.materialOptions(product).filter(o=>o.available)||[];
  let sizeControl=null, optionControl=null;
  if(sizes.length){const control=selector('Size',sizes.map(o=>({id:o.size_id,label:o.label})));controls.appendChild(control.wrap);sizeControl=control.select}
  if(materials.length){const control=selector(product.product_type==='decal'?'Color / finish':'Finish',materials.map(o=>({id:pricing.optionKey(product,o),label:product.product_type==='decal'?(o.color+' / '+o.finish):(o.name||o.label||o.finish_id)})));controls.appendChild(control.wrap);optionControl=control.select}
  const refresh=()=>{
   const cost=pricing?.priceFor(catalog,product,sizeControl?.value||null,optionControl?.value||null);
   confirm.disabled=cost===null||cost===undefined;
   confirm.style.opacity=confirm.disabled?'0.4':'1';
   note.textContent=cost===null||cost===undefined?'Price unavailable for this combination. Complete Price Entry before selling.':'Price: '+pricing.money(cost);
  };
  sizeControl?.addEventListener('change',refresh);optionControl?.addEventListener('change',refresh);
  refresh();
  confirm.onclick=()=>{
   const size=sizeControl?.value||null,option=optionControl?.value||null;
   const cost=pricing.priceFor(catalog,product,size,option);
   if(cost===null)return;
   quickAdd(product,{size,option,price:cost});dialog.close();
  };
  if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');
 }
 // The approved homepage product-card appearance stays unchanged.
 document.querySelectorAll('#new-arrivals .product-card,#coming-soon .product-card').forEach(card=>{
  const slug=card.dataset.productSlug;
  const product=(catalog.products||[]).find(x=>x.slug===slug||x.product_id===slug);
  const action=card.querySelector('.product-hover-action');if(!action||!product)return;
  card.href='product.html?slug='+encodeURIComponent(product.slug||product.product_id);
  const upcoming=!!card.closest('#coming-soon')||product.status==='Coming Soon';
  action.textContent=upcoming?'COMING SOON':'ADD TO CART';
  action.setAttribute('role','button');action.tabIndex=0;
  action.setAttribute('aria-label',action.textContent+' '+product.title);
  const activate=e=>{
   e.preventDefault();e.stopPropagation();
   if(upcoming)return;
   const single=uniqueReadyVariant(product);
   if(single){quickAdd(product,single);action.textContent='ADDED!';setTimeout(()=>action.textContent='ADD TO CART',900)}
   else openQuick(product);
  };
  action.addEventListener('click',activate);
  action.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' ')activate(e)});
 });
 // Shopping-grid hover buttons are independent of the image/title link.
 document.addEventListener('click',e=>{
  const btn=e.target.closest('.shop-card-action');if(!btn)return;
  const product=(catalog.products||[]).find(p=>p.slug===btn.dataset.slug||p.product_id===btn.dataset.slug);
  if(!product)return;
  if(review&&!product.active){e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();location.assign(reviewUrl('product.html?slug='+encodeURIComponent(product.slug||product.product_id)));return;}
  if(!product.active)return;
  e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();
  if(product.status==='Coming Soon')return;
  const single=uniqueReadyVariant(product);
  if(single){quickAdd(product,single);btn.textContent='ADDED!';setTimeout(()=>btn.textContent='ADD TO CART',900)}
  else openQuick(product);
 },true);
 // Change grid hover-button label only where an item can be bought; never claim Draft is purchasable.
 const observer=new MutationObserver(()=>document.querySelectorAll('.shop-card-action').forEach(btn=>{
  if(btn.dataset.quickReady)return;
  const product=(catalog.products||[]).find(p=>p.slug===btn.dataset.slug||p.product_id===btn.dataset.slug);
  if(product?.active && product.status!=='Draft')btn.textContent='ADD TO CART';
  btn.dataset.quickReady='true';
 }));
 document.querySelectorAll('#shop-grid').forEach(grid=>observer.observe(grid,{childList:true}));
 if(review){
  const marker=document.createElement('div');marker.textContent='REVIEW MODE: Draft products are shown for inspection only. Cart and checkout are not live.';
  marker.style.cssText='background:#fff4b9;color:#111;border-bottom:3px solid #111;padding:10px 20px;font:800 13px Nunito,sans-serif;text-align:center';
  document.querySelector('.marquee-green')?.after(marker);
  document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.defaultPrevented||a.target==='_blank'||e.ctrlKey||e.metaKey)return;const href=a.getAttribute('href');if(!href||href.startsWith('#')||/^(https?:|mailto:|tel:|javascript:)/i.test(href))return;let u;try{u=new URL(href,location.href)}catch{return}if(u.origin!==location.origin||!u.pathname.endsWith('.html'))return;e.preventDefault();location.assign(reviewUrl(href))},true);
 }
  // Single-photo cards must keep their primary image visible on hover.
  // Two-photo cards retain their existing approved primary/secondary crossfade.
  const singlePhotoStyle=document.createElement('style');
  singlePhotoStyle.textContent='.shop-card:not(:has(.shop-burst-img.secondary)):hover .shop-burst-img.primary,.shop-card:not(:has(.shop-burst-img.secondary)):focus-within .shop-burst-img.primary{opacity:1}';
  document.head.appendChild(singlePhotoStyle);
})();
