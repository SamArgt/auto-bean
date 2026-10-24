import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildModel,questions,batchState,reviewAvailable,save} from './model.mjs';
import {checkPostings} from './postings.mjs';
const read = path => JSON.parse(readFileSync(new URL(path,import.meta.url)));
function fixture(profile='') {
  const prefix='./fixtures/'+(profile?profile+'/':'');
  const session=read(prefix+'session.json'),status=read(prefix+'import-status.json');
  return [session,status,session.groups.map(g=>read(prefix+g.parsed_group))];
}
test('all stage profiles load exact group membership and preserve unavailable data',()=>{
  for(const profile of ['','accounts','mixed']) {
    const m=buildModel(...fixture(profile));assert.equal(m.statements.length,3);
    assert.equal(batchState(m).inputs,profile?3:2);
    assert.equal(batchState(m).canSend,false);
    if(profile){assert.equal(m.statements.flatMap(s=>s.rows).length,0);assert.ok(m.accounts.every(a=>!a.closing_balance));assert.ok(m.statements.every(s=>!reviewAvailable(s)));}
  }
});
test('mismatched fingerprints, duplicate sources, group IDs and transfer links fail closed',()=>{
  const cases=[
    a=>a[2][0].statements[0].source_fingerprint='sha256:bad',
    a=>a[0].groups[1].group_id='banking',
    a=>a[2][0].statements.push(a[2][0].statements[0]),
    a=>a[2][0].statements[0].extracted_records.find(r=>r.review.linked_records).review.linked_records[0].record_id='missing'
  ];
  for(const change of cases){const args=fixture();change(args);assert.throws(()=>buildModel(...args));}
});
test('account-only responses unlock one batch, without advancing the group',()=>{
  const m=buildModel(...fixture('accounts'));
  for(const s of m.statements){const q=questions(s)[0];s.answers.set(q.key,'Assets:Bank:Confirmed');save(m,s,q.key,'Assets:Bank:Confirmed');}
  assert.equal(batchState(m).canSend,true);assert.equal(m.sent,0);assert.equal(m.queue.size,3);
  assert.equal(m.groups[0].status,'account_review');
  m.statements[0].drafts.set('unsaved',[]);assert.equal(batchState(m).canSend,false);
});
test('clarification responses do not invent posting approval readiness',()=>{
  const m=buildModel(...fixture());
  for(const s of m.statements)for(const q of questions(s)){s.answers.set(q.key,'Please use the source evidence.');save(m,s,q.key,'Please use the source evidence.');}
  assert.equal(reviewAvailable(m.statements[0]),false);
  assert.equal(reviewAvailable(m.statements[1]),true);
  assert.equal(batchState(m).approvals,2); // savings + separate price run
  m.statements[1].approved=true;m.prices[0].approved=true;assert.equal(batchState(m).canSend,true);
  save(m,m.statements[1],'postings:interest',[]);assert.equal(batchState(m).canSend,false);
});
test('split, fee, cost and internal transfer proposals balance exactly',()=>{
  const m=buildModel(...fixture());
  for(const a of m.accounts)for(const r of a.statement.rows.filter(r=>r.account_id===a.account_id))assert.deepEqual(checkPostings({account:a.review.ledger_account},r,r.review.postings),[],r.description);
  const a=m.accounts[2],r=a.statement.rows.find(r=>r.review.postings.some(p=>p.cost));
  const ps=structuredClone(r.review.postings);ps[0].amount='-221.49';
  assert.ok(checkPostings({account:a.review.ledger_account},r,ps).length);
  ps[0].amount=r.review.postings[0].amount;ps.find(p=>p.cost).cost='111 EUR';assert.ok(checkPostings({account:a.review.ledger_account},r,ps).some(e=>e.includes('Unbalanced')));
});
test('multiple accounts in one statement keep source-scoped identities',()=>{
  const args=fixture('accounts');const doc=args[2][0].statements[0];
  doc.statement_metadata.accounts.push({...structuredClone(doc.statement_metadata.accounts[0]),account_id:'other'});
  const m=buildModel(...args);assert.equal(m.accounts.length,4);assert.equal(questions(m.statements[0]).length,2);
});
test('a ready source can be reviewed while its group has an extraction blocker',()=>{
  const args=fixture();args[1].groups.banking.current_status='process_blocked';
  const m=buildModel(...args);assert.equal(reviewAvailable(m.statements[1]),true);
});
