import {buildModel, questions, reviewAvailable, batchState} from './model.mjs';
import {checkPostings} from './postings.mjs';
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const amount = (n,c) => `${Number(n).toLocaleString('en-GB',{minimumFractionDigits:2,maximumFractionDigits:8})} ${esc(c)}`;
const balance = b => b ? amount(b.amount,b.currency) : 'Unavailable';
const badge = (label, kind='') => `<span class="badge ${kind}">${esc(label)}</span>`;
const file = s => s.doc.source_file.split('/').at(-1);
const statusLabel = value => ({raw_ready:'Ready to extract',process_blocked:'Extraction blocked',process_review:'Source review',account_review:'Account review',account_blocked:'Account input needed',balance_review:'Balance review',balance_blocked:'Balance input needed',categorize_ready:'Ready to categorize',categorize_blocked:'Transaction input needed',categorize_review:'Transaction review',write_ready:'Ready to write',write_blocked:'Writing blocked',final_review:'Final review',done:'Done'}[value] ?? value);
const count = (n, noun) => `${n} ${noun}${n === 1 ? '' : 's'}`;
const stage = new URLSearchParams(location.search).get('stage') ?? 'transactions';
const prefix = ['accounts','mixed'].includes(stage) ? stage+'/' : '';
let model, tab='session', accountKey, filter='all', search='', timer, openGroups=new Set();
let persisted, busy=false;
function hydrate(state) {
  const drafts=new Map((model?.statements??[]).map(s=>[s.doc.source_file,s.drafts]));
  persisted=state;
  model=buildModel(state.session,state.status,state.documents);
  for(const s of model.statements) {
    s.drafts=drafts.get(s.doc.source_file)??new Map();
    for(const [key,value] of Object.entries(state.batch.answers)) if(key.startsWith(s.doc.source_file+'#')) s.answers.set(key.slice(s.doc.source_file.length+1),value);
    s.approved=state.batch.approvals.includes(s.doc.source_file);
  }
  model.prices.forEach(p=>p.approved=!!p.approval);
  model.queue=new Map(Object.entries(state.batch.pending));model.sent=state.batch.notifications;
}
async function action(route, payload={}) {
  if(busy)return false;busy=true;
  document.querySelector('.workspace-layout').inert=true;$('editorContent').inert=true;syncBatch();
  try {
    const response=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage,expected_token:persisted.batch.token,...payload})});
    const state=await response.json();if(!response.ok)throw Error(state.error);
    hydrate(state);return true;
  } catch(error){toast('Not saved: '+error.message);return false;}
  finally {busy=false;document.querySelector('.workspace-layout').inert=false;$('editorContent').inert=false;syncBatch();}
}
async function saveChange(s,subject,value) {
  return action('save',{source_file:s.doc.source_file,subject,value});
}
function inspectJSON() {
  $('editorContent').innerHTML=`<h2>Saved JSON</h2><p class="subtle">${esc(persisted.directory)}</p><p>${persisted.batch.history.length} saves · each save writes the JSON below immediately.</p>${[...persisted.batch.history].reverse().map(h=>`<details ${h.number===persisted.batch.history.length?'open':''}><summary>Save ${h.number} · ${esc(h.subject)} · ${esc(h.path)}</summary><pre>${esc((h.diff||'Statement JSON unchanged: confirmed the existing value.\n')+'\n'+(h.bookkeeping_diff??''))}</pre></details>`).join('')}<details><summary>Current JSON files</summary><pre>${esc(JSON.stringify({session:persisted.session,groups:persisted.documents,batch:persisted.batch},null,2))}</pre></details>`;
  if(!$('editor').open)$('editor').showModal();
}
function toast(text) { $('toast').textContent=text; $('toast').hidden=false; clearTimeout(timer); timer=setTimeout(()=>$('toast').hidden=true,4000); }
function suggestionOptions(suggestions) {
  return suggestions.map((text,i)=>`<option value="${i}">${esc(text)}${i===0?' (suggested)':''}</option>`).join('')+'<option value="other">Something else…</option>';
}
function questionForm(s,q) {
  const suggestions=q.account?.review?.suggestions??[], id=`choice-${s.id}-${q.key.replaceAll(':','-')}`;
  const comparison=q.kind==='Balance' ? q.account.review.reconciliation.map(r=>`<div class="comparison"><span>Statement<strong>${balance(q.account.opening_balance)}</strong></span><span>Ledger<strong>${amount(r.ledger_amount,r.currency)}</strong></span><span>Difference<strong>${amount(r.difference,r.currency)}</strong></span></div>`).join('') : '';
  return `<div class="question"><p class="rationale">${esc(q.text)}</p>${comparison}<form class="choice-form" data-answer="${s.id}" data-key="${esc(q.key)}">${suggestions.length?`<label for="${id}">${q.kind==='Account'?'Account':'Next step'}</label><div class="choice-line"><select id="${id}" data-choice>${suggestionOptions(suggestions)}</select><button class="primary">Save choice</button></div>`:''}<div data-custom ${suggestions.length?'hidden':''}><label for="${id}-custom">${q.kind==='Account'?'Ledger account':'Your response'}</label><input id="${id}-custom" ${suggestions.length?'':'required'} aria-label="${esc(q.kind)} response" placeholder="${q.kind==='Account'?'Assets:Bank:Checking':'Describe the correction'}">${suggestions.length?'':'<button class="primary">Save response</button>'}</div></form></div>`;
}
function sourceQuestions(s) { return questions(s).filter(q=>!q.row); }
function wireQuestions() {
  document.querySelectorAll('[data-answer]').forEach(form=>{
    const select=form.querySelector('select'), input=form.querySelector('input');
    if(select)select.onchange=()=>{form.querySelector('[data-custom]').hidden=select.value!=='other';input.required=select.value==='other';};
    form.onsubmit=async e=>{
      e.preventDefault();
      const s=model.statements.find(s=>s.id===form.dataset.answer),q=questions(s).find(q=>q.key===form.dataset.key);
      if(!q)return;
      const value=select&&select.value!=='other'?q.account.review.suggestions[Number(select.value)]:input.value.trim();
      if(!value)return;
      if(q.kind==='Account'&&!/^(Assets|Liabilities|Equity|Income|Expenses)(?::[A-Z][A-Za-z0-9-]*)+$/.test(value)){toast('Enter a full ledger account.');return;}
      if(await saveChange(s,q.key,value)){render();toast('Response saved to JSON.');}
    };
  });
}
function renderSession() {
  $('content').innerHTML=model.groups.map(g=>`<details class="group" data-group="${g.group_id}" ${openGroups.has(g.group_id)?'open':''}><summary><div><strong>${esc(g.name)}</strong><small>${count(g.statements.length,'statement')} · ${count(g.statements.reduce((n,s)=>n+s.accounts.length,0),'account')}</small></div>${badge(statusLabel(g.status))}${g.statements.some(s=>questions(s).length)?badge(g.statements.reduce((n,s)=>n+questions(s).length,0)+' need input','warn'):badge('No open questions','saved')}</summary>${g.statements.map(s=>`<article class="statement"><div class="statement-head"><div><h3>${esc(file(s))}</h3><small>${esc(s.doc.statement_metadata.institution_name)} · ${esc(s.doc.statement_metadata.statement_period?.start_date ?? 'Period unavailable')}</small></div>${s.doc.extraction_state!=='complete'?badge('Extraction '+s.doc.extraction_state,'warn'):badge(s.rows.length ? count(s.rows.length,'transaction') : /^(account_|balance_|process|raw_)/.test(s.status) ? 'Transactions pending' : '0 transactions')}</div>${s.accounts.map(a=>`<div class="account-row"><div><button class="account-link" data-account="${a.key}">${esc(a.account_name??a.account_id)} ↗</button><small style="display:block">${esc(s.answers.get('account:'+a.account_id) && !a.review?.reconciliation ? s.answers.get('account:'+a.account_id) : a.review?.ledger_account ?? 'Mapping unavailable')}</small></div><div class="balance"><small>Opening</small>${balance(a.opening_balance)}</div><div class="balance"><small>Closing</small>${balance(a.closing_balance)}</div><div>${questions(s).some(q=>q.account===a||q.row?.account_id===a.account_id)?badge('Needs input','warn'):badge(s.answers.has('account:'+a.account_id)?'Response saved':'No input needed',s.answers.has('account:'+a.account_id)?'saved':'')}</div></div>`).join('') || '<p class="muted">Accounts unavailable until extraction succeeds.</p>'}${sourceQuestions(s).map(q=>questionForm(s,q)).join('')}${questions(s).some(q=>q.row)?`<p class="subtle">${questions(s).filter(q=>q.row).length} transaction input needed <button data-needs="${s.id}">Review transactions →</button></p>`:''}${reviewAvailable(s)?`<div class="approval"><span>${s.approved?'Review saved for this statement.':'Statement approval'}</span><button data-review="${s.id}" ${questions(s).length||s.drafts.size?'disabled':''}>${s.approved?'Review saved ✓':'Review statement'}</button></div>`:s.answers.size?'<p class="subtle">Response saved · awaiting the next agent pass.</p>':''}</article>`).join('')}</details>`).join('') || '<div class="empty">No statement groups in this session.</div>';
  document.querySelectorAll('[data-group]').forEach(el=>el.ontoggle=()=>el.open?openGroups.add(el.dataset.group):openGroups.delete(el.dataset.group));
  document.querySelectorAll('[data-account]').forEach(b=>b.onclick=()=>showAccount(b.dataset.account));
  document.querySelectorAll('[data-needs]').forEach(b=>b.onclick=()=>{const s=model.statements.find(s=>s.id===b.dataset.needs);showAccount(s.accounts.find(a=>questions(s).some(q=>q.row?.account_id===a.account_id)).key,'needs');});
  document.querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>reviewStatement(model.statements.find(s=>s.id===b.dataset.review)));
  wireQuestions();
}
function showAccount(key,nextFilter='all') {accountKey=key;filter=nextFilter;search='';tab='account';render();}
function rowNeeds(r) {return questions(r.statement).some(q=>q.row===r);}
function renderAccount() {
  const a=model.accounts.find(a=>a.key===accountKey) ?? model.accounts[0];
  if (!a) {$('content').innerHTML='<div class="empty">Accounts are not available yet. Review the source input in Session.</div>';return;}
  accountKey=a.key;const s=a.statement, rows=s.rows.filter(r=>r.account_id===a.account_id);
  const visible=rows.filter(r=>(filter!=='needs'||rowNeeds(r))&&(filter!=='transfers'||r.review?.disposition==='paired_transfer')&&`${r.description} ${r.review?.postings?.map(p=>p.account).join(' ')}`.toLowerCase().includes(search.toLowerCase())).sort((a,b)=>b.transaction_date.localeCompare(a.transaction_date));
  $('content').innerHTML=`<div class="section-head"><div><h2>${esc(a.account_name??a.account_id)}</h2><small>${esc(file(s))}</small><p class="subtle">${esc(a.review?.ledger_account??'Mapping unavailable')}</p></div><div class="balance"><small>Closing balance</small>${balance(a.closing_balance)}</div></div>${sourceQuestions(s).filter(q=>!q.account||q.account===a).map(q=>questionForm(s,q)).join('')}<div class="toolbar"><button data-filter="all" aria-pressed="${filter==='all'}">All ${rows.length}</button><button data-filter="needs" aria-pressed="${filter==='needs'}">Needs input ${rows.filter(rowNeeds).length}</button><button data-filter="transfers" aria-pressed="${filter==='transfers'}">Transfers</button><input id="search" type="search" aria-label="Search transactions" placeholder="Search transactions" value="${esc(search)}"></div>${rows.length?`<div class="table-wrap"><table><thead><tr><th>Date</th><th>Transaction</th><th>Category / status</th><th class="amount">Amount</th><th></th></tr></thead><tbody>${visible.map(r=>`<tr class="${rowNeeds(r)?'needs':''}"><td>${esc(r.transaction_date.slice(5))}</td><td><button class="row-button" data-row="${esc(r.record_id)}">${esc(r.description)}</button><small>${esc(r.raw_fields?.reference??r.source_reference)}</small></td><td>${rowNeeds(r)?badge('Needs input','warn'):r.review?.disposition==='paired_transfer'?badge('Internal transfer'):s.answers.has('row:'+r.record_id)?badge('Response saved','saved'):esc(r.review?.postings?.filter(p=>p.account!==a.review?.ledger_account).map(p=>p.account.split(':').slice(1).join(' / ')).join(', ')??'Not categorized')}${s.drafts.has(r.record_id)?' '+badge('Unsaved draft','warn'):''}</td><td class="amount">${amount(r.amount,r.currency)}</td><td><button data-row="${esc(r.record_id)}" aria-label="Review ${esc(r.description)}">↗</button></td></tr>`).join('')||'<tr><td colspan="5" class="muted">No matching transactions.</td></tr>'}</tbody></table></div>`:'<div class="empty">Transactions are not available at this stage.</div>'}<p class="subtle">${visible.length} of ${rows.length} transactions · ${esc(file(s))}</p>`;
  document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;renderAccount();});
  $('search').oninput=e=>{const pos=e.target.selectionStart;search=e.target.value;renderAccount();$('search').focus();$('search').setSelectionRange(pos,pos);};
  document.querySelectorAll('[data-row]').forEach(b=>b.onclick=()=>editRow(s.rows.find(r=>r.record_id===b.dataset.row)));
  wireQuestions();
}
function postingsHTML(ps) {return `<div class="table-wrap"><table><tbody>${(ps??[]).map(p=>`<tr><td><code>${esc(p.account)}</code></td><td class="amount">${amount(p.amount,p.currency)}${p.cost?`<small>Cost ${esc(p.cost)} / unit</small>`:''}${p.price?`<small>Price ${esc(p.price)} / unit</small>`:''}</td></tr>`).join('')}</tbody></table></div>`;}
function editRow(r) {
  const s=r.statement,a=s.accounts.find(a=>a.account_id===r.account_id), draft=s.drafts.get(r.record_id), q=questions(s).find(q=>q.row===r);
  const suggestions=r.review?.suggestions??[];
  $('editorContent').innerHTML=`<p class="eyebrow">${esc(a.account_name)} · ${esc(r.transaction_date)}</p><h2>${esc(r.description)}</h2><p>${amount(r.amount,r.currency)}</p>${q?`<div class="question"><p class="rationale">${esc(q.text)}</p>${suggestions.length?`<label for="transactionSuggestion">Treatment</label><div class="choice-line"><select id="transactionSuggestion">${suggestionOptions(suggestions)}</select><button class="primary" id="saveSuggestion">Save choice</button></div>`:''}<div id="customResponse" ${suggestions.length&&!s.drafts.has('response:'+r.record_id)?'hidden':''}><label for="response">Your correction</label><textarea id="response" placeholder="Describe the correct treatment"></textarea>${suggestions.length?'':'<button id="saveResponse" class="primary">Save response</button>'}</div></div>`:s.answers.has('row:'+r.record_id)?`<p>${badge('Response saved','saved')} ${esc(s.answers.get('row:'+r.record_id))}</p>`:''}${r.peers?`<div class="question">Internal transfer · one shared posting owner<p><code>${esc(r.review.posting_owner)}</code></p>${r.peers.map((p,i)=>`<button data-peer="${i}">View ${esc(file(p.statement))} →</button>`).join('')}</div>`:''}<div id="postingEditor">${postingsHTML(r.review?.postings)}${!r.peers&&r.review?.postings?.length?'<div class="actions"><button id="edit">Edit postings</button></div>':''}</div><details class="evidence"><summary>Source & reasoning</summary><p>${esc(file(s))} · ${esc(r.source_reference)}</p><p>${esc(r.review?.rationale)}</p></details>`;
  if (!$('editor').open) $('editor').showModal();
  const saveResponse=async value=>{if(!value)return;if(await saveChange(s,'row:'+r.record_id,value)){s.drafts.delete('response:'+r.record_id);render();editRow(model.statements.find(x=>x.id===s.id).rows.find(x=>x.record_id===r.record_id));toast('Response saved to JSON.');}};
  if($('transactionSuggestion')) {
    if(s.drafts.has('response:'+r.record_id))$('transactionSuggestion').value='other';
    $('transactionSuggestion').onchange=()=>{$('customResponse').hidden=$('transactionSuggestion').value!=='other';};
    $('saveSuggestion').onclick=()=>saveResponse($('transactionSuggestion').value==='other'?$('response').value.trim():suggestions[Number($('transactionSuggestion').value)]);
  }
  if ($('response')) {
    $('response').value=s.drafts.get('response:'+r.record_id)??'';
    $('response').oninput=e=>{if(e.target.value)s.drafts.set('response:'+r.record_id,e.target.value);else s.drafts.delete('response:'+r.record_id);syncBatch();};
    if($('saveResponse'))$('saveResponse').onclick=()=>saveResponse($('response').value.trim());
  }
  document.querySelectorAll('[data-peer]').forEach(b=>b.onclick=()=>editRow(r.peers[Number(b.dataset.peer)]));
  if ($('edit')) $('edit').onclick=()=>{s.drafts.set(r.record_id,structuredClone(r.review.postings).map(p=>({...p,cost:p.cost??'',price:p.price??''})));renderPostingEditor(r,a);syncBatch();};
  if(draft) renderPostingEditor(r,a);
}
function renderPostingEditor(r,a) {
  const s=r.statement,ps=s.drafts.get(r.record_id);
  $('postingEditor').innerHTML=ps.map((p,i)=>`<div class="posting">${['account','amount','currency','cost','price'].map(k=>`<label>${{account:'Account',amount:'Amount / units',currency:'Currency',cost:'Unit cost',price:'Unit price'}[k]}<input data-index="${i}" data-field="${k}" aria-label="Posting ${i+1} ${k}" value="${esc(p[k])}"></label>`).join('')}<button data-remove="${i}" aria-label="Remove posting ${i+1}">×</button></div>`).join('')+'<div class="error" id="postingErrors" role="status"></div><div class="actions"><button id="addPosting">Add split</button><button class="primary" id="savePostings">Save postings</button><button id="discard">Discard edits</button></div><p class="subtle">Unit cost / price: e.g. 110.00 EUR. Simple unit values only.</p>';
  const errors=()=>checkPostings({account:a.review.ledger_account},r,ps);
  const check=()=>{$('postingErrors').textContent=errors().join(' ')||'Balanced · source amount preserved';$('savePostings').disabled=!!errors().length;};
  document.querySelectorAll('[data-index]').forEach(input=>input.oninput=()=>{ps[Number(input.dataset.index)][input.dataset.field]=input.value;check();});
  document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{ps.splice(Number(b.dataset.remove),1);renderPostingEditor(r,a);});
  $('addPosting').onclick=()=>{ps.push({account:'Expenses:',amount:'0',currency:r.currency,cost:'',price:''});renderPostingEditor(r,a);};
  $('discard').onclick=()=>{s.drafts.delete(r.record_id);editRow(r);render();};
  $('savePostings').onclick=async()=>{if(errors().length)return;const postings=ps.map(p=>Object.fromEntries(Object.entries(p).map(([k,v])=>[k,String(v).trim()]).filter(([,v])=>v!=='')));if(await saveChange(s,'postings:'+r.record_id,postings)){s.drafts.delete(r.record_id);render();editRow(model.statements.find(x=>x.id===s.id).rows.find(x=>x.record_id===r.record_id));toast('Postings saved to JSON.');}};
  check();
}
function reviewStatement(s) {
  $('editorContent').innerHTML=`<p class="eyebrow">Statement review</p><h2>${esc(file(s))}</h2><p class="subtle">Approval covers mappings, postings and supporting directives. Writing and validation follow with the agent.</p>${s.accounts.map(a=>`<p><strong>${esc(a.account_name)}</strong><br><code>${esc(a.review.ledger_account)}</code> · Opening ${balance(a.opening_balance)} · Closing ${balance(a.closing_balance)}</p>`).join('')}${s.rows.map(r=>`<h3 style="margin:20px 0 8px">${esc(r.description)} ${r.peers?badge('Shared transfer'):''}</h3>${postingsHTML(r.review.postings)}`).join('')}<details class="evidence"><summary>Supporting directives & validation</summary><pre>${esc(s.accounts.flatMap(a=>a.review?.proposed_directives??[]).join('\n')||'No supporting directives proposed.')}</pre><p>${s.doc.review?.validation ? esc(s.doc.review.validation.stage+' validation: '+s.doc.review.validation.state) : 'Validation unavailable.'}</p><p>Ledger write has not been simulated. Shared transfers require all affected statements to be approved.</p></details><div class="actions"><button id="approveStatement" class="primary">Approve statement</button></div>`;
  $('editor').showModal();
  $('approveStatement').onclick=async()=>{if(questions(s).length||s.drafts.size)return;if(await saveChange(s,'approval','approved')){$('editor').close();render();toast('Approval saved to JSON.');}};
}
function renderPrices() {
  $('content').innerHTML=model.prices.map((p,i)=>`<article class="price-card"><div class="section-head"><div><h2>${esc(p.requested_date)}</h2><small>${esc(p.run_id)}</small></div>${badge(p.state)}</div>${p.jobs?.length?`<div class="table-wrap"><table><thead><tr><th>Commodity</th><th>Quote</th><th>Source</th><th>Result</th></tr></thead><tbody>${p.jobs.map(j=>`<tr><td><strong>${esc(j.commodity)}</strong></td><td><strong>${esc(j.directive?.match(/price\s+\S+\s+(.+)$/)?.[1]??'Unavailable')}</strong><small>${esc(j.quote_date??'Date unavailable')}</small></td><td>${esc(j.source)}</td><td>${badge(j.outcome)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="muted">No quotes available.</p>'}<div class="approval"><span>Synthetic rates · ${esc(p.coverage?.join(', ')??'No coverage')}${p.validation?'':' · ledger validation unavailable'}</span>${p.jobs?.some(j=>j.outcome==='emitted')?`<button data-price="${i}" ${p.approved?'disabled':''}>${p.approved?'Approval saved ✓':'Approve prices'}</button>`:''}</div></article>`).join('')||'<div class="empty">No price run yet.<p>Prices follow the current statement pass.</p></div>';
  document.querySelectorAll('[data-price]').forEach(b=>b.onclick=async()=>{const p=model.prices[Number(b.dataset.price)];if(await action('save',{run_id:p.run_id,subject:'approval',value:'approved'})){render();toast('Price approval saved to JSON.');}});
}
function syncBatch() {
  if(!model)return;const b=batchState(model);
  $('send').disabled=busy||!b.canSend;$('reset').disabled=busy;
  $('batchStatus').textContent=`${count(model.queue.size,'saved change')}${b.inputs?' · '+count(b.inputs,'input')+' left':''}`;
  $('batchHelp').textContent=b.drafts?`${b.drafts} unsaved drafts` : b.inputs?'Review highlighted inputs to continue.' : b.approvals?`${b.approvals} review approvals left · Session / Price` : model.queue.size?'Ready to send in one batch.':model.sent?'Batch sent · waiting for the agent.':'No changes to send.';
  $('notifications').textContent=model.sent+' simulated notifications';
}
function renderAccountNav() {
  $('accountNav').innerHTML=model.accounts.map(a=>{
    const pending=questions(a.statement).filter(q=>q.account===a||q.row?.account_id===a.account_id).length;
    return `<button class="sidebar-account" data-sidebar-account="${a.key}" ${tab==='account'&&accountKey===a.key?'aria-current="page"':''}><span><strong>${esc(a.account_name??a.account_id)}</strong><small>${esc(file(a.statement))}</small></span>${pending?badge(pending,'warn'):''}</button>`;
  }).join('')||'<p class="sidebar-empty">Accounts pending extraction</p>';
  document.querySelectorAll('[data-sidebar-account]').forEach(button=>button.onclick=()=>showAccount(button.dataset.sidebarAccount));
}
function render() {
  document.querySelectorAll('[data-tab]').forEach(b=>{if(b.dataset.tab===tab)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  $('overview').textContent=`${model.groups.length} groups · ${model.statements.length} statements · ${model.statements.reduce((n,s)=>n+questions(s).length,0)} need input`;
  ({session:renderSession,account:renderAccount,price:renderPrices}[tab])();renderAccountNav();syncBatch();
}
$('close').onclick=()=>{$('editor').close();render();};
$('editor').addEventListener('cancel',()=>setTimeout(render,0));
$('stage').value=prefix?stage:'transactions';
$('stage').onchange=e=>location.search='?stage='+e.target.value;
$('reset').onclick=async()=>{if(await action('reset')){model.statements.forEach(s=>s.drafts.clear());$('editor').close();render();toast('Saved copies reset to original fixtures.');}};
$('inspect').onclick=inspectJSON;
$('fixture').href='./fixtures/'+prefix+'session.json';
$('send').onclick=async()=>{if(!batchState(model).canSend)return;if(await action('send')){render();toast('Batch sent (simulated). No real agent was notified.');}};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;render();});
try {const response=await fetch('/api/state?stage='+encodeURIComponent(stage),{cache:'no-store'});if(!response.ok)throw Error('Start the prototype with serve.py.');hydrate(await response.json());render();}
catch(e) {$('content').textContent='Saved JSON unavailable: '+e.message;$('batchStatus').textContent='Review unavailable';$('batchHelp').textContent='Run the prototype save server.';}
