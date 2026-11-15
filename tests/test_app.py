import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.config import Settings
from app.data import PROGRAMS, COURSES
from app.db import connect
from app.llm import answer, build_payload
from app.main import create_app
from app.progress import calculate_progress
from app.retrieval import question_courses

PASSWORD = 'Pass-the-Torch-test-password!'


def profile(codes=('CSCI455X','CSCI570'), program='scientists-engineers'):
    return {'program_id':program,'start_date':'2026-08','graduation_date':'2028-12',
            'courses':[{'code':c,'status':'current','term':'Fall 2026','instructor':'Professor Example'} for c in codes]}


def answers(pairs=None):
    return ['11–15',['Problem sets / proofs'],'Induction and mathematical reasoning helped.',
            {'courses':pairs or [],'balance':'Manageable with planning' if pairs else 'Not assessed / only course'},
            'Office hours helped me understand the proofs.',
            'Start the assignments early and review the definitions.']


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=str(Path(self.temp.name)/'test.sqlite3')
        self.client=TestClient(create_app(Settings(db_path=self.path)))
        self.client.__enter__()
        self.register('one')

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.temp.cleanup()

    def register(self, who):
        r=self.client.post('/api/register',json={'name':who+' Student','email':who+'@usc.edu','password':PASSWORD})
        self.assertEqual(r.status_code,201,r.text)
        self.uid=r.json()['account']['id']
        self.headers={'x-csrf-token':r.json()['csrf']}

    def save(self, p=None):
        r=self.client.put('/api/profile',json=p or profile(),headers=self.headers)
        self.assertEqual(r.status_code,200,r.text)

    def review(self, code, values=None, prior=None):
        return self.client.post('/api/reviews',json={'course_code':code,'answers':values or answers(),'previous_id':prior,'consent':True},headers=self.headers)

    def ask(self, **kwargs):
        return self.client.post('/api/ask',json={'question':'What is CSCI570 workload like?',**kwargs},headers=self.headers)

    def test_current_student_unlock_requires_every_course(self):
        self.save()
        self.assertEqual(self.ask().status_code,403)
        self.assertEqual(self.review('CSCI570').status_code,201)
        self.assertFalse(self.client.get('/api/me').json()['access']['unlocked'])
        self.assertEqual(self.review('CSCI455X').status_code,201)
        self.assertTrue(self.client.get('/api/me').json()['access']['unlocked'])
        r=self.ask();self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['mode'],'evidence_only')
        self.assertEqual(r.json()['student_sources'][0]['unique_contributors'],1)
        self.assertIn('[R:',r.json()['answer'])

    def test_incoming_student_has_no_three_question_quota(self):
        p=profile(codes=());p.update(start_date='2090-08',graduation_date='2092-12');self.save(p)
        self.assertTrue(self.client.get('/api/me').json()['access']['incoming'])
        for _ in range(5):self.assertEqual(self.ask().status_code,200)
        self.save(profile(codes=('CSCI570',)))
        self.assertEqual(self.ask().status_code,403)

    def test_cannot_clear_history_to_reenter_incoming_access(self):
        self.save();p=profile(codes=());p.update(start_date='2090-08',graduation_date='2092-12');self.save(p)
        self.assertFalse(self.client.get('/api/me').json()['access']['unlocked'])
        self.assertEqual(self.ask().status_code,403)

    def test_refresh_expires_after_21_days(self):
        self.save(profile(codes=('CSCI570',)))
        rid=self.review('CSCI570').json()['id']
        future=datetime.now(timezone.utc)+timedelta(days=22)
        with patch('app.experience.now',return_value=future), patch('app.main.now',return_value=future):
            self.assertEqual(self.ask().status_code,403)
            self.assertFalse(self.client.get('/api/me').json()['access']['courses'][0]['fresh'])
            self.assertEqual(self.review('CSCI570',prior=rid).status_code,201)
            self.assertEqual(self.ask().status_code,200)

    def test_followup_preserves_written_dates_and_counts_one_person(self):
        self.save(profile(codes=('CSCI570',)))
        first=self.review('CSCI570').json()['id']
        old=self.client.get('/api/reviews/latest/CSCI570').json()['review']['answers']
        values=answers();values[0]='16–20';values[2]=values[4]=values[5]=None
        future=datetime.now(timezone.utc)+timedelta(days=10)
        with patch('app.experience.now',return_value=future), patch('app.main.now',return_value=future):
            self.assertEqual(self.review('CSCI570',values,first).status_code,201)
        b=self.client.get('/api/course/CSCI570').json()
        self.assertEqual(b['total_checkins'],2)
        self.assertEqual(b['unique_contributors'],1)
        self.assertEqual(b['hours_distribution'],{'16–20':1})
        new=b['reviews'][0]['answers']
        self.assertEqual(old[2]['written_at'],new[2]['written_at'])
        self.assertEqual(new[2]['state'],'reconfirmed')
        self.assertNotEqual(old[2]['confirmed_at'],new[2]['confirmed_at'])
        self.assertEqual(new[0]['state'],'new')

    def test_stale_review_tab_rejected(self):
        self.save(profile(codes=('CSCI570',)))
        self.assertEqual(self.review('CSCI570').status_code,201)
        self.assertEqual(self.review('CSCI570').status_code,409)

    def test_pairing_requires_explicit_same_term_history(self):
        self.save()
        self.assertEqual(self.review('CSCI570',answers(['CSCI561'])).status_code,422)
        self.assertEqual(self.review('CSCI570',answers(['CSCI455X'])).status_code,201)
        b=self.client.get('/api/course/CSCI570').json()
        self.assertEqual(b['combinations'][0]['courses'],['CSCI455X','CSCI570'])
        self.assertEqual(b['combinations'][0]['contributors'],1)

    def test_new_person_can_read_feedback_but_not_private_history(self):
        self.save(profile(codes=('CSCI570',)));self.review('CSCI570');self.register('two')
        me=self.client.get('/api/me').json()
        self.assertIsNone(me['profile']);self.assertEqual(me['courses'],[])
        p=profile(codes=());p.update(start_date='2090-08',graduation_date='2092-12');self.save(p)
        r=self.ask().json();self.assertEqual(r['student_sources'][0]['unique_contributors'],1)
        self.assertNotIn('one@usc.edu',json.dumps(r))
        self.assertEqual(r['student_sources'][0]['reviews'][0]['contributor_name'],'one Student')

    def test_draft_is_private_and_does_not_unlock(self):
        self.save(profile(codes=('CSCI570',)))
        r=self.client.put('/api/reviews/draft',json={'course_code':'CSCI570','answers':{'0':'11–15'},'position':1},headers=self.headers)
        self.assertEqual(r.status_code,200)
        self.assertFalse(self.client.get('/api/me').json()['access']['unlocked'])
        self.assertEqual(self.client.get('/api/reviews/latest/CSCI570').json()['draft']['position'],1)
        self.assertEqual(self.client.get('/api/course/CSCI570').json()['unique_contributors'],0)
        self.register('two');self.save(profile(codes=('CSCI570',)))
        self.assertIsNone(self.client.get('/api/reviews/latest/CSCI570').json()['draft'])

    def test_instructor_required_and_change_requires_new_review(self):
        p=profile(codes=('CSCI570',));p['courses'][0]['instructor']='  '
        self.assertEqual(self.client.put('/api/profile',json=p,headers=self.headers).status_code,422)
        self.save(profile(codes=('CSCI570',)));self.review('CSCI570')
        p['courses'][0]['instructor']='Different Instructor';self.save(p)
        self.assertEqual(self.ask().status_code,403)
        self.assertEqual(self.client.get('/api/course/CSCI570?instructor=Different%20Instructor').json()['unique_contributors'],0)

    def test_sources_filter_by_term_and_instructor(self):
        self.save(profile(codes=('CSCI570',)));self.review('CSCI570')
        self.assertEqual(self.client.get('/api/course/CSCI570?term=Spring%202025').json()['unique_contributors'],0)
        self.assertEqual(self.client.get('/api/course/CSCI570?instructor=Professor%20Example').json()['unique_contributors'],1)
        names=self.client.get('/api/instructors?course=CSCI570&term=Fall%202026').json()
        self.assertEqual(names['instructors'],['Professor Example'])

    def test_delete_only_own_chain_and_relock(self):
        self.save(profile(codes=('CSCI570',)));rid=self.review('CSCI570').json()['id'];self.review('CSCI570',prior=rid)
        self.register('two');self.save(profile(codes=('CSCI570',)))
        self.client.request('DELETE','/api/reviews/CSCI570',json={},headers=self.headers)
        self.assertEqual(self.client.get('/api/course/CSCI570').json()['total_checkins'],2)
        login=self.client.post('/api/login',json={'email':'one@usc.edu','password':PASSWORD}).json()
        self.headers={'x-csrf-token':login['csrf']}
        self.assertEqual(self.client.request('DELETE','/api/reviews/CSCI570',json={},headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/api/course/CSCI570').json()['total_checkins'],0)
        self.assertEqual(self.ask().status_code,403)

    def test_question_history_context_and_no_private_identity_in_model(self):
        p=profile(codes=());p.update(start_date='2090-08',graduation_date='2092-12');self.save(p)
        captured=[]
        async def capture(settings,question,bundles,progress,personal):
            captured.append(build_payload(settings,question,bundles,progress,personal))
            return {'answer':'Test','mode':'evidence_only','notice':'Test transport'}
        history=[{'role':'user','content':'What about CSCI570?'},{'role':'assistant','content':'Earlier untrusted response.'}]
        with patch('app.main.llm.answer',side_effect=capture):
            r=self.ask(question='What about preparation?',section='preparation',history=history)
        self.assertEqual(r.status_code,200)
        text=json.dumps(captured)
        self.assertIn('Earlier untrusted response.',text)
        self.assertNotIn('one@usc.edu',text);self.assertNotIn('one Student',text);self.assertNotIn(PASSWORD,text)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM experiences').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM information_requests').fetchone()[0],1)

    def test_csrf_origin_password_and_validation(self):
        self.assertEqual(self.client.put('/api/profile',json=profile()).status_code,403)
        self.assertEqual(self.client.put('/api/profile',json=profile(),headers={**self.headers,'origin':'https://evil.example'}).status_code,403)
        r=self.client.post('/api/register',json={'name':'X','email':'notusc@example.org','password':'SECRET'})
        self.assertEqual(r.status_code,422);self.assertNotIn('SECRET',r.text)
        with connect(self.path) as db:
            encoded=db.execute('SELECT password_hash FROM accounts').fetchone()[0]
            self.assertNotIn(PASSWORD,encoded);self.assertIn('600000',encoded)
        self.assertEqual(self.client.post('/api/logout',json={},headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/api/me').status_code,401)
        self.assertEqual(self.client.post('/api/login',json={'email':'one@usc.edu','password':PASSWORD}).status_code,200)

    def test_malformed_answers_and_unowned_course_rejected(self):
        self.save(profile(codes=('CSCI570',)))
        self.assertEqual(self.review('CSCI561').status_code,422)
        for index,value in ((0,99),(1,[]),(2,None),(3,{'balance':'Comfortable','courses':[]}),(4,'bad')):
            a=answers();a[index]=value
            self.assertEqual(self.review('CSCI570',a).status_code,422)

    def test_contact_details_redacted(self):
        self.save(profile(codes=('CSCI570',)));a=answers();a[5]='Contact person@usc.edu or ID 1234567890 for details.';self.review('CSCI570',a)
        text=self.client.get('/api/course/CSCI570').text
        self.assertNotIn('person@usc.edu',text);self.assertNotIn('1234567890',text)

    def test_page_uses_matching_versioned_assets_and_disables_cache(self):
        import hashlib
        import re
        from app.version import BUILD_ID
        page=self.client.get('/')
        self.assertEqual(page.headers['cache-control'],'no-store')
        for filename in ('app.js','styles.css','torch.svg'):
            digest=hashlib.sha256((Path('app/static')/filename).read_bytes()).hexdigest()[:12]
            url='/static/'+filename+'?v='+digest
            self.assertIn(url,page.text)
            asset=self.client.get(url)
            self.assertEqual(asset.status_code,200)
            self.assertEqual(asset.headers['cache-control'],'no-store')
        for node in ('nav','main','status'):
            self.assertIn('id="'+node+'"',page.text)
        self.assertEqual(self.client.get('/api/catalog').json()['app_version'],BUILD_ID)
        self.assertIn(BUILD_ID,Path('app/static/app.js').read_text(encoding='utf-8'))
        self.assertNotIn('Coursewise could not start',Path('app/static/app.js').read_text(encoding='utf-8'))

    def test_degree_options_and_static_assets(self):
        self.save();r=self.client.get('/api/explore').json()
        self.assertEqual(r['progress']['completed']['degree_units'],0)
        self.assertEqual(r['progress']['projected']['degree_units'],4)
        self.assertTrue(any('CSCI402' in r['courses'] for r in r['requirements']))
        page=self.client.get('/');self.assertEqual(page.status_code,200);self.assertIn('Pass the Torch',page.text)
        self.assertEqual(self.client.get('/static/torch.svg').status_code,200)
        self.assertIn("frame-ancestors 'none'",page.headers['content-security-policy'])
        self.assertEqual(self.client.get('/api/me').headers['cache-control'],'no-store')
class RuleTests(unittest.TestCase):
    def calculate(self, program_id, codes, current=(), start="2026-08"):
        p=next(p for p in PROGRAMS if p["id"]==program_id)
        p={**p,"source_url":p["url"],"snapshot_date":"2026-11-14"}
        return calculate_progress(p,[{"course_code":c,"status":"current" if c in current else "completed"} for c in codes],
                                  {k:{"units":v[0]} for k,v in COURSES.items()},start)

    def test_program_specific_foundation_and_current_credit(self):
        r=self.calculate("scientists-engineers",["CSCI455X","CSCI402","CSCI570","EE450","EE457","CSCI561"],current=["CSCI561"])
        self.assertEqual(r["completed"]["degree_units"],12)
        self.assertEqual(r["projected"]["degree_units"],16)
        self.assertIn("EE457",[x["code"] for x in r["projected"]["manual_review"]])
        self.assertEqual(r["target_degree_units"],33)

    def test_ai_groups_and_different_required_core(self):
        r=self.calculate("ai",["CSCI561","CSCI566","CSCI567","CSCI570","CSCI544","CSCI535","CSCI563","CSCI587"])
        self.assertEqual(r["completed"]["degree_units"],32)
        self.assertEqual(sum(bool(g["completed"]) for g in r["group_details"]),2)
        self.assertEqual(len(r["requirements"]),4)
        self.assertFalse(r["audit_complete"])

    def test_general_600_unit_cap_and_unknowns(self):
        r=self.calculate("general",["CSCI570","CSCI616","CSCI617","CSCI619","CSCI999"])
        self.assertEqual(r["completed"]["degree_units"],12)
        self.assertEqual(len(r["completed"]["manual_review"]),2)

    def test_scientists_engineers_one_doctoral_course_cap(self):
        r=self.calculate("scientists-engineers",["CSCI616","CSCI617"])
        self.assertEqual(r["completed"]["degree_units"],4)

    def test_data_science_dsci_cap(self):
        r=self.calculate("data-science",["DSCI551","DSCI553","DSCI554","DSCI558"])
        self.assertEqual(r["completed"]["degree_units"],12)
        self.assertEqual(len(r["completed"]["manual_review"]),1)

    def test_game_emphasis_and_historical_cohort_warning(self):
        codes="CSCI570 CSCI561 CSCI580 CTIN532L CTIN541 CSCI529A CSCI529B CSCI567".split()
        r=self.calculate("game",codes,start="2023-08")
        self.assertEqual(r["completed"]["degree_units"],32)
        self.assertFalse(r["rules_applicable"])
        self.assertIn("predates",r["warnings"][0])

    def test_extract_question_courses(self):
        self.assertEqual(question_courses("Can I take 402 + CSCI 561 and EE 450?",[]),["CSCI402","CSCI561","EE450"])



class ModelTests(unittest.TestCase):
    def setUp(self):
        self.settings=Settings(api_key='test-key-not-real',model='configured-test-model')
        stamp='2026-11-14T20:00:00+00:00'
        self.bundles=[{'course_code':'CSCI570','unique_contributors':1,'total_checkins':1,'retrieved_checkins':1,
                       'hours_distribution':{'11–15':1},'workload_drivers':{'Projects':1},'combinations':[],
                       'reviews':[{'id':1,'citation':'R:1','contributor_name':'Private Author','term':'Fall 2026',
                                   'instructor':'Example','enrollment_status':'current','answers':[{'value':v,'written_at':stamp,'confirmed_at':stamp,'state':'new'} for v in answers()]}]}]

    def test_payload_privacy_and_storage(self):
        p=build_payload(self.settings,'Tell me about 570',self.bundles,None)
        self.assertFalse(p['store']);self.assertNotIn('Private Author',json.dumps(p));self.assertNotIn('test-key-not-real',json.dumps(p))

    def test_adapter_accepts_cited_output(self):
        def handler(request):
            self.assertEqual(str(request.url),'https://api.openai.com/v1/responses')
            self.assertEqual(request.headers['authorization'],'Bearer test-key-not-real')
            return httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':'One student reported 11–15 hours outside class. [R:1]'}]}]})
        result=asyncio.run(answer(self.settings,'Tell me about 570',self.bundles,None,transport=httpx.MockTransport(handler)))
        self.assertEqual(result['mode'],'ai')

    def test_invalid_citation_and_outage_fallback(self):
        for response in [httpx.Response(500,text='private error'),httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':'Invented. [R:999]'}]}]})]:
            result=asyncio.run(answer(self.settings,'Tell me about 570',self.bundles,None,transport=httpx.MockTransport(lambda request:response)))
            self.assertEqual(result['mode'],'evidence_only');self.assertNotIn('private error',json.dumps(result));self.assertNotIn('Invented',result['answer'])

class GeminiTests(unittest.TestCase):
    def setUp(self):
        ModelTests.setUp(self)
        self.settings=Settings(api_key='fake-google-key',model='gemini-3.5-flash-lite',provider='gemini')

    def test_gemini_request_and_source_citation(self):
        def handler(request):
            self.assertEqual(str(request.url),'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent')
            self.assertEqual(request.headers['x-goog-api-key'],'fake-google-key')
            self.assertNotIn('fake-google-key',str(request.url))
            payload=json.loads(request.content)
            self.assertIn('systemInstruction',payload)
            self.assertNotIn('tools',payload)
            self.assertNotIn('Private Author',json.dumps(payload))
            return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'thought':True,'text':'INTERNAL NOT FOR DISPLAY'},{'text':'One contributor reported 11–15 hours. [R:1]'}]}}]})
        result=asyncio.run(answer(self.settings,'Tell me about 570',self.bundles,None,transport=httpx.MockTransport(handler)))
        self.assertEqual(result['mode'],'ai')
        self.assertIn('Gemini',result['notice'])
        self.assertNotIn('INTERNAL',result['answer'])

    def test_gemini_invalid_citations_and_incomplete_output_fallback(self):
        for reason,text in [('STOP','Unsupported claim [R:999]'),('MAX_TOKENS','Truncated [R:1]')]:
            transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'candidates':[{'finishReason':reason,'content':{'parts':[{'text':text}]}}]}))
            result=asyncio.run(answer(self.settings,'Tell me about 570',self.bundles,None,transport=transport))
            self.assertEqual(result['mode'],'evidence_only')

    def test_provider_errors_are_actionable_without_raw_secrets(self):
        for code in (400,401,403,404,429,500):
            transport=httpx.MockTransport(lambda request:httpx.Response(code,text='Sensitive upstream details fake-google-key'))
            result=asyncio.run(answer(self.settings,'Tell me about 570',self.bundles,None,transport=transport))
            self.assertEqual(result['error_code'],f'provider_{code}')
            self.assertNotIn('fake-google-key',json.dumps(result))
            self.assertNotIn('Sensitive upstream',json.dumps(result))

    def test_timeout_falls_back(self):
        def handler(request):
            raise httpx.ReadTimeout('private connection detail',request=request)
        result=asyncio.run(answer(self.settings,'Tell me about 570',self.bundles,None,transport=httpx.MockTransport(handler)))
        self.assertEqual(result['error_code'],'provider_timeout')
        self.assertNotIn('private connection',json.dumps(result))


class ProviderConfigurationTests(unittest.TestCase):
    def test_provider_selects_only_its_own_key(self):
        import os
        values={'COURSEWISE_AI_PROVIDER':'gemini','GEMINI_API_KEY':'fake-google-key','GEMINI_MODEL':'models/gemini-3.5-flash-lite','OPENAI_API_KEY':'fake-openai-key','OPENAI_MODEL':'other-model'}
        with patch.dict(os.environ,values,clear=True),patch('app.config.load_local_env'):
            settings=Settings.from_env()
        self.assertEqual(settings.provider,'gemini')
        self.assertEqual(settings.api_key,'fake-google-key')
        self.assertEqual(settings.model,'gemini-3.5-flash-lite')
        self.assertTrue(settings.ai_configured)

    def test_missing_configuration_never_calls_provider(self):
        settings=Settings(provider='gemini',api_key='',model='gemini-3.5-flash-lite')
        def unexpected(request):
            raise AssertionError('No API request without a key')
        result=asyncio.run(answer(settings,'What should I take?',[],None,transport=httpx.MockTransport(unexpected)))
        self.assertEqual(result['mode'],'evidence_only')

    def test_catalog_never_returns_key(self):
        with tempfile.TemporaryDirectory() as directory:
            settings=Settings(db_path=str(Path(directory)/'test.sqlite3'),provider='gemini',api_key='fake-google-secret',model='gemini-3.5-flash-lite')
            with TestClient(create_app(settings)) as client:
                response=client.get('/api/catalog')
                self.assertEqual(response.json()['ai_provider'],'gemini')
                self.assertTrue(response.json()['ai_configured'])
                self.assertNotIn('fake-google-secret',response.text)

if __name__=='__main__':
    unittest.main()
