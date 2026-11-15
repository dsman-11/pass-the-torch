// Exercise the actual form handlers without a browser or third-party DOM library.
// These are controller checks; they do not replace visual/browser testing.
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('app/static/app.js','utf8');
function node(){return {innerHTML:'',textContent:'',disabled:false,isConnected:true,classList:{toggle(){}},setAttribute(){},removeAttribute(){},focus(){},scrollIntoView(){},querySelector(){return null;},querySelectorAll(){return [];}};}
function harness(){
  const elements={'#main':node(),'#nav':node(),'#status':node()},events={},calls=[];
  const context=vm.createContext({console,URLSearchParams,Date,Set,Error,Promise,
    window:{scrollTo(){}},setTimeout,clearTimeout,FormData:class{constructor(form){this.values=form.values || {};}get(k){return this.values[k]??null;}*[Symbol.iterator](){yield*Object.entries(this.values);}},
    document:{querySelector:s=>elements[s] || null,getElementById:id=>elements['#'+id],querySelectorAll:()=>[],addEventListener:(name,fn)=>events[name]=fn},
    fetch:()=>new Promise(()=>{})});
  vm.runInContext(source,context);
  const evaluate=code=>vm.runInContext(code,context);
  evaluate(`S.catalog={programs:[{id:'ai',name:'MS CS AI'}],courses:[{code:'CSCI570',title:'Algorithms',units:4}]};`);
  return {context,evaluate,elements,events,calls};
}
const wait=async()=>{for(let i=0;i<10;i++)await new Promise(resolve=>setImmediate(resolve));};
function routeFetch(h,routes){h.context.fetch=async(path,options)=>{h.calls.push({path,options});const value=routes[path];assert.notEqual(value,undefined,'Unexpected API route '+path);return {ok:true,status:200,json:async()=>value};};}

test('account Continue submits and opens the centered academic profile',async()=>{
  const h=harness();routeFetch(h,{'/api/register':{csrf:'token'},'/api/me':{account:{name:'Test Person'},csrf:'token',profile:null,courses:[],access:{courses:[]}}});
  const button=node(),form={id:'account-form',values:{name:'Test Person',email:'test@usc.edu',password:'long-test-password'},querySelector:()=>button};
  h.events.submit({target:form,preventDefault(){}});await wait();
  assert.match(h.elements['#main'].innerHTML,/id="profile-form"/);
  assert.match(h.elements['#main'].innerHTML,/center/);
  assert.equal(JSON.parse(h.calls[0].options.body).email,'test@usc.edu');
});

test('review Next saves privately and increments the question/remaining counts',async()=>{
  const h=harness();h.evaluate(`S.me={account:{name:'Test'},access:{courses:[]}};S.schema={hours:['11–15'],drivers:['Projects'],balance:[],labels:[]};S.review={course:{course_code:'CSCI570',instructor:'Example',term:'Fall 2026'},answers:{},position:0,previous:null,number:1,total:2};`);
  const button=node(),answerNode={value:'11–15'},form={id:'review-answer',querySelector:s=>s==='button[type=submit]'?button:answerNode};
  h.elements['#review-answer']=form;routeFetch(h,{'/api/reviews/draft':{ok:true}});
  h.events.submit({target:form,preventDefault(){}});await wait();
  assert.match(h.elements['#main'].innerHTML,/Question 2 of 6/);
  assert.match(h.elements['#main'].innerHTML,/4 more after this/);
  const payload=JSON.parse(h.calls[0].options.body);
  assert.equal(payload.answers['0'],'11–15');assert.equal(payload.position,1);
  assert.equal(h.calls[0].options.method,'PUT');
});

test('initial review uses free responses for 3, 5 and 6 and escapes saved text',()=>{
  const h=harness();h.evaluate(`S.me={account:{name:'Test'},access:{courses:[]}};S.schema={hours:[],drivers:[],balance:[],labels:[]};S.review={course:{course_code:'CSCI570',instructor:'Example',term:'Fall 2026'},answers:{2:'<script>bad()</script>'},position:2,previous:null,number:1,total:1};wizard();`);
  assert.match(h.elements['#main'].innerHTML,/<textarea/);
  assert.doesNotMatch(h.elements['#main'].innerHTML,/<script>bad/);
  assert.match(h.elements['#main'].innerHTML,/&lt;script&gt;/);
  for(const i of [4,5]){h.evaluate(`S.review.position=${i};wizard();`);assert.match(h.elements['#main'].innerHTML,/<textarea/);}
});

test('follow-up reconfirmation and final consent summary render without losing history',()=>{
  const h=harness();h.evaluate(`S.me={account:{name:'Test'},access:{courses:[]}};S.schema={labels:['Hours','Drivers','Preparation','Combination','Learning','Advice']};const old=Array.from({length:6},()=>({value:'Prior written answer',written_at:'2026-11-14T12:00:00Z'}));S.review={course:{course_code:'CSCI570',instructor:'Example',term:'Fall 2026'},answers:{0:'11–15',1:['Projects'],2:null,3:{courses:[],balance:'Not assessed / only course'},4:null,5:null},position:2,previous:{id:1,answers:old},number:1,total:1};wizard();`);
  assert.match(h.elements['#main'].innerHTML,/No change; I still stand by this answer/);
  h.evaluate('S.review.position=6;wizard();');
  assert.match(h.elements['#main'].innerHTML,/Ready to share/);
  assert.match(h.elements['#main'].innerHTML,/id="consent"/);
  assert.match(h.elements['#main'].innerHTML,/Reconfirming previous answer/);
});

test('academic profile Continue sends required instructors and opens the contribution gate',async()=>{
  const h=harness();h.evaluate(`S.me={account:{name:'Test Person'},profile:null,courses:[],access:{courses:[]}};S.profile={program_id:'ai',start_date:'2026-08',graduation_date:'2028-12',courses:[{}]};`);
  const fields={code:{value:'CSCI570'},status:{value:'current'},term:{value:'Fall 2026'},instructor:{value:'Professor Example'}};
  const row={querySelector:s=>fields[s.match(/data-key=(\w+)/)[1]]};
  const button=node(),form={id:'profile-form',values:{program_id:'ai',start_date:'2026-08',graduation_date:'2028-12'},querySelector:()=>button,querySelectorAll:()=>[row]};
  h.elements['#profile-form']=form;
  routeFetch(h,{'/api/profile':{ok:true},'/api/me':{account:{name:'Test Person'},csrf:'token',profile:{program_id:'ai'},courses:[{course_code:'CSCI570',term:'Fall 2026',instructor:'Professor Example'}],access:{unlocked:false,reason:'Review each course.',courses:[{course_code:'CSCI570',term:'Fall 2026',instructor:'Professor Example',fresh:false}]}},'/api/explore':{progress:{}},'/api/review-schema':{labels:[]},'/api/reviews/mine':{reviews:[]}});
  h.events.submit({target:form,preventDefault(){}});await wait();
  assert.match(h.elements['#main'].innerHTML,/Your course reviews/);
  assert.match(h.elements['#main'].innerHTML,/0 of 1 initial reviews completed/);
  assert.equal(JSON.parse(h.calls[0].options.body).courses[0].instructor,'Professor Example');
});

test('AI answers render safe formatting and only known source buttons',()=>{
  const h=harness();const html=h.evaluate("renderAnswer('**Useful summary**\\n\\n- First point [R:1]\\n- <img src=x onerror=bad()> [R:999]',new Set(['R:1']),'turn-0')");
  assert.match(html,/<strong>Useful summary<\/strong>/);
  assert.match(html,/<ul>/);assert.match(html,/data-id="source-turn-0-R-1"/);
  assert.doesNotMatch(html,/<img/);assert.doesNotMatch(html,/data-id="source-turn-0-R-999"/);
});

test('leaving a review saves the currently typed answer before clearing it',async()=>{
  const h=harness();h.evaluate("S.page='review';S.review={course:{course_code:'CSCI570'},answers:{},position:2,previous:null};");
  const text={value:'New preparation detail that has not reached Next yet.'};
  h.elements['#review-answer']={querySelector:s=>s.includes('unchanged')?null:text};
  routeFetch(h,{'/api/reviews/draft':{ok:true}});
  await h.evaluate('leaveReview()');
  assert.equal(JSON.parse(h.calls[0].options.body).answers['2'],text.value);
  assert.equal(h.evaluate('S.review'),null);
});

test('late API responses from a previous account or evidence mode are discarded',async()=>{
  const h=harness();let finish;h.context.fetch=()=>new Promise(resolve=>finish=resolve);
  const pending=h.evaluate("api('/ask','POST',{})");
  h.evaluate('S.epoch++');finish({ok:true,status:200,json:async()=>({answer:'Earlier private conversation'})});
  await assert.rejects(pending,error=>error.name==='AbortError');
  assert.equal(h.evaluate('Object.keys(S.conversations).length'),0);
});

test('source reference opens its source card and enclosing source list',async()=>{
  const h=harness(),card=node(),outer={tagName:'DETAILS',open:false,parentElement:null};
  card.open=false;card.parentElement=outer;h.elements['#source-turn-0-R-1']=card;
  const button={...node(),dataset:{act:'source',id:'source-turn-0-R-1'}};
  h.events.click({target:{closest:()=>button}});await wait();
  assert.equal(card.open,true);assert.equal(outer.open,true);
});

test('typing a free response automatically saves a private draft',async()=>{
  const h=harness();h.evaluate("S.page='review';S.review={course:{course_code:'CSCI570'},answers:{},position:4,previous:null};");
  h.elements['#review-answer']={querySelector:s=>s.includes('unchanged')?null:{value:'A concrete learning experience before pressing Next.'}};
  routeFetch(h,{'/api/reviews/draft':{ok:true}});
  h.evaluate('scheduleDraft()');await new Promise(resolve=>setTimeout(resolve,500));
  assert.equal(h.calls.length,1);assert.equal(h.evaluate('S.review.dirty'),false);
  assert.match(JSON.parse(h.calls[0].options.body).answers['4'],/learning experience/);
});

test('search is compact initially and filters by course title or feedback',()=>{
  const h=harness();h.elements['#search-results']=node();h.elements['#course-search']={value:''};h.elements['#course-filter']={value:'all'};
  h.evaluate("S.me={courses:[]};S.academic={courses:[{code:'CSCI567',title:'Machine Learning',units:4,option_status:'remaining',contributor_count:5},{code:'CSCI566',title:'Deep Learning',units:4,option_status:'needs_review',contributor_count:0}]};searchResults();");
  assert.doesNotMatch(h.elements['#search-results'].innerHTML,/course-card/);
  h.elements['#course-search'].value='Machine';h.evaluate('searchResults()');
  assert.match(h.elements['#search-results'].innerHTML,/CSCI567/);assert.doesNotMatch(h.elements['#search-results'].innerHTML,/CSCI566/);
  h.elements['#course-search'].value='';h.elements['#course-filter'].value='with_feedback';h.evaluate('searchResults()');
  assert.match(h.elements['#search-results'].innerHTML,/5 contributors/);assert.doesNotMatch(h.elements['#search-results'].innerHTML,/CSCI566/);
});

test('a queued draft cannot send old answers after the account changes',async()=>{
  const h=harness();let release;h.context.previousSave=new Promise(resolve=>release=resolve);
  h.evaluate("S.review={course:{course_code:'CSCI570'},answers:{2:'Previous account preparation'},position:2,previous:null,pending:previousSave};");
  routeFetch(h,{'/api/reviews/draft':{ok:true}});
  const queued=h.evaluate('saveReviewDraft(2)');h.evaluate('S.epoch++');release();
  await assert.rejects(queued,error=>error.name==='AbortError');
  assert.equal(h.calls.length,0);
});

test('mixed heading and star bullets render and consecutive citations collapse safely',()=>{
  const h=harness();const html=h.evaluate("renderAnswer('Preparation\\n* **Background:** Prior knowledge helps. [R:1] [R:2] [P:profile]\\n* Advice: start early.',new Set(['R:1','R:2','P:profile']),'turn-2')");
  assert.match(html,/<p>Preparation<\/p><ul>/);
  assert.match(html,/data-act="source-group"/);assert.match(html,/>2 reviews<\/button>/);
  assert.match(html,/>Your profile<\/button>/);assert.doesNotMatch(html,/\* <strong>/);
});

test('incomplete profile hides task navigation and completed profile uses the agreed order',()=>{
  const h=harness();h.elements['#mode-bar']=node();
  h.evaluate("S.me={account:{name:'Test'},profile:null,access:{courses:[]}};S.catalog.demo_available=true;frame('profile');");
  assert.doesNotMatch(h.elements['#nav'].innerHTML,/Explore courses/);assert.equal(h.elements['#mode-bar'].innerHTML,'');
  h.evaluate("S.me.profile={program_id:'ai'};frame('contribute');");
  const nav=h.elements['#nav'].innerHTML;
  assert.ok(nav.indexOf('>Profile')<nav.indexOf('>Contribute'));
  assert.ok(nav.indexOf('>Contribute')<nav.indexOf('>Explore courses'));
  assert.equal(h.elements['#mode-bar'].innerHTML,'');
  h.evaluate("frame('explore');");assert.match(h.elements['#mode-bar'].innerHTML,/Try demo evidence/);
});

test('Next is initially disabled and becomes available after a valid answer',()=>{
  const h=harness();h.evaluate("S.me={account:{name:'Test'},access:{courses:[]}};S.schema={hours:['6–10']};S.review={course:{course_code:'CSCI570',instructor:'Example',term:'Fall 2026'},answers:{},position:0,previous:null,number:1,total:1};wizard();");
  assert.match(h.elements['#main'].innerHTML,/type="submit" disabled/);
  const next=node();next.disabled=true;
  h.elements['#review-answer']={querySelector:s=>s==='button[type=submit]'?next:null};
  h.evaluate("S.review.answers[0]='6–10';updateReviewControls();");
  assert.equal(next.disabled,false);
});

test('Too early excludes other drivers and normal selection clears Too early',()=>{
  const h=harness();h.evaluate("S.page='review';S.schema={};S.review={course:{course_code:'CSCI570'},answers:{},position:1};");
  const coding={name:'answer',value:'Coding assignments',checked:true,dataset:{},matches:()=>false,closest:()=>true};
  const early={name:'answer',value:'Too early to tell',checked:true,dataset:{},matches:()=>false,closest:()=>true};
  const next=node();h.elements['#review-answer']={querySelector:s=>s==='button[type=submit]'?next:s.includes('Too early')?early:null,querySelectorAll:s=>s.includes(':checked')?[coding,early].filter(x=>x.checked):[coding,early]};
  h.events.change({target:early});assert.equal(coding.checked,false);
  coding.checked=true;h.events.change({target:coding});assert.equal(early.checked,false);
  clearTimeout(h.evaluate('S.review.timer'));
});

test('sharing stays disabled until the consent checkbox is selected',()=>{
  const h=harness();const share=node();share.disabled=true;h.elements['[data-act=submit-review]']=share;
  const consent={id:'consent',name:'',checked:true,dataset:{},matches:()=>false,closest:()=>null};
  h.events.change({target:consent});assert.equal(share.disabled,false);
  consent.checked=false;h.events.change({target:consent});assert.equal(share.disabled,true);
});

test('editing a preview answer saves it and returns directly to the preview',async()=>{
  const h=harness();h.evaluate("S.me={account:{name:'Test'},access:{courses:[]}};S.schema={hours:['6–10','11–15'],labels:['Hours','Drivers','Background','Combination','Learning','Advice']};S.review={course:{course_code:'CSCI570',term:'Fall 2026',instructor:'Example'},answers:{0:'6–10',1:['Projects'],2:'Some prior background',3:{courses:[],balance:'Not assessed / only course'},4:'Learning experience',5:'Start work early'},position:6,previous:null,number:1,total:1};");
  routeFetch(h,{'/api/reviews/draft':{ok:true}});
  const edit={...node(),dataset:{act:'edit-answer',index:'0'}};
  h.events.click({target:{closest:()=>edit}});await wait();
  assert.equal(h.evaluate('S.review.position'),0);
  const next=node(),choice={value:'11–15'};
  const form={id:'review-answer',querySelector:s=>s==='button[type=submit]'?next:choice};h.elements['#review-answer']=form;
  h.events.submit({target:form,preventDefault(){}});await wait();
  assert.equal(h.evaluate('S.review.position'),6);
  assert.match(h.elements['#main'].innerHTML,/11–15/);
  assert.match(h.elements['#main'].innerHTML,/Ready to share/);
});

test('source display preserves the full course set and shows differing provenance dates',()=>{
  const h=harness();h.evaluate("S.schema={labels:['Hours','Drivers','Background','Combination','Learning','Advice']};");
  const value={id:1,citation:'R:1',course_code:'CSCI570',contributor_name:'Student',instructor:'Example',term:'Fall 2026',submitted_at:'2026-11-14T12:00:00Z',review_kind:'follow-up',answers:Array.from({length:6},()=>({value:'Some written experience',written_at:'2026-11-14T12:00:00Z',confirmed_at:'2026-11-14T12:00:00Z',state:'new'}))};
  value.answers[1].value=['Projects'];
  value.answers[3].value={courses:['CSCI455X'],balance:'Manageable with planning'};
  value.answers[2].written_at='2026-10-20T12:00:00Z';value.answers[2].state='reconfirmed';
  h.context.reviewFixture=value;
  const html=h.evaluate("sourceHTML(reviewFixture)");
  assert.match(html,/CSCI570 \+ CSCI455X/);
  assert.equal((html.match(/class="answer-date"/g)||[]).length,1);
  assert.match(html,/reconfirmed/);
});

test('pair comparison ratings and evidence types stay visibly separate',()=>{
  const h=harness();h.evaluate("S.schema={labels:[]};");
  h.context.turnFixture={question:'Compare',result:{answer:'Different experiences. [P:profile]',mode:'ai',notice:'Test',dataset_mode:'demo',student_sources:[],evidence_summary:{review_count:18,unique_contributors:10},profile_source:{citation:'P:profile',courses:[],completed_units:0,in_progress_units:4},combination_groups:[{courses:['CSCI402','CSCI561'],unique_contributors:4,balance:{'Difficult to balance':2}},{courses:['CSCI402','CSCI567'],unique_contributors:4,balance:{'Unsustainable so far':1}}]}};
  const html=h.evaluate('turnHTML(turnFixture)');
  assert.match(html,/18 reviews from 10 contributors/);
  assert.match(html,/CSCI402 \+ CSCI561/);assert.match(html,/CSCI402 \+ CSCI567/);
  assert.match(html,/Your self-reported profile/);assert.match(html,/fictional student experiences/);
});
