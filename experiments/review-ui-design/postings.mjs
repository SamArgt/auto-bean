const UNIT=100000000n;
export function decimal(value){
 const text=String(value).trim();
 if(!/^[+-]?\d+(?:\.\d{1,8})?$/.test(text))throw new Error('Use a decimal with up to 8 decimal places.');
 const negative=text.startsWith('-'),parts=text.replace(/^[+-]/,'').split('.');
 return (negative?-1n:1n)*(BigInt(parts[0])*UNIT+BigInt((parts[1]??'').padEnd(8,'0')));
}
export function checkPostings(s,r,ps){
 const errors=[],totals=new Map();let source=0n;
 if(ps.length<2)errors.push('Keep at least two postings.');
 ps.forEach((p,i)=>{try{
  if(!/^(Assets|Liabilities|Equity|Income|Expenses)(?::[A-Z][A-Za-z0-9-]*)+$/.test(p.account.trim()))throw new Error('Enter a full ledger account such as Expenses:Dining.');
  if(!/^[A-Z][A-Z0-9._-]*$/.test(p.currency.trim()))throw new Error('Enter a currency or commodity such as EUR or VWCE.');
  const amount=decimal(p.amount);let currency=p.currency.trim(),weight=amount*UNIT;
  if(p.cost?.trim()&&p.price?.trim())throw new Error('Use either unit cost or unit price in this prototype.');
  const annotation=p.cost?.trim()||p.price?.trim();
  if(annotation){const match=annotation.match(/^(\d+(?:\.\d{1,8})?)\s+([A-Z][A-Z0-9._-]*)$/);if(!match)throw new Error('Use an explicit unit value and currency, for example 110.00 EUR.');const rate=decimal(match[1]);if(rate<=0n)throw new Error('Unit cost or price must be positive.');weight=amount*rate;currency=match[2];}
  totals.set(currency,(totals.get(currency)??0n)+weight);
  if(p.account.trim()===s.account){if(p.currency.trim()!==r.currency||annotation)throw new Error('The statement cash posting must keep its original currency without cost or price.');source+=amount;}
 }catch(e){errors.push('Posting '+(i+1)+': '+e.message)}});
 if(source!==decimal(r.amount))errors.push('Statement cash postings must total '+r.amount+' '+r.currency+'.');
 if(!errors.length)for(const [currency,total]of totals)if(total!==0n)errors.push('Unbalanced '+currency+': difference '+(Number(total)/1e16).toLocaleString('en-GB',{maximumFractionDigits:8})+'.');
 return errors;
}
