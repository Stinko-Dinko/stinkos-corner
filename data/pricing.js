/* Stinko's Corner variant pricing. Workbook Price Entry is the only source of prices. */
(function(){'use strict';
 const S=()=>window.STINKO_CATALOG||window.STINKOS_CATALOG||{};
 const money=n=>'$'+Number(n).toFixed(2);
 const sizeOptions=p=>(S().size_options||[]).filter(x=>x.product_type===p.product_type);
 const materialOptions=p=>p.product_type==='decal'?(S().vinyl_options||[]):String(p.product_type||'').includes('sticker')?(S().sticker_finishes||[]):[];
 const optionKey=(p,o)=>p.product_type==='decal'?(o.vinyl_option_id||o.id):(o.finish_id||o.id);
 const priceFor=(cat,p,sizeId,materialId)=>{const override=Number(p.price_override);if(p.price_override!==null&&p.price_override!==undefined&&p.price_override!==''&&Number.isFinite(override))return override;
 if(!sizeId)return null;const choices=materialOptions(p);if(choices.length&&!materialId)return null;
 const material=choices.find(x=>optionKey(p,x)===materialId);if(choices.length&&(!material||!material.available))return null;
 const size=sizeOptions(p).find(x=>x.size_id===sizeId);if(!size||!size.available)return null;
 const tier=material?.pricing_tier||'Standard';const found=(cat.pricing_rules||[]).find(x=>x.product_type===p.product_type&&x.size_id===sizeId&&x.pricing_tier===tier);return found&&Number.isFinite(Number(found.price))?Number(found.price):null};
 const startingPrice=(cat,p)=>{if(p.price_override!==null&&p.price_override!==undefined&&p.price_override!==''&&Number.isFinite(Number(p.price_override)))return Number(p.price_override);const sizes=sizeOptions(p).filter(x=>x.available),opts=materialOptions(p).filter(x=>x.available);const all=[];for(const s of sizes){if(!opts.length){let v=priceFor(cat,p,s.size_id,'');if(v!==null)all.push(v)}else for(const m of opts){let v=priceFor(cat,p,s.size_id,optionKey(p,m));if(v!==null)all.push(v)}}return all.length?Math.min(...all):null};
 const listPrice=(cat,p)=>{const v=startingPrice(cat,p);return v===null?'Price not set':'From '+money(v)};
 window.STINKO_PRICING={money,sizeOptions,materialOptions,optionKey,priceFor,startingPrice,listPrice};
})();
