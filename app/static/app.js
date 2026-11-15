'use strict';
const EXPECTED_BUILD = '2026.11.15.5';
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const S = {catalog:null, me:null, csrf:'', login:false, page:'account', academic:null, schema:null, profile:null, review:null, selected:new Set(), course:null, section:'workload', filters:{term:'',instructor:''}, conversations:{}, mine:[], evidenceMode:'real', epoch:0};
const sections = {workload:'Workload', preparation:'Preparation', learning:'Learning experience', combinations:'Course combinations'};
const dateText = d => d ? new Date(d).toLocaleDateString(undefined,{year:'numeric',month:'short',day:'numeric'}) : '';
const monthNow = () => new Date().toISOString().slice(0,7);
const termNow = () => `${new Date().getMonth()<4?'Spring':new Date().getMonth()<7?'Summer':'Fall'} ${new Date().getFullYear()}`;
const formatValue = value => Array.isArray(value) ? value.join(', ') : value && typeof value==='object' ? `${value.courses.join(' + ') || 'No combination assessed'} · ${value.balance}` : String(value ?? 'No change');
function status(message='',success=false){const el=$('#status');el.textContent=message;el.classList.toggle('success',success);}
async function api(path,method='GET',body){
  const epoch=S.epoch;
  const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-Evidence-Mode':S.evidenceMode,...(S.csrf?{'X-CSRF-Token':S.csrf}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
  let data;try{data=await response.json();}catch{throw Error('The server could not complete the request.');}
  if(epoch!==S.epoch){const error=Error('Discarding a response from an earlier session.');error.name='AbortError';throw error;}
  if(!response.ok){if(response.status===401&&S.me){S.epoch++;if(S.review){clearTimeout(S.review.timer);S.review=null;}S.me=null;S.csrf='';S.conversations={};S.evidenceMode='real';account();}throw Error(Array.isArray(data.detail)?data.detail.map(x=>`${x.field || 'Form'}: ${x.message}`).join('; '):data.detail || 'Please try again.');}return data;
}
async function run(button,work){if(button?.disabled)return;status();if(button){button.disabled=true;button.setAttribute('aria-busy','true');}try{await work();}catch(e){if(e.name==='AbortError')return;status(e.message);$('#status').scrollIntoView({block:'nearest'});}finally{if(button?.isConnected){button.disabled=false;button.removeAttribute('aria-busy');}}}
function frame(page){
  S.page=page;if(document.body)document.body.dataset.page=page;
  const reading=['explore','course','compare'].includes(page),bar=$('#mode-bar');
  if(bar)bar.innerHTML=S.me&&S.me.profile&&reading&&S.catalog.demo_available?`<div class="mode-strip ${S.evidenceMode==='demo'?'demo-strip':''}"><div><b>${S.evidenceMode==='demo'?'Simulated demo evidence':'Student feedback'}</b><span>${S.evidenceMode==='demo'?'Fictional students, instructors and experiences. Your own reviews remain separate.':'Answers use submitted student reviews and the linked program reference.'}</span></div><button class="button secondary" data-act="toggle-evidence">${S.evidenceMode==='demo'?'Use real reviews':'Try demo evidence'}</button></div>`:'';
  const due=S.me?.access?.courses.filter(c=>!c.fresh).length || 0;
  $('#nav').innerHTML=S.me?`${S.me.profile?`<button data-act="profile" class="${page==='profile'?'selected':''}">Profile</button><button data-act="contribute" class="${['contribute','review'].includes(page)?'selected':''}">Contribute ${due?`<span class="count">${due}</span>`:''}</button><button data-act="explore" class="${reading?'selected':''}">Explore courses</button>`:''}<span class="profile-name">${esc(S.me.account.name)}</span><button data-act="logout">Sign out</button>`:'';
}
function focusMain(){document.getElementById('main').focus({preventScroll:true});window.scrollTo({top:0});}
async function refresh(){
  S.me=await api('/me');S.csrf=S.me.csrf;
  if(S.me.profile){[S.academic,S.schema]=await Promise.all([api('/explore'),api('/review-schema')]);S.mine=(await api('/reviews/mine')).reviews;}
}
function account(){
  frame('account');
  $('#main').innerHTML=`<div class="center narrow"><div class="intro"><img class="intro-icon" src="/static/torch.svg" alt=""><span class="eyebrow">Pass the Torch</span><h1>${S.login?'Sign in':'Create your account'}</h1><p>Explore your MS CS requirements and course experiences shared by USC students. Contribute feedback from the courses you take.</p></div><section class="panel"><form id="account-form">${S.login?'':'<label>Full name<input name="name" autocomplete="name" minlength="2" maxlength="80" required></label>'}<label>USC email<input name="email" type="email" autocomplete="username" placeholder="you@usc.edu" maxlength="254" required></label><label>Password<small>Use a new password with at least 12 characters.</small><input name="password" type="password" autocomplete="${S.login?'current-password':'new-password'}" minlength="12" maxlength="128" required></label><button class="button full" type="submit">${S.login?'Sign in':'Create account'}</button></form><button class="button quiet full" data-act="toggle-login">${S.login?'Create an account':'Already registered? Sign in'}</button><p class="small muted">USC membership is self-reported in this prototype. Your email is private. Shared reviews display your name to signed-in students.</p></section></div>`;
}
function terms(value){const year=new Date().getFullYear(),out=[];for(let y=year-6;y<=year+4;y++)for(const season of ['Spring','Summer','Fall'])out.push(`${season} ${y}`);if(value&&!out.includes(value))out.unshift(value);return out.map(t=>`<option ${t===value?'selected':''}>${t}</option>`).join('');}
function instructorControl(c,i){const names=c.names || [];return `<label>Instructor ${names.length?`<select data-key="instructor-choice" data-index="${i}"><option value="">Select instructor</option>${names.map(n=>`<option value="${esc(n)}" ${n===c.instructor?'selected':''}>${esc(n)}</option>`).join('')}<option value="__manual" ${c.instructor&&!names.includes(c.instructor)?'selected':''}>Enter instructor name</option></select>`:''}<input data-key="instructor" value="${esc(c.instructor || '')}" placeholder="Instructor’s full name" minlength="2" maxlength="100" required ${names.length&&names.includes(c.instructor)?'readonly':''}><small>${names.length?'Names are student-reported; enter a missing instructor manually.':'Enter the instructor’s name. An official roster is not connected.'}</small></label>`;}
function academicTerms(value,graduation=false){
  const year=new Date().getFullYear(),opts=[];
  for(let y=year-6;y<=year+8;y++)for(const [term,month] of (graduation?[['Spring','05'],['Summer','08'],['Fall','12']]:[['Spring','01'],['Summer','05'],['Fall','08']]))opts.push([`${y}-${month}`,`${term} ${y}`]);
  if(value&&!opts.some(([v])=>v===value))opts.unshift([value,`${new Date(value+'-15T12:00:00').toLocaleDateString(undefined,{month:'long',year:'numeric'})} (saved)`]);
  return `<option value="">Select semester and year</option>`+opts.map(([v,label])=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(label)}</option>`).join('');
}
function courseTitle(code){const c=S.catalog.courses.find(c=>c.code===code);return c&&c.title!==code?c.title:'';}
function captureProfile(){const f=$('#profile-form');if(!f)return;const data=new FormData(f);S.profile={...S.profile,program_id:data.get('program_id'),start_date:data.get('start_date'),graduation_date:data.get('graduation_date'),courses:[...f.querySelectorAll('.course-entry')].map((row,i)=>({...S.profile.courses[i],code:row.querySelector('[data-key=code]').value,status:row.querySelector('[data-key=status]').value,term:row.querySelector('[data-key=term]').value,instructor:row.querySelector('[data-key=instructor]').value}))};}
function profile(){
  frame('profile');
  if(!S.profile)S.profile={...(S.me.profile || {program_id:'',start_date:'',graduation_date:''}),courses:S.me.courses.map(c=>({...c,code:c.course_code}))};
  const p=S.profile;
  $('#main').innerHTML=`<div class="center"><div class="step-line"><span>Account</span><i></i><b>Program & courses</b><i></i><span>Reviews</span><i></i><span>Explore</span></div><div class="intro compact"><h1>Your program and courses</h1><p>Your track determines the requirements shown. Add the courses you have completed and those you are taking now.</p></div><form id="profile-form" class="stack"><section class="panel"><label>MS CS track<select name="program_id" required><option value="">Select your track</option>${S.catalog.programs.map(x=>`<option value="${x.id}" ${p.program_id===x.id?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label><div class="two"><label>Program start<select name="start_date" required>${academicTerms(p.start_date)}</select></label><label>Expected graduation<select name="graduation_date" required>${academicTerms(p.graduation_date,true)}</select></label></div></section><section class="panel"><div class="row between"><h2>Course history</h2><button class="button secondary" type="button" data-act="add-course">+ Add course</button></div><p class="small muted">Incoming students can leave this empty. Planned courses are explored after setup.</p><datalist id="course-list">${S.catalog.courses.map(c=>`<option value="${c.code}">${esc(c.title)}</option>`).join('')}</datalist>${p.courses.map((c,i)=>`<fieldset class="course-entry" data-index="${i}"><legend>Course ${i+1}</legend><label>Course code<small>Type a code or search the suggestions by name.</small><input data-key="code" data-index="${i}" list="course-list" value="${esc(c.code)}" placeholder="CSCI570" maxlength="20" required></label><div class="two"><label>Status<select data-key="status"><option value="current" ${c.status==='current'?'selected':''}>Currently taking</option><option value="completed" ${c.status==='completed'?'selected':''}>Completed</option></select></label><label>Semester<select data-key="term" data-index="${i}">${terms(c.term)}</select></label></div><div class="instructor-area">${instructorControl(c,i)}</div><button type="button" class="button quiet" data-act="remove-course" data-index="${i}">Remove course</button></fieldset>`).join('') || '<p class="empty">No courses entered.</p>'}</section><div class="row end"><button class="button" type="submit">Save academic profile →</button></div></form></div>`;
}
function accessNotice(){const a=S.me.access;return a.unlocked?'':`<div class="notice"><div class="row between"><span>${esc(a.reason)}</span><button class="button secondary" data-act="contribute">Complete reviews →</button></div></div>`;}
function courseCard(c){
  const enrolled=S.me.courses.find(x=>x.course_code===c.code),state=c.option_status || enrolled?.status || 'remaining';
  const labels={completed:'Already completed',current:'In progress',remaining:'Remaining option',needs_review:'Needs adviser review'};
  return `<article class="course-card"><div class="row between"><h3>${esc(c.code)}</h3><span class="pill">${c.units} units</span></div><p>${c.title!==c.code?esc(c.title):'Title not included in this snapshot'}</p><span class="pill ${state==='completed'?'green':''}">${labels[state]}</span><p class="small muted">${esc(c.option_reason || '')}</p><span class="small">${c.contributor_count?`${c.contributor_count} ${S.evidenceMode==='demo'?'simulated contributors':'contributors'} · all reported terms`:'No student feedback yet'}</span><div class="row between"><button class="button secondary" data-act="course" data-code="${c.code}">Explore →</button><label class="check-inline"><input type="checkbox" data-compare="${c.code}" ${S.selected.has(c.code)?'checked':''}> Compare</label></div></article>`;
}
function searchResults(){
  const query=($('#course-search')?.value || '').trim().toLowerCase(),filter=$('#course-filter')?.value || 'all';
  const target=$('#search-results');if(!query&&filter==='all'){if(target)target.innerHTML='<p class="small muted">Search by code or title, filter for feedback, or use the requirements checklist above.</p>';return;}
  const matches=(S.academic.courses || []).filter(c=>(!query||`${c.code} ${c.title}`.toLowerCase().includes(query))&&(filter==='all'||(filter==='with_feedback'?c.contributor_count>0:c.option_status===filter)));
  const out=$('#search-results');if(out)out.innerHTML=`<p class="small muted">${matches.length} course options · eligibility and prerequisites require confirmation</p><div class="cards">${matches.map(courseCard).join('') || '<p class="empty">No matching courses.</p>'}</div>`;
}
function compareBar(){return S.selected.size?`<div class="toolbar row between"><p><strong>${S.selected.size} courses selected</strong> · ${[...S.selected].map(esc).join(' + ')}</p><button class="button secondary" data-act="compare" ${S.selected.size<2?'disabled':''}>Compare courses →</button></div>`:'';}
function explore(){
  if(!S.me.profile)return profile();frame('explore');const p=S.academic.progress;
  const prep=S.academic.requirements.filter(r=>r.label.includes('preparatory')).flatMap(r=>r.options).filter(c=>['current','completed'].includes(c.option_status));
  $('#main').innerHTML=`<div class="row between overview-head"><div><span class="eyebrow">${esc(p.program)}</span><h1>Your degree requirements</h1></div><button class="button" data-act="plan">Ask about my plan ↓</button></div><p class="muted">Explore remaining requirements, compare courses and ask AI about student experiences.</p>${accessNotice()}<div class="stats"><div class="stat"><b>${p.completed.degree_units}<small> / ${p.target_degree_units}</small></b><span>completed degree units</span></div><div class="stat"><b>${p.projected.degree_units-p.completed.degree_units}</b><span>degree units in progress</span></div><div class="stat"><b>${Math.max(0,p.target_degree_units-p.projected.degree_units)}</b><span>remaining if current courses are passed</span></div></div>${prep.length?`<p class="small prep-note">Tracked separately: ${prep.map(c=>`${esc(c.code)} · ${c.units} preparatory units · ${c.option_status==='current'?'in progress':'completed'}`).join('; ')}. Preparatory units are excluded from the ${p.target_degree_units} degree-unit total.</p>`:''}<details class="planning-reference"><summary>${p.rules_applicable?'Program reference and planning notes':'Earlier cohort: confirm your applicable catalogue'}</summary><p class="small muted">${esc(p.notes)}</p><p class="small muted">Grades, prerequisites, approvals and future offerings need confirmation. <a href="${esc(p.source_url)}" target="_blank" rel="noopener noreferrer">USC program source ↗</a> · Snapshot ${esc(p.snapshot_date)}</p></details><div id="compare-bar">${compareBar()}</div><section class="section-head"><h2>Requirements & course options</h2></section>${S.academic.requirements.map(r=>`<details class="requirement"><summary><b>${esc(r.label)}${r.courses.length===1&&courseTitle(r.courses[0])?`<small>${esc(courseTitle(r.courses[0]))}</small>`:''}</b><span class="pill ${r.status==='completed'?'green':''}">${esc(({remaining:'Still needed',current:'In progress',completed:'Completed'})[r.status] || r.status)}</span></summary><div class="requirement-body">${r.detail?`<p class="small muted">${esc(r.detail)}</p>`:''}<div class="cards">${r.options.map(courseCard).join('') || '<p class="empty">This option needs a catalogue check.</p>'}</div></div></details>`).join('')}${p.group_details.length?`<section class="panel"><h3>Elective breadth</h3><p class="small">${p.required_group_courses} group courses spanning at least ${p.required_group_diversity} groups are required.</p>${p.group_details.map(g=>`<p class="small"><strong>${esc(g.label)}</strong> · completed: ${g.completed.length}; including current: ${g.projected.length}</p>`).join('')}</section>`:''}${p.projected.manual_review.length?`<section class="notice"><strong>Manual review needed</strong>${p.projected.manual_review.map(c=>`<p class="small">${esc(c.code)}: ${esc(c.reason)}</p>`).join('')}</section>`:''}<section class="panel course-search-panel"><h2>Find a course</h2><div class="two"><label>Course code or title<input id="course-search" type="search" placeholder="402, Machine Learning…"></label><label>Show<select id="course-filter"><option value="all">All track options</option><option value="remaining">Remaining options</option><option value="current">In progress</option><option value="completed">Already completed</option><option value="needs_review">Needs adviser review</option><option value="with_feedback">With feedback</option></select></label></div><div id="search-results"></div></section><section id="plan-chat" class="panel chat-panel"><h2>Ask about courses and your plan</h2>${chatHTML('requirements',[])}</section>`;
  searchResults();
}
function contribute(){
  if(!S.me.profile)return profile();frame('contribute');const a=S.me.access,required=a.courses,done=required.filter(c=>c.fresh).length,initial=required.some(c=>!c.review_id);
  const other=S.me.courses.filter(c=>!required.some(r=>r.course_code===c.course_code)),shared=[...new Set(S.mine.map(r=>r.course_code))];
  $('#main').innerHTML=`<div class="center"><div class="intro compact"><h1>Your course reviews</h1><p>Your answers become evidence for AI course guidance. Check in for each course every three weeks.</p></div>${a.unlocked?`<section class="notice green review-success"><strong>${a.incoming?'Your profile is ready.':required.length===2?'Both reviews shared.':'Your reviews are up to date.'}</strong><p>You can now explore courses and ask AI.</p><button class="button" data-act="explore">Explore courses →</button></section>`:`<p class="small muted">Complete a review for each listed course to unlock AI questions. You can view your degree checklist now.</p>`}<section class="panel"><div class="row between"><h2>${done} of ${required.length} ${initial?'initial reviews completed':'up to date'}</h2>${a.unlocked?'':'<span class="pill">Reviews needed</span>'}</div><progress max="${Math.max(1,required.length)}" value="${done}" aria-label="Course reviews completed"></progress>${required.length?required.map((c,i)=>`<article class="review-item"><div class="row between"><div><h3>${esc(c.course_code)}</h3>${courseTitle(c.course_code)?`<p class="small">${esc(courseTitle(c.course_code))}</p>`:''}<p class="small muted">${esc(c.instructor)} · ${esc(c.term)}</p><span class="small ${c.fresh?'review-ready':'muted'}">${c.fresh?`Next check-in ${dateText(c.due_at)}`:c.review_id?'Check-in due':'Initial review needed'}</span></div><button class="button ${c.fresh?'secondary':''}" data-act="review" data-code="${c.course_code}" data-number="${i+1}" data-total="${required.length}">${c.review_id?'Update review':'Review course'} →</button></div></article>`).join(''):`<p class="small muted">${esc(a.reason)}</p><button class="button secondary" data-act="profile">Edit course history</button>`}<p class="small muted">Shared reviews display your name, instructor and semester. AI answers the questions.</p></section>${other.length?`<section class="panel"><h2>Other completed courses</h2>${other.map(c=>`<div class="review-item row between"><span>${esc(c.course_code)} · ${esc(c.term)}</span><button class="button secondary" data-act="review" data-code="${c.course_code}">Share experience →</button></div>`).join('')}</section>`:''}${shared.length?`<details class="source manage-feedback"><summary>Manage shared feedback</summary><p class="small muted">Removing a course’s reviews removes its full check-in history from future answers.</p>${shared.map(code=>`<div class="row between review-item"><span class="small">${esc(code)}</span><button class="button quiet" data-act="delete-reviews" data-code="${code}">Remove my reviews</button></div>`).join('')}</details>`:''}</div>`;
}
async function beginReview(code,number='1',total='1'){
  const data=await api('/reviews/latest/'+encodeURIComponent(code));const c=S.me.courses.find(x=>x.course_code===code);const previous=data.review;
  const draft=data.draft&&data.draft.previous_id===(previous?.id ?? null)?data.draft:null;
  const answers=draft?.answers || Object.fromEntries((previous?.answers || []).map((a,i)=>[String(i),[2,4,5].includes(i)?null:i===1?{drivers:a.value,other:a.other_text || ''}:a.value]));
  S.review={course:c,previous,answers,position:draft?.position || 0,number,total};wizard();focusMain();
}
function choices(name,options,value,multi=false){return `<div class="choices">${options.map(v=>`<label class="choice"><input type="${multi?'checkbox':'radio'}" name="${name}" value="${esc(v)}" ${(multi?(value || []).includes(v):value===v)?'checked':''}>${esc(v)}</label>`).join('')}</div>`;}
function captureReview(){const r=S.review;if(!r||r.position===6)return;const i=r.position,f=$('#review-answer');if(!f)return;
  if(i===0)r.answers[i]=f.querySelector('[name=answer]:checked')?.value;
  else if(i===1)r.answers[i]={drivers:[...f.querySelectorAll('[name=answer]:checked')].map(x=>x.value),other:f.querySelector('[name=other]')?.value || ''};
  else if(i===3)r.answers[i]={courses:[...f.querySelectorAll('[name=paired]:checked')].map(x=>x.value),balance:f.querySelector('[name=answer]:checked')?.value};
  else r.answers[i]=f.querySelector('[name=unchanged]:checked')?null:f.querySelector('textarea').value;
}
function driverAnswer(value){return Array.isArray(value)?{drivers:value,other:''}:value || {drivers:[],other:''};}
function validReviewAnswer(){
  const r=S.review,i=r.position,v=r.answers[i];
  if(i===0&&!S.schema.hours.includes(v))throw Error('Choose an hours range.');
  if(i===1){const d=driverAnswer(v);if(!d.drivers.length)throw Error('Choose at least one activity.');if(d.drivers.includes('Too early to tell')&&d.drivers.length>1)throw Error('Use Too early to tell on its own.');if(d.drivers.includes('Other')&&d.other.trim().length<2)throw Error('Describe the other activity.');}
  if(i===3&&(!v?.balance||(!v.courses.length&&v.balance!==S.schema.balance.at(-1))))throw Error('Select the other courses you mean, or choose Not assessed / only course.');
  if([2,4,5].includes(i)&&!(v===null&&r.previous)&&(!(typeof v==='string')||v.trim().length<10))throw Error('Write at least 10 characters, or choose Too early to tell.');
}
function reviewReady(){try{validReviewAnswer();return true;}catch{return false;}}
function updateReviewControls(){
  if(!S.review||S.review.position===6)return;
  const f=$('#review-answer');if(!f)return;const next=f.querySelector('button[type=submit]');if(next)next.disabled=!reviewReady();
  const other=S.review.position===1?f.querySelector('#other-driver'):null;if(other){const selected=driverAnswer(S.review.answers[1]).drivers.includes('Other');other.hidden=!selected;const input=other.querySelector('input');input.disabled=!selected;input.required=selected;}
}
function reviewValue(value,index,code,answer=null){
  if(index===1){const d=driverAnswer(value);return d.drivers.join(', ')+(d.other?`: ${d.other}`:answer?.other_text?`: ${answer.other_text}`:'');}
  if(index===3&&value&&typeof value==='object')return `${value.courses.length?[...new Set([code,...value.courses])].join(' + '):'No combination assessed'} · ${value.balance}`;
  return formatValue(value);
}
async function saveReviewDraft(position){
  const r=S.review;if(!r)return;clearTimeout(r.timer);
  const ownerEpoch=S.epoch,revision=r.revision || 0,payload={course_code:r.course.course_code,answers:JSON.parse(JSON.stringify(r.answers)),position,previous_id:r.previous?.id ?? null};
  r.pending=(r.pending || Promise.resolve()).catch(()=>{}).then(()=>{if(ownerEpoch!==S.epoch){const e=Error('Session changed');e.name='AbortError';throw e;}return api('/reviews/draft','PUT',payload);});
  await r.pending;if((r.revision || 0)===revision)r.dirty=false;
  const saved=$('#draft-state');if(saved&&S.review===r)saved.textContent=r.dirty?'Saving changes…':'Draft saved privately · shared only after you submit';
}
async function leaveReview(){if(S.page!=='review'||!S.review)return;captureReview();await saveReviewDraft(S.review.position);S.review=null;}
function scheduleDraft(){const r=S.review;if(!r||S.page!=='review')return;captureReview();r.revision=(r.revision || 0)+1;r.dirty=true;updateReviewControls();const saved=$('#draft-state');if(saved)saved.textContent='Saving privately…';clearTimeout(r.timer);r.timer=setTimeout(()=>{if(S.review!==r)return;saveReviewDraft(r.position).catch(()=>{const el=$('#draft-state');if(el)el.textContent='Not saved yet. Use Save & return before leaving.';});},400);}
function wizard(){
  frame('review');const r=S.review,i=r.position,c=r.course,v=r.answers[i],prev=r.previous?.answers[i];
  const prompts=[`In a typical week, how many hours do you spend on ${c.course_code} outside class?`,'Which activities take the most time in this course?','What knowledge or skills has this course expected you to already understand?','How manageable is this course alongside your other courses?','What has helped or made it difficult for you to learn in this course?','What should a student know before registering?'];
  let field='';
  if(i===0)field=choices('answer',S.schema.hours,v);
  if(i===1){const d=driverAnswer(v);field=choices('answer',S.schema.drivers,d.drivers,true)+`<label id="other-driver" ${d.drivers.includes('Other')?'':'hidden'}>Please specify<input name="other" value="${esc(d.other)}" minlength="2" maxlength="300" ${d.drivers.includes('Other')?'required':'disabled'}></label>`;}
  if(i===3){const peers=S.me.courses.filter(p=>p.term===c.term&&p.course_code!==c.course_code);field=`<p class="small muted">Select the same-semester courses you are assessing together with ${esc(c.course_code)}.</p>${peers.length?choices('paired',peers.map(p=>p.course_code),v?.courses,true):'<p class="small muted">No other same-semester courses are listed.</p>'}${choices('answer',S.schema.balance,v?.balance)}`;}
  if([2,4,5].includes(i))field=`${prev?`<div class="previous"><b>Previous answer · written ${dateText(prev.written_at)}</b><br>${esc(prev.value)}</div><label class="check"><input type="checkbox" name="unchanged" ${v===null?'checked':''}>No change; I still stand by this answer.</label>`:''}<label>Your experience<textarea name="answer" maxlength="1800" minlength="10" ${v===null&&prev?'disabled':''} placeholder="A specific example or a few sentences is enough.">${esc(v===null?prev?.value:v)}</textarea></label><button type="button" class="button quiet" data-act="too-early">Too early to tell</button>`;
  const summary=i===6?Array.from({length:6},(_,n)=>{const old=r.answers[n]===null,answer=old?r.previous.answers[n]:null;return `<div class="summary-answer"><div class="row between"><b>${n+1}. ${esc(S.schema.labels[n])}</b><button class="button quiet" data-act="edit-answer" data-index="${n}" aria-label="Edit ${esc(S.schema.labels[n])}">Edit</button></div>${old?'<span class="muted">Reconfirming previous answer: </span>':''}${esc(reviewValue(old?answer.value:r.answers[n],n,c.course_code,answer))}</div>`;}).join(''):'';
  $('#main').innerHTML=`<div class="center review-wizard"><div class="wizard-head"><button class="button quiet" data-act="save-exit">← Save & return to reviews</button><div class="row between"><span class="eyebrow">Course ${esc(r.number)} of ${esc(r.total)} · ${r.previous?'Check-in':'Initial review'}</span><strong>${esc(c.course_code)}</strong></div><p class="small muted">${esc(c.instructor)} · ${esc(c.term)} · ${r.previous?'Update what changed.':'Your experience of the course so far.'}</p><div class="question-count"><span>${i===6?'Review your answers':`Question ${i+1} of 6`}</span><strong>${i===6?'Ready to share':`${5-i} more after this`}</strong></div><progress value="${i}" max="6" aria-label="Questions completed"></progress></div><section class="panel">${i===6?`<h2>Review & share</h2>${summary}<div class="divider"></div><label class="check"><input id="consent" type="checkbox">I agree to share my answers, name, course, instructor and semester with signed-in students and allow my answers to be used in AI responses. I can remove my shared reviews.</label><div class="row between"><button class="button secondary" data-act="review-back">← Back</button><button class="button" data-act="submit-review" disabled>Share review →</button></div>`:`<form id="review-answer"><div class="question"><h2>${esc(prompts[i])}</h2>${i===0?'<p class="small muted">Include assignments, reading, projects and studying.</p>':''}${i===1?'<p class="small muted">Select all that apply.</p>':''}${field}</div><div class="row between"><button class="button secondary" type="button" data-act="review-back" ${i===0&&!r.returnToSummary?'disabled':''}>${r.returnToSummary?'Cancel edit':'← Back'}</button><button class="button" type="submit" ${reviewReady()?'':'disabled'}>${r.returnToSummary?'Return to preview':i===5?'Review answers':'Next'} →</button></div></form>`}</section><p id="draft-state" class="small muted" role="status">Saved privately as you answer · shared only after you submit</p></div>`;
}
function sourceId(prefix,citation){return `source-${prefix}-${citation.replace(/[^a-zA-Z0-9-]/g,'-')}`;}
function sourceHTML(r,only=null,prefix=''){
  const names=S.schema.labels,indices=only || [0,1,2,3,4,5],day=d=>d?.slice(0,10);
  return `<details class="source" ${prefix?`id="${sourceId(prefix,r.citation)}"`:''}><summary>${r.is_simulated?'Simulated review':'Review'} ${r.id} · ${esc(r.course_code)} · ${esc(r.contributor_name)}<br>${esc(r.instructor)} · ${esc(r.term)} · ${dateText(r.submitted_at)}</summary><p class="small muted">${r.is_simulated?'Fictional demo experience':'Self-reported'} · ${esc(r.review_kind)} · submitted ${dateText(r.submitted_at)}</p>${indices.map(i=>{const a=r.answers[i],different=day(a.written_at)!==day(r.submitted_at)||day(a.confirmed_at)!==day(a.written_at);return `<p><strong>${esc(names[i])}</strong><br>${esc(reviewValue(a.value,i,r.course_code,a))}${different?`<span class="answer-date">Written ${dateText(a.written_at)} · ${a.state==='reconfirmed'?'reconfirmed':'reported'} ${dateText(a.confirmed_at)}</span>`:''}</p>`;}).join('')}</details>`;
}
function distribution(b){const entries=Object.entries(b.hours_distribution);return entries.length?`<div class="distribution">${entries.map(([range,n])=>`<div class="distribution-row"><span>${esc(range)}${range.includes('early')?'':' hrs'}</span><progress value="${n}" max="${b.unique_contributors}" aria-label="${esc(range)}: ${n} contributors"></progress><span>${n} student${n===1?'':'s'}</span></div>`).join('')}</div>`:'';}
function evidenceSection(b,section){const map={workload:[0,1],preparation:[2],learning:[4,5],combinations:[3]};const gaps=`<div class="${b.unique_contributors?'notice':'empty'}">${b.unique_contributors?`${b.unique_contributors} distinct ${b.is_simulated?'simulated ':''}contributor(s). These ${b.is_simulated?'fictional cases':'reports'} describe individual experiences; the amount and relevance of evidence determine what can be concluded.`:'No student experience has been shared for this selection yet. The chatbot can use available program requirements and will identify the missing experience.'}</div>`;
  let detail='';
  if(section==='workload')detail=distribution(b)+Object.entries(b.workload_drivers).map(([name,n])=>`<span class="pill">${esc(name)} · ${n}</span> `).join('');
  if(section==='combinations')detail=b.combinations.length?b.combinations.map(p=>`<div class="source"><strong>${p.courses.map(esc).join(' + ')}</strong><p>${p.contributors} contributor(s) reporting this exact set in ${esc(b.course_code)} reviews.</p><p>${Object.entries(p.balance).map(([v,n])=>`${esc(v)}: ${n}`).join(' · ')}</p></div>`).join(''):'<p class="small muted">No explicit course-combination observations in these reports.</p>';
  return `${gaps}${detail}<p class="small muted">${esc(b.scope_note)} Source cards below show up to ${b.retrieved_checkins} contributors.</p>${b.reviews.map(r=>sourceHTML(r,map[section])).join('')}`;
}
function chatKey(section,codes){return JSON.stringify([S.me?.account?.id,S.evidenceMode,section,codes,S.filters]);}
function chatHTML(section,codes){
  const key=chatKey(section,codes),turns=S.conversations[key] || [];
  return `${S.me.access.unlocked?'':accessNotice()}<button class="button secondary" data-act="summarize" ${S.me.access.unlocked?'':'disabled'}>Summarize available feedback</button><form id="chat-form" data-section="${section}" data-codes="${esc(codes.join(','))}"><label>Your question<textarea name="question" minlength="5" maxlength="2000" ${S.me.access.unlocked?'required':'disabled'} placeholder="Ask about ${section==='requirements'?'courses, workload or your remaining requirements':sections[section]?.toLowerCase()}…"></textarea></label><div class="row between"><p class="small muted">Answers use available evidence. Contributors receive no messages.</p><button type="submit" class="button" ${S.me.access.unlocked?'':'disabled'}>Ask AI →</button></div></form><details class="technical-details"><summary>How answers work</summary><p class="small muted">Your question and course history are sent to the configured AI with relevant evidence. Your name, email and password are excluded. ${S.catalog.ai_configured?`Provider: ${esc(S.catalog.ai_provider)} · model: ${esc(S.catalog.ai_model)}`:'AI is not configured; this prototype will show saved evidence.'}</p></details><div id="chat-output" class="conversation" aria-live="polite">${turns.map(turnHTML).join('')}</div>`;
}
function renderAnswer(text,refs,prefix){
  function inline(line){
    return esc(line).replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>').replace(/`([^`\n]+)`/g,'<code>$1</code>')
      .replace(/(?:\[(?:R:\d+|S:[a-z0-9-]+|P:profile)\][ \t]*)+/g,block=>{
        const ids=[...new Set([...block.matchAll(/\[((?:R:\d+|S:[a-z0-9-]+|P:profile))\]/g)].map(m=>m[1]))],known=ids.filter(id=>refs.has(id)),reviews=known.filter(id=>id.startsWith('R:')),other=known.filter(id=>!id.startsWith('R:'));
        const button=id=>`<button class="source-ref" data-act="source" data-id="${sourceId(prefix,id)}">${id.startsWith('R:')?'Review '+id.slice(2):id==='P:profile'?'Your profile':'USC reference'}</button>`;
        return (reviews.length>1?`<button class="source-ref" data-act="source-group" data-ids="${reviews.map(id=>sourceId(prefix,id)).join(',')}">${reviews.length} reviews</button>`:reviews.map(button).join(''))+other.map(button).join('')+ids.filter(id=>!refs.has(id)).map(id=>`[${id}]`).join('');
      });
  }
  // Process each line so a heading followed by a list still renders as a list.
  let html='',list=false,paragraph=[];
  const flush=()=>{if(paragraph.length){html+='<p>'+paragraph.join('<br>')+'</p>';paragraph=[];}};
  for(const raw of text.split('\n')){
    const line=raw.trim(),bullet=/^(?:[-*]|\d+\.)\s+/.test(line);
    if(bullet){flush();if(!list){html+='<ul>';list=true;}html+='<li>'+inline(line.replace(/^(?:[-*]|\d+\.)\s+/,''))+'</li>';}
    else{if(list){html+='</ul>';list=false;}if(!line){flush();}else if(/^#{1,4}\s+/.test(line)){flush();html+='<p><strong>'+inline(line.replace(/^#{1,4}\s+/,''))+'</strong></p>';}else paragraph.push(inline(line));}
  }
  if(list)html+='</ul>';flush();return html;
}
function turnHTML(t,index=0){
  const result=t.result,prefix='turn-'+index,official=result.official_sources || [],profile=result.profile_source,all=[...(result.student_sources || []).flatMap(b=>b.reviews),...(result.combination_sources || [])],reviews=[...new Map(all.map(r=>[r.citation,r])).values()];
  const refs=new Set([...official.map(r=>r.citation),...reviews.map(r=>r.citation),...(profile?[profile.citation]:[])]),counts=result.evidence_summary,scope=result.retrieval_scope,groups=new Map();
  for(const r of reviews){if(!groups.has(r.course_code))groups.set(r.course_code,[]);groups.get(r.course_code).push(r);}
  const simulated=result.dataset_mode==='demo',label=simulated?'Fictional demo feedback':'Student feedback';
  const sourceSummary=counts?`${label}: ${counts.review_count} reviews from ${counts.unique_contributors} contributor${counts.unique_contributors===1?'':'s'}`:`${label}: ${reviews.length} reviews`;
  const pairs=result.combination_groups || [];
  const pairSummary=pairs.length>1?`<div class="cards pair-summaries">${pairs.map(g=>`<section class="course-card"><h3>${g.courses.map(esc).join(' + ')}</h3><p>${g.unique_contributors} distinct ${simulated?'simulated ':''}contributors</p><p>${Object.entries(g.balance).map(([rating,n])=>`${esc(rating)}: ${n}`).join(' · ') || 'No exact-set feedback yet.'}</p></section>`).join('')}</div>`:'';
  const body=simulated?result.answer.replace(/^Simulated demo evidence — fictional student experiences\.\s*/, ''):result.answer;
  const notice=simulated?(result.mode==='ai'?'Simulated demo evidence · fictional student experiences.':'Simulated demo evidence · '+result.notice.replace(/^Simulated demo evidence\.[\s\S]*?difficulty\.\s*/,'')):result.mode==='ai'?'AI summary · check the supporting student reports.':result.notice;
  return `<article class="turn"><h3>${esc(t.question)}</h3><p class="small ${simulated?'demo-label':'muted'}">${esc(notice)}</p>${scope?`<p class="small muted">Feedback searched: ${scope.courses.map(esc).join(', ') || 'no course selected'}${scope.term?` · ${esc(scope.term)}`:''}${scope.instructor?` · ${esc(scope.instructor)}`:''}. ${esc(scope.note)}</p>`:''}${pairSummary}<div class="answer-text">${renderAnswer(body,refs,prefix)}</div><details class="source evidence-list"><summary>${esc(sourceSummary)}</summary>${[...groups].map(([code,items])=>`<details class="source course-source-group"><summary>${esc(code)} · ${items.length} review${items.length===1?'':'s'}</summary>${items.map(r=>sourceHTML(r,null,prefix)).join('')}</details>`).join('') || '<p>No matching student reviews.</p>'}</details>${official.length||profile?`<details class="source reference-list"><summary>Program reference & your profile</summary>${official.map(o=>`<details class="source" id="${sourceId(prefix,o.citation)}"><summary>USC program rules</summary><p><a href="${esc(o.url)}" target="_blank" rel="noopener noreferrer">${esc(o.title)} ↗</a><br>Snapshot ${esc(o.snapshot_date)} · department summary</p></details>`).join('')}${profile?`<details class="source" id="${sourceId(prefix,profile.citation)}"><summary>Your self-reported profile</summary><p>${profile.courses.map(c=>`${esc(c.course_code)} · ${esc(c.status)}`).join('<br>') || 'No course history entered.'}</p><p>${profile.completed_units} completed degree units; ${profile.in_progress_units} degree units in progress. Calculated using the program reference.</p></details>`:''}</details>`:''}</article>`;
}
async function openCourse(code,reset=true){if(reset){S.filters={term:'',instructor:''};S.section='workload';}const query=new URLSearchParams(S.filters);const b=await api('/course/'+encodeURIComponent(code)+'?'+query);if(reset)S.courseOptions={terms:b.terms,instructors:b.instructors};S.course={code,bundle:b};course();}
function course(){frame('course');const {code,bundle:b}=S.course,c=S.catalog.courses.find(c=>c.code===code)||{code,title:code,units:'?'},fit=S.academic.requirements.filter(r=>r.courses.includes(code));
  $('#main').innerHTML=`<div class="breadcrumbs"><button class="button quiet" data-act="explore">← Degree requirements</button></div><div class="row between"><div><span class="eyebrow">Course exploration</span><h1>${esc(code)}</h1><p class="muted">${esc(c.title===code?'Title not included in this snapshot':c.title)} · ${c.units} units</p></div><label class="check-inline"><input type="checkbox" data-compare="${code}" ${S.selected.has(code)?'checked':''}> Include in comparison</label></div><section class="panel"><h3>Requirement fit</h3><p class="small">${fit.length?fit.map(r=>esc(r.label)).join(' · '):'Needs adviser/catalogue review for this track.'}</p><p class="small muted">Listed as an option, subject to group breadth, unit limits, prerequisites and approvals. This does not establish enrollment eligibility or future availability.</p><a class="small" href="${esc(S.academic.progress.source_url)}" target="_blank" rel="noopener noreferrer">${esc(S.academic.progress.program)} · USC department source ↗</a></section><div id="compare-bar">${compareBar()}</div><form id="filter-form" class="row filters"><label>Semester<select name="term"><option value="">All reported semesters</option>${S.courseOptions.terms.map(t=>`<option ${S.filters.term===t?'selected':''}>${esc(t)}</option>`).join('')}</select></label><label>Instructor<select name="instructor"><option value="">All reported instructors</option>${S.courseOptions.instructors.map(t=>`<option ${S.filters.instructor===t?'selected':''}>${esc(t)}</option>`).join('')}</select></label><button class="button secondary" type="submit">Apply filters</button></form><div class="tabs" role="tablist" aria-label="Course feedback sections">${Object.entries(sections).map(([key,name])=>`<button class="tab" id="tab-${key}" role="tab" aria-controls="course-section" tabindex="${S.section===key?0:-1}" aria-selected="${S.section===key}" data-act="section" data-section="${key}">${name}</button>`).join('')}</div><section id="course-section" role="tabpanel" aria-labelledby="tab-${S.section}"><h2>${sections[S.section]}</h2>${evidenceSection(b,S.section)}<section class="panel chat-panel"><h2>Ask about ${sections[S.section].toLowerCase()}</h2>${chatHTML(S.section,[code])}</section></section>`;
}
async function compare(){const codes=[...S.selected];if(codes.length<2)throw Error('Select at least two courses to compare.');if(codes.length>5)throw Error('Compare up to five courses at a time.');S.filters={term:'',instructor:''};const [bundles,pair]=await Promise.all([Promise.all(codes.map(c=>api('/course/'+encodeURIComponent(c)))),api('/comparison?'+new URLSearchParams({codes:codes.join(',')}))]);frame('compare');$('#main').innerHTML=`<button class="button quiet" data-act="explore">← Degree requirements</button><span class="eyebrow">${S.evidenceMode==='demo'?'Simulated demo evidence · ':''}Course combinations</span><h1>Compare ${codes.map(esc).join(' + ')}</h1><p class="muted">Compare reported experiences. Different courses’ workload ranges are not added into a workload prediction.</p><div class="cards">${bundles.map(b=>`<section class="panel"><h2>${esc(b.course_code)}</h2><p class="small">${b.unique_contributors} ${b.is_simulated?'simulated ':''}contributor(s)</p>${distribution(b)}<button class="button secondary" data-act="course" data-code="${b.course_code}">Open course →</button></section>`).join('')}</div><section class="section-head"><h2>Explicit reports of this exact combination</h2><p class="small muted">${esc(pair.scope_note)}</p><div class="notice"><strong>${pair.unique_contributors} distinct ${pair.is_simulated?'simulated ':''}contributors reporting this exact combination</strong><p>${Object.entries(pair.balance).map(([v,n])=>`${esc(v)}: ${n}`).join(' · ') || 'No exact-set reports available.'}</p></div>${pair.reviews.map(r=>sourceHTML(r,[3,5])).join('')}</section><section class="panel chat-panel"><h2>Ask about this combination</h2>${chatHTML('combinations',codes)}</section>`;}

document.addEventListener('submit',event=>{
  const form=event.target;if(!['account-form','profile-form','review-answer','chat-form','filter-form'].includes(form.id))return;event.preventDefault();const button=form.querySelector('button[type=submit]');
  run(button,async()=>{
    const f=new FormData(form);
    if(form.id==='account-form'){
      S.epoch++;const result=await api(S.login?'/login':'/register','POST',Object.fromEntries(f));S.csrf=result.csrf;S.profile=null;S.conversations={};await refresh();if(S.me.profile)explore();else profile();focusMain();
    }else if(form.id==='profile-form'){
      captureProfile();S.epoch++;await api('/profile','PUT',S.profile);S.profile=null;S.conversations={};await refresh();if(S.me.access.unlocked)explore();else contribute();focusMain();
    }else if(form.id==='review-answer'){
      captureReview();validReviewAnswer();const next=S.review.returnToSummary?6:S.review.position+1;await saveReviewDraft(next);S.review.position=next;S.review.returnToSummary=false;wizard();focusMain();
    }else if(form.id==='filter-form'){
      S.filters={term:f.get('term'),instructor:f.get('instructor')};await openCourse(S.course.code,false);
    }else if(form.id==='chat-form'){
      const question=f.get('question'),section=form.dataset.section,codes=form.dataset.codes.split(',').filter(Boolean),key=chatKey(section,codes);
      const previous=S.conversations[key] || [],history=previous.slice(-3).flatMap(t=>[{role:'user',content:t.question},{role:'assistant',content:t.result.answer.slice(0,6000)}]);
      const output=$('#chat-output');const loading=document.createElement('p');loading.className='loading';loading.textContent='Reading the available sources…';loading.setAttribute('role','status');output.prepend(loading);
      try{
        const result=await api('/ask','POST',{question,courses:codes,section,history,summarize:form.dataset.summary==='true',...S.filters});
        S.conversations[key]=[...previous,{question,result}].slice(-8);
        if(output.isConnected){output.innerHTML=S.conversations[key].map(turnHTML).join('');form.querySelector('textarea').value='';output.lastElementChild?.scrollIntoView({block:'start',behavior:'smooth'});}
      }finally{delete form.dataset.summary;if(loading.isConnected)loading.remove();}
    }
  });
});
document.addEventListener('click',event=>{
  const el=event.target.closest('[data-act]');if(!el)return;const action=el.dataset.act;
  run(el,async()=>{
    if(['explore','contribute','profile','logout','course','compare','toggle-evidence'].includes(action))await leaveReview();
    if(action==='toggle-login'){S.login=!S.login;account();}
    if(action==='explore'){if(!S.me.profile)return profile();await refresh();explore();focusMain();}
    if(action==='contribute'){if(!S.me.profile)return profile();await refresh();contribute();focusMain();}
    if(action==='profile'){S.profile=null;profile();focusMain();}
    if(action==='logout'){S.epoch++;await api('/logout','POST',{});S.me=null;S.csrf='';S.profile=null;S.review=null;S.conversations={};S.evidenceMode='real';S.selected.clear();account();}
    if(action==='add-course'){captureProfile();S.profile.courses.push({code:'',status:'current',term:termNow(),instructor:'',names:[]});profile();document.querySelector('.course-entry:last-of-type input')?.focus();}
    if(action==='remove-course'){captureProfile();S.profile.courses.splice(Number(el.dataset.index),1);profile();}
    if(action==='course'){await openCourse(el.dataset.code);focusMain();}
    if(action==='compare'){await compare();focusMain();}
    if(action==='review'){await beginReview(el.dataset.code,el.dataset.number,el.dataset.total);}
    if(action==='review-back'){const r=S.review;if(r.returnToSummary){r.answers[r.position]=r.editOriginal;r.returnToSummary=false;r.position=6;}else{captureReview();r.position--;}await saveReviewDraft(r.position);wizard();focusMain();}
    if(action==='edit-answer'){const r=S.review;r.position=Number(el.dataset.index);r.returnToSummary=true;r.editOriginal=r.answers[r.position]===undefined?undefined:JSON.parse(JSON.stringify(r.answers[r.position]));await saveReviewDraft(r.position);wizard();focusMain();}
    if(action==='save-exit'){captureReview();await saveReviewDraft(S.review.position);S.review=null;contribute();status('Review draft saved privately.',true);focusMain();}
    if(action==='too-early'){const text=$('#review-answer textarea');text.disabled=false;text.value='Too early to tell.';const unchanged=$('[name=unchanged]');if(unchanged)unchanged.checked=false;scheduleDraft();}
    if(action==='submit-review'){
      if(!$('#consent').checked)throw Error('Confirm sharing your review before submitting.');
      const r=S.review;clearTimeout(r.timer);if(r.pending)await r.pending;S.epoch++;await api('/reviews','POST',{course_code:r.course.course_code,answers:Array.from({length:6},(_,i)=>r.answers[i]),previous_id:r.previous?.id ?? null,consent:true});
      S.review=null;S.conversations={};await refresh();contribute();if(!S.me.access.unlocked)status('Review shared. Complete the remaining course reviews to unlock asking.',true);focusMain();
    }
    if(action==='delete-reviews'){
      if(!window.confirm(`Remove all your shared reviews for ${el.dataset.code}?`))return;
      S.epoch++;await api('/reviews/'+encodeURIComponent(el.dataset.code),'DELETE',{});S.conversations={};await refresh();contribute();status('Your course reviews were removed from future retrieval.',true);
    }
    if(action==='summarize'){const f=$('#chat-form');f.dataset.summary='true';f.querySelector('textarea').value='What does the available feedback say?';f.requestSubmit();}
    if(action==='plan'){const el=$('#plan-chat');el.scrollIntoView({block:'start',behavior:'smooth'});el.querySelector('textarea')?.focus({preventScroll:true});}
    if(action==='toggle-evidence'){S.epoch++;S.evidenceMode=S.evidenceMode==='real'?'demo':'real';S.conversations={};await refresh();if(S.page==='course'&&S.course){await openCourse(S.course.code);}else if(S.page==='compare'){await compare();}else if(S.page==='contribute'){contribute();}else if(S.page==='profile'){profile();}else explore();}
    if(action==='source-group'){let first;for(const id of el.dataset.ids.split(',')){const target=document.getElementById(id);if(!target)continue;let p=target.parentElement;first ||= p;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement;}}first?.scrollIntoView({block:'center',behavior:'smooth'});}
    if(action==='source'){const target=document.getElementById(el.dataset.id);if(target){target.open=true;let p=target.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement;}target.scrollIntoView({block:'center',behavior:'smooth'});}}
    if(action==='section'){S.section=el.dataset.section;course();$('#tab-'+S.section).focus();}
  });
});
document.addEventListener('change',async event=>{
  const el=event.target;
  if(el.matches('[data-compare]')){
    if(el.checked&&S.selected.size>=5){el.checked=false;status('Select up to five courses for a comparison.');return;}
    if(el.checked)S.selected.add(el.dataset.compare);else S.selected.delete(el.dataset.compare);
    document.querySelectorAll(`[data-compare="${el.dataset.compare}"]`).forEach(c=>c.checked=el.checked);
    const bar=$('#compare-bar');if(bar)bar.innerHTML=compareBar();
  }
  if(el.id==='course-filter'){searchResults();}
  if(el.closest?.('#review-answer')){
    const f=$('#review-answer');
    if(S.review.position===1&&el.name==='answer'){
      if(el.value==='Too early to tell'&&el.checked)f.querySelectorAll('[name=answer]').forEach(x=>{if(x!==el)x.checked=false;});
      else if(el.checked){const early=f.querySelector('[name=answer][value="Too early to tell"]');if(early)early.checked=false;}
    }
    if(el.name==='unchanged'){const text=f.querySelector('textarea');text.disabled=el.checked;}
    scheduleDraft();
  }
  if(el.id==='consent'){const button=$('[data-act=submit-review]');if(button)button.disabled=!el.checked;}
  if(el.dataset.key==='instructor-choice'){
    const input=el.closest('label').querySelector('input');input.readOnly=el.value!=='__manual';input.value=el.value==='__manual'?'':el.value;if(!input.readOnly)input.focus();
  }
  if(['code','term'].includes(el.dataset.key)){
    captureProfile();const i=Number(el.dataset.index),c=S.profile.courses[i];
    c.code=c.code.replace(/[\s-]/g,'').toUpperCase();if(/^\d{3}[A-Z]{0,2}$/.test(c.code))c.code='CSCI'+c.code;if(c.code==='CSCI455')c.code='CSCI455X';
    const row=el.closest('.course-entry');row.querySelector('[data-key=code]').value=c.code;c.instructor='';c.names=[];row.querySelector('.instructor-area').innerHTML=instructorControl(c,i);
    try{const data=await api('/instructors?'+new URLSearchParams({course:c.code,term:c.term}));
      if(row.isConnected&&row.querySelector('[data-key=code]').value===c.code&&row.querySelector('[data-key=term]').value===c.term){c.instructor=row.querySelector('[data-key=instructor]').value;c.names=data.instructors;row.querySelector('.instructor-area').innerHTML=instructorControl(c,i);}
    }catch(e){status(e.message);}
  }
});
document.addEventListener('input',event=>{if(event.target.id==='course-search')searchResults();if(event.target.closest?.('#review-answer'))scheduleDraft();});
window.addEventListener?.('beforeunload',event=>{if(S.review?.dirty){event.preventDefault();event.returnValue='';}});
document.addEventListener('keydown',event=>{
  if(event.target.matches('[role=tab]')&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
    event.preventDefault();const keys=Object.keys(sections),i=keys.indexOf(S.section),next=event.key==='Home'?0:event.key==='End'?keys.length-1:(i+(event.key==='ArrowLeft'?-1:1)+keys.length)%keys.length;
    document.querySelector(`[data-section="${keys[next]}"]`).click();
  }
});
(async()=>{
  try{S.catalog=await api('/catalog');if(S.catalog.app_version!==EXPECTED_BUILD)throw Error('An earlier Python server is running. Stop it with Ctrl+C, then start Pass the Torch from the newly extracted folder.');try{await refresh();}catch(e){if(!S.me){account();return;}throw e;}if(S.me?.profile)explore();else profile();}
  catch(e){if(!S.me)account();status(e.message);}
})();
