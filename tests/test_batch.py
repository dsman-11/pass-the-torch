import asyncio
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.config import Settings
from app.db import connect, initialize
from app.llm import normalize_citations, answer
from app.main import create_app
from app.models import normalize_course
import test_app as base
from test_app import profile, answers


class CitationTests(unittest.TestCase):
    def test_grouped_real_refs_normalize_but_invalid_course_refs_fail(self):
        allowed={'R:1','R:2','S:scientists-engineers'}
        self.assertEqual(normalize_citations('Supported. [R:1, R:2]',allowed),'Supported. [R:1] [R:2]')
        for text in ['Claim [R:CSCI402, R:CSCI561] [S:scientists-engineers]',
                     'Claim [R:999] [R:1]', 'Claim R:1 [R:2]', 'Claim [R:1',
                     'Claim [ R:CSCI402 ] [S:scientists-engineers]']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                normalize_citations(text,allowed)

    def test_screenshot_failure_falls_back_in_adapter(self):
        settings=Settings(api_key='fake',model='test')
        text='Missing workload [R:CSCI402, R:CSCI561]. Degree [S:scientists-engineers].'
        transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':text}]}]}))
        progress={'program_id':'scientists-engineers','program':'MS CS','completed':{'degree_units':0},'projected':{'degree_units':4},'target_degree_units':33,'rules_applicable':True}
        result=asyncio.run(answer(settings,'What about 402 and 561?',[],progress,transport=transport))
        self.assertEqual(result['mode'],'evidence_only')
        self.assertNotIn('[R:CSCI',result['answer'])


class BatchAppTests(unittest.TestCase):
    setUp = base.AppTests.setUp
    tearDown = base.AppTests.tearDown
    register = base.AppTests.register
    save = base.AppTests.save
    review = base.AppTests.review
    ask = base.AppTests.ask
    def test_demo_is_separate_and_exact_combo_counts_people_once(self):
        self.save()
        self.review('CSCI570')
        real=self.client.get('/api/course/CSCI402').json()
        self.assertEqual(real['unique_contributors'],0)
        headers={'x-evidence-mode':'demo'}
        demo=self.client.get('/api/course/CSCI402',headers=headers).json()
        self.assertEqual(demo['unique_contributors'],8)
        self.assertTrue(all(r['is_simulated'] for r in demo['reviews']))
        self.assertTrue(all(r['instructor'].startswith('Demo ') for r in demo['reviews']))
        pair=self.client.get('/api/comparison?codes=CSCI402,CSCI561',headers=headers).json()
        self.assertEqual(pair['unique_contributors'],4)  # not 8 course reports
        self.assertEqual(sum(pair['balance'].values()),4)
        empty=self.client.get('/api/course/CSCI566',headers=headers).json()
        self.assertEqual(empty['unique_contributors'],0)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM accounts').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM experiences').fetchone()[0],1)
        # Demo source selection cannot satisfy real contribution requirements.
        self.assertEqual(self.client.post('/api/ask',json={'question':'What about 402?'},headers={**self.headers,**headers}).status_code,403)

    def test_demo_ask_labels_simulation_and_model_receives_no_names(self):
        self.save(profile(codes=('CSCI570',)))
        self.review('CSCI570')
        contexts=[]
        async def capture(settings,question,bundles,progress,personal):
            contexts.append(personal)
            return {'answer':'An illustrative comparison.','mode':'ai','notice':'Test model'}
        with patch('app.main.llm.answer',side_effect=capture):
            r=self.client.post('/api/ask',json={'question':'Compare 402 and 561'},headers={**self.headers,'x-evidence-mode':'demo'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertIn('fictional',r.json()['answer'])
        self.assertEqual(contexts[0]['dataset_mode'],'simulated')
        self.assertEqual(contexts[0]['combination_evidence']['unique_contributors'],4)
        self.assertNotIn('Demo Student',json.dumps(contexts))
        self.assertTrue(r.json()['combination_sources'])

    def test_alternate_pairs_have_separate_deduplicated_sources(self):
        self.save(profile(codes=('CSCI570',)));self.review('CSCI570')
        contexts=[]
        async def capture(settings,question,bundles,progress,personal):
            contexts.append(personal)
            return {'answer':'Two different pairs.','mode':'ai','notice':'Test'}
        with patch('app.main.llm.answer',side_effect=capture):
            r=self.client.post('/api/ask',json={'question':'Compare 402 + 561 with 402 + 567'},headers={**self.headers,'x-evidence-mode':'demo'})
        self.assertEqual(r.status_code,200)
        groups=contexts[0]['related_combinations']
        self.assertEqual({tuple(g['courses']):g['unique_contributors'] for g in groups},
                         {('CSCI402','CSCI561'):4,('CSCI402','CSCI567'):4})
        self.assertNotIn('Demo Student',json.dumps(groups))

    def test_options_use_current_credit_history(self):
        p=profile(codes=('CSCI616',));p['courses'][0]['status']='completed';self.save(p)
        data=self.client.get('/api/explore').json()
        selected=next(c for c in data['courses'] if c['code']=='CSCI617')
        self.assertEqual(selected['option_status'],'needs_review')
        self.assertIn('600-level',selected['option_reason'])
        old=next(c for c in data['courses'] if c['code']=='CSCI616')
        self.assertEqual(old['option_status'],'completed')
        demo=self.client.get('/api/explore',headers={'x-evidence-mode':'demo'}).json()
        self.assertEqual(next(c for c in demo['courses'] if c['code']=='CSCI402')['contributor_count'],8)

    def test_current_question_replaces_old_course_context(self):
        self.save(profile(codes=('CSCI570',)));self.review('CSCI570')
        captured=[]
        async def capture(settings,question,bundles,progress,personal):
            captured.append([b['course_code'] for b in bundles])
            return {'answer':'Test','mode':'ai','notice':'Test'}
        with patch('app.main.llm.answer',side_effect=capture):
            self.ask(question='Compare 402 and 567 instead',history=[{'role':'user','content':'Compare 402 and 561'}])
        self.assertEqual(captured[0],['CSCI402','CSCI567'])

    def test_existing_455_feedback_migrates_without_changing_id_or_dates(self):
        self.save(profile(codes=('CSCI455X','CSCI570')))
        rid=self.review('CSCI455X').json()['id']
        values=answers(['CSCI455X']);self.review('CSCI570',values)
        with connect(self.path) as db:
            original=dict(db.execute('SELECT * FROM experiences WHERE id=?',(rid,)).fetchone())
            db.execute("UPDATE student_courses SET course_code='CSCI455' WHERE course_code='CSCI455X'")
            db.execute("UPDATE experiences SET course_code='CSCI455' WHERE id=?",(rid,))
            other=db.execute("SELECT id,answers_json FROM experiences WHERE course_code='CSCI570'").fetchone()
            data=json.loads(other['answers_json']);data[3]['value']['courses']=['CSCI455']
            db.execute('UPDATE experiences SET answers_json=? WHERE id=?',(json.dumps(data),other['id']))
            db.execute("DELETE FROM migrations WHERE id='455-alias-v1'")
        opened_backups=[]
        original_connect=sqlite3.connect
        def track_backup(path,*args,**kwargs):
            connection=original_connect(path,*args,**kwargs)
            if Path(path).parent.name=='backups':
                opened_backups.append(connection)
            return connection
        with patch('app.migrations.sqlite3.connect',side_effect=track_backup):
            initialize(self.path)
        self.assertEqual(len(opened_backups),1)
        with self.assertRaises(sqlite3.ProgrammingError):
            opened_backups[0].execute('SELECT 1')
        with connect(self.path) as db:
            migrated=dict(db.execute('SELECT * FROM experiences WHERE id=?',(rid,)).fetchone())
            self.assertEqual(migrated['course_code'],'CSCI455X')
            self.assertEqual(migrated['submitted_at'],original['submitted_at'])
            self.assertEqual(migrated['answers_json'],original['answers_json'])
            other=json.loads(db.execute("SELECT answers_json FROM experiences WHERE course_code='CSCI570'").fetchone()[0])
            self.assertEqual(other[3]['value']['courses'],['CSCI455X'])
        backups=list((Path(self.path).parent/'backups').glob('*.sqlite3'))
        self.assertEqual(len(backups),1)
        self.assertEqual(self.client.get('/api/reviews/latest/CSCI455').json()['review']['id'],rid)
        self.assertEqual(normalize_course('455'),'CSCI455X')
        self.assertEqual(self.client.get('/api/course/CSCI455').json()['unique_contributors'],1)
        initialize(self.path)
        self.assertEqual(len(list((Path(self.path).parent/'backups').glob('*.sqlite3'))),1)

    def test_complete_demo_journey_uses_real_contributions_and_simulated_sources(self):
        self.save(profile(codes=('CSCI455','CSCI570')))
        self.assertEqual(self.review('455').status_code,201)
        rid=self.review('CSCI570').json()['id']
        self.assertTrue(self.client.get('/api/me').json()['access']['unlocked'])
        overview=self.client.get('/api/explore',headers={'x-evidence-mode':'demo'}).json()
        self.assertEqual(overview['progress']['projected']['degree_units'],4)
        self.assertTrue(any(r['status']=='remaining' for r in overview['requirements']))
        self.assertEqual(self.client.get('/api/comparison?codes=402,561',headers={'x-evidence-mode':'demo'}).json()['unique_contributors'],4)
        result=self.client.post('/api/ask',json={'question':'What about 402 and 561?'},headers={**self.headers,'x-evidence-mode':'demo'}).json()
        self.assertEqual(result['dataset_mode'],'demo')
        self.assertIn('R:',json.dumps(result['student_sources']))
        new=answers();new[2]=new[4]=new[5]=None
        self.assertEqual(self.review('CSCI570',new,rid).status_code,201)
        review=self.client.get('/api/reviews/latest/CSCI570').json()['review']
        self.assertEqual(review['answers'][2]['state'],'reconfirmed')


class WalkthroughTests(unittest.TestCase):
    setUp = base.AppTests.setUp
    tearDown = base.AppTests.tearDown
    register = base.AppTests.register
    save = base.AppTests.save
    review = base.AppTests.review
    ask = base.AppTests.ask

    def test_general_summary_retrieves_current_reviews_and_deduplicates_people(self):
        self.save(profile(codes=('CSCI455X','CSCI570')))
        self.review('CSCI455X',answers(['CSCI570']))
        self.review('CSCI570',answers(['CSCI455X']))
        captured=[]
        async def capture(settings,question,bundles,progress,personal):
            captured.extend(bundles)
            return {'answer':'One contributor shared two reviews. [R:1] [R:2]','mode':'ai','notice':'Test'}
        with patch('app.main.llm.answer',side_effect=capture):
            response=self.ask(question='What does the available feedback say?',summarize=True,history=[{'role':'user','content':'What about CSCI566?'}])
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertEqual(data['evidence_summary'],{'review_count':2,'unique_contributors':1})
        self.assertEqual({b['course_code'] for b in captured if b['reviews']},{'CSCI455X','CSCI570'})
        self.assertIn('current/recent',data['retrieval_scope']['note'])
        self.assertLessEqual(len(data['retrieval_scope']['courses']),5)
        self.assertEqual(data['profile_source']['citation'],'P:profile')
        self.assertEqual(data['profile_source']['in_progress_units'],4)

    def test_summary_respects_selected_course_and_instructor_filters(self):
        self.save(profile(codes=('CSCI570',)));self.review('CSCI570')
        data=self.ask(question='What does the available feedback say?',courses=['CSCI570'],instructor='Different instructor').json()
        self.assertEqual(data['retrieval_scope']['courses'],['CSCI570'])
        self.assertEqual(data['evidence_summary']['review_count'],0)
        self.assertEqual(data['student_sources'][0]['unique_contributors'],0)

    def test_demo_comparison_returns_independent_rating_groups(self):
        self.save(profile(codes=('CSCI570',)));self.review('CSCI570')
        result=self.client.post('/api/ask',json={'question':'Compare 402 + 561 with 402 + 567'},headers={**self.headers,'x-evidence-mode':'demo'}).json()
        groups={tuple(g['courses']):g for g in result['combination_groups']}
        self.assertEqual(groups[('CSCI402','CSCI561')]['balance']['Difficult to balance'],2)
        self.assertEqual(groups[('CSCI402','CSCI567')]['balance']['Unsustainable so far'],1)
        self.assertTrue(all(g['unique_contributors']==4 for g in groups.values()))
        self.assertEqual(result['evidence_summary']['unique_contributors'],10)
        self.assertNotIn('one Student',json.dumps(result['student_sources']))

    def test_other_driver_is_saved_and_remains_available_on_followup(self):
        self.save(profile(codes=('CSCI570',)))
        values=answers();values[1]={'drivers':['Other','Reading'],'other':'Debugging my local environment'}
        rid=self.review('CSCI570',values).json()['id']
        first=self.client.get('/api/reviews/latest/CSCI570').json()['review']['answers'][1]
        self.assertEqual(first['value'],['Other','Reading'])
        self.assertEqual(first['other_text'],'Debugging my local environment')
        values[2]=values[4]=values[5]=None
        self.assertEqual(self.review('CSCI570',values,rid).status_code,201)
        new=self.client.get('/api/reviews/latest/CSCI570').json()['review']['answers'][1]
        self.assertEqual(new['written_at'],first['written_at'])
        self.assertEqual(new['state'],'reconfirmed')
        values[1]['other']=''
        self.assertEqual(self.review('CSCI570',values,new.get('id')).status_code,409)
        # Validation also applies to a fresh initial submission.
        self.register('other');self.save(profile(codes=('CSCI570',)))
        self.assertEqual(self.review('CSCI570',values).status_code,422)

    def test_legacy_cookie_session_survives_upgrade_and_logs_out(self):
        token=self.client.cookies.get('pass_the_torch_session')
        self.client.cookies.clear()
        self.client.cookies.set('coursewise_session',token)
        self.assertEqual(self.client.get('/api/me').status_code,200)
        self.assertEqual(self.client.post('/api/logout',json={},headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/api/me').status_code,401)


class WalkthroughModelTests(unittest.TestCase):
    setUp=base.ModelTests.setUp

    def test_model_receives_named_background_field_instead_of_positional_answers(self):
        from app.llm import build_payload
        payload=build_payload(self.settings,'What should I know?',self.bundles,None)
        context=json.loads(payload['input'][0]['content'])
        review=context['student_evidence'][0]['reviews'][0]
        self.assertNotIn('answers',review)
        self.assertEqual(review['feedback']['expected_prior_background']['value'],'Induction and mathematical reasoning helped.')
        self.assertIn('learning_experience',review['feedback'])

    def test_observed_category_reversal_is_rejected_but_faithful_advice_is_accepted(self):
        self.bundles[0]['reviews'][0]['answers'][2]['value']='Proof by induction, sorting run times'
        for text,expected in [('CSCI 570 covers proof by induction and sorting run times. [R:1]','evidence_only'),
                              ('One student recommends prior familiarity with proof by induction and sorting run times. [R:1]','ai'),
                              ('CSCI570 expected background includes proof by induction and sorting run times; this does not establish that they are taught. [R:1]','ai')]:
            transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':text}]}]}))
            result=asyncio.run(answer(self.settings,'What background?',self.bundles,None,transport=transport))
            self.assertEqual(result['mode'],expected)
            if expected=='evidence_only':self.assertEqual(result['error_code'],'background_interpretation')

    def test_profile_citations_are_validated_independently_from_program_sources(self):
        self.assertEqual(normalize_citations('Your current course. [P:profile]',{'P:profile'}),'Your current course. [P:profile]')
        with self.assertRaises(ValueError):normalize_citations('Unknown [P:someone-else]',{'P:profile'})


class BrandingCompatibilityTests(unittest.TestCase):
    def test_new_setting_names_win_and_legacy_names_remain_valid(self):
        import os
        values={'PASS_THE_TORCH_DB':'data/new.sqlite3','COURSEWISE_DB':'data/old.sqlite3',
                'PASS_THE_TORCH_AI_PROVIDER':'gemini','GEMINI_API_KEY':'fake','GEMINI_MODEL':'gemini-test'}
        with patch.dict(os.environ,values,clear=True),patch('app.config.load_local_env'):
            self.assertEqual(Settings.from_env().db_path,'data/new.sqlite3')
        del values['PASS_THE_TORCH_DB']
        with patch.dict(os.environ,values,clear=True),patch('app.config.load_local_env'):
            self.assertEqual(Settings.from_env().db_path,'data/old.sqlite3')

    def test_previous_default_database_is_preferred_without_explicit_configuration(self):
        import os
        with patch.dict(os.environ,{},clear=True),patch('app.config.load_local_env'),patch('app.config.Path.is_file',return_value=True):
            self.assertEqual(Path(Settings.from_env().db_path),Path('data')/'coursewise.sqlite3')
