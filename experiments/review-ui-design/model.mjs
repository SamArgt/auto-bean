export function buildModel(session, status, documents) {
  if (session.schema_version !== 1 || status.version !== 1 || !Array.isArray(session.groups)) throw Error('Unsupported session schema.');
  const sources = new Set(), paths = new Set(), ids = new Set();
  const groups = session.groups.map((g, i) => {
    const state = status.groups?.[g.group_id], doc = documents[i];
    const same = (a, b) => JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
    if (ids.has(g.group_id) || paths.has(g.parsed_group) || !state || state.session_id !== session.session_id || state.parsed_group !== g.parsed_group || doc?.schema_version !== 2 || doc.group_id !== g.group_id || !same(g.source_files, Object.keys(state.sources)) || !same(g.source_files, doc.statements.map(s => s.source_file))) throw Error('Group membership mismatch: ' + g.group_id);
    paths.add(g.parsed_group); ids.add(g.group_id);
    return {...g, status: state.current_status, statements: doc.statements.map((s, j) => {
      if (sources.has(s.source_file) || state.sources[s.source_file].source_fingerprint !== s.source_fingerprint) throw Error('Source identity mismatch.');
      sources.add(s.source_file);
      const item = {id: `${i}-${j}`, doc: s, status: state.current_status, approved: false, answers: new Map(), drafts: new Map()};
      item.accounts = s.statement_metadata.accounts.map((a, k) => ({...a, key: `${i}-${j}-${k}`, statement: item}));
      item.rows = s.extracted_records.map(r => ({...r, review: structuredClone(r.review), statement: item}));
      if (new Set(item.accounts.map(a => a.account_id)).size !== item.accounts.length || item.rows.some(r => !item.accounts.some(a => a.account_id === r.account_id))) throw Error('Unknown or duplicate source account.');
      return item;
    })};
  });
  const statements = groups.flatMap(g => g.statements);
  for (const s of statements) for (const r of s.rows) {
    if (r.review?.disposition !== 'paired_transfer') continue;
    r.peers = (r.review.linked_records ?? []).map(link => {
      const peer = statements.find(p => p.doc.source_file === link.source_file)?.rows.find(p => p.record_id === link.record_id && p.account_id === link.account_id);
      if (!peer || peer.review?.posting_owner !== r.review.posting_owner || !peer.review.linked_records?.some(l => l.source_file === s.doc.source_file && l.record_id === r.record_id && l.account_id === r.account_id)) throw Error('Transfer link mismatch.');
      return peer;
    });
    if (!r.peers.length) throw Error('Missing transfer counterpart.');
  }
  return {session, groups, statements, accounts: statements.flatMap(s => s.accounts), prices: session.price_runs.map(p => ({...p, approved: false})), queue: new Map(), sent: 0};
}
export function questions(s) {
  const result = [];
  const processing = s.doc.review?.processing;
  if (processing?.needs_input || ['failed', 'partial'].includes(s.doc.extraction_state)) result.push({key:'source', kind:'Source', text:processing?.failure_reason ?? 'Clarify the incomplete source.'});
  for (const a of s.accounts) if (a.review?.state === 'needs_input') result.push({key:'account:'+a.account_id, kind:a.review.reconciliation?.some(r => r.state === 'mismatch') ? 'Balance' : 'Account', text:a.review.rationale, account:a});
  for (const r of s.rows) if (r.review?.state === 'needs_input' || r.review?.disposition === 'hold') result.push({key:'row:'+r.record_id, kind:'Transaction', text:r.review.rationale, row:r});
  return result.filter(q => !s.answers.has(q.key));
}
export function reviewAvailable(s) {
  return s.doc.extraction_state === 'complete' && (s.rows.length > 0 || /^(categorize_|write_|final_review)/.test(s.status)) && s.rows.every(r => r.review && r.review.state !== 'needs_input' && r.review.disposition !== 'hold') && s.accounts.every(a => a.review?.ledger_account && a.review.state !== 'needs_input');
}
export function batchState(model) {
  const inputs = model.statements.reduce((n,s) => n + questions(s).length, 0);
  const drafts = model.statements.reduce((n,s) => n+s.drafts.size,0);
  const approvals = model.statements.filter(s => reviewAvailable(s) && !s.approved).length + model.prices.filter(p => p.jobs?.some(j => j.outcome === 'emitted') && !p.approved).length;
  return {inputs, drafts, approvals, canSend: model.queue.size > 0 && !inputs && !drafts && !approvals};
}
export function save(model, s, key, value) {
  s.approved = false;
  model.queue.delete(s.id+':approval');
  model.queue.set(s.id+':'+key, {source_file:s.doc.source_file, subject:key, value:structuredClone(value)});
}
