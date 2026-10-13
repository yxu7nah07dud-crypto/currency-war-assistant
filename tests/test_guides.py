"""Public-guide pagination and exact-code regression tests; synthetic data only."""
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock, patch

from currency_war_assistant.api import GuideClient
from currency_war_assistant.controller import Controller
from currency_war_assistant.share import trait_hints


def guide(identifier, code=None):
    return {'id':identifier,'title':'Synthetic '+identifier,'description':'Synthetic instructions',
            'tourn_detail':{'share_code':code or 'Q09ERQ=='+identifier,
                            'role_stages':[{'stage':'Final','front_roles':[{'id':'role'}]}]}}


class GuideTests(unittest.TestCase):
    def setUp(self):
        cache=Path(__file__).resolve().parent/'_cache'
        cache.mkdir(exist_ok=True)
        directory=cache/('guides-'+uuid.uuid4().hex)
        directory.mkdir()
        def cleanup():
            assert directory.resolve().parent==cache.resolve()
            for path in directory.iterdir():
                path.unlink()
            directory.rmdir()
        self.addCleanup(cleanup)
        self.client=GuideClient(directory)
        self.client.page_delay=0

    def pages(self, order='Hot', page=1, token='', **filters):
        expected='' if page==1 else order+str(page-1)
        self.assertEqual(expected,token)
        return {'list':[guide(order+str(page))], 'next_page_token':order+str(page) if page<6 else ''}

    def test_reads_both_orders_past_old_three_page_limit(self):
        with patch.object(self.client,'list_page',side_effect=self.pages):
            result=self.client.refresh()
        self.assertEqual(12,len(result))
        self.assertEqual('complete',self.client.coverage['state'])
        self.assertTrue(all(s['done'] for s in self.client.coverage['orders'].values()))
        restored=GuideClient(self.client.cache)
        self.assertEqual(12,len(restored.cached_guides()))
        self.assertEqual('complete',restored.coverage['state'])

    def test_user_agent_tracks_application_version(self):
        from currency_war_assistant import __version__
        self.assertEqual('CurrencyWarAssistant/'+__version__,self.client.headers['User-Agent'])

    def test_second_manual_refresh_reads_heads_without_changing_coverage(self):
        with patch.object(self.client,'list_page',side_effect=self.pages) as request:
            self.client.refresh()
            first=request.call_count
            before=self.client.summary()['coverage']
            request.reset_mock()
            self.client.refresh()
            self.assertEqual(4,request.call_count)
            self.assertLess(request.call_count,first)
            self.assertEqual(before,self.client.coverage)

    def test_incremental_failure_preserves_complete_baseline(self):
        with patch.object(self.client,'list_page',side_effect=self.pages):self.client.refresh()
        before=self.client.summary()['coverage']
        with patch.object(self.client,'list_page',side_effect=OSError('offline')):self.client.refresh()
        self.assertEqual(before,self.client.coverage)

    def test_old_complete_coverage_is_fully_refreshed(self):
        with patch.object(self.client,'list_page',side_effect=self.pages):self.client.refresh()
        self.client.coverage['completed_at']=time.time()-86401
        with patch.object(self.client,'list_page',side_effect=self.pages) as request:self.client.refresh()
        self.assertEqual(12,request.call_count)

    def test_page_budget_is_partial_and_resumes_at_saved_token(self):
        with patch.object(self.client,'list_page',side_effect=self.pages):
            self.client.refresh(pages=3)
        self.assertEqual('partial',self.client.coverage['state'])
        resumed=GuideClient(self.client.cache);resumed.page_delay=0
        with patch.object(resumed,'list_page',side_effect=self.pages) as request:
            resumed.refresh()
        self.assertEqual(4,request.call_args_list[0].args[1])
        self.assertEqual('complete',resumed.coverage['state'])
        self.assertEqual(12,len(resumed.cached_guides()))

    def test_network_failure_keeps_pages_and_marks_incomplete(self):
        def response(*args,**kwargs):
            if args[1]==3:raise OSError('offline fixture')
            return self.pages(*args,**kwargs)
        with patch.object(self.client,'list_page',side_effect=response):
            result=self.client.refresh()
        self.assertEqual(2,len(result))
        self.assertEqual('interrupted',self.client.coverage['state'])
        self.assertFalse(self.client.online)
        with patch.object(self.client,'list_page',side_effect=self.pages):
            self.client.refresh()
        self.assertEqual('complete',self.client.coverage['state'])

    def test_stale_resume_token_restarts_stream_once(self):
        self.client.cached_guides()
        self.client.coverage={'state':'interrupted','orders':{'Hot':{'page':7,'token':'STALE','done':False}}}
        def response(order,page,token):
            if token=='STALE':raise OSError('expired cursor')
            return self.pages(order,page,token)
        with patch.object(self.client,'list_page',side_effect=response) as request:self.client.refresh()
        self.assertEqual(('Hot',8,'STALE'),request.call_args_list[0].args)
        self.assertEqual(('Hot',1,''),request.call_args_list[1].args)
        self.assertEqual('complete',self.client.coverage['state'])

    def test_only_two_complete_absences_remove_guides_and_lock_is_protected(self):
        self.client._merge([guide('gone'),guide('locked')])
        with patch.object(self.client,'list_page',return_value={'list':[guide('present')],'next_page_token':''}):
            self.client.refresh(full=True,protected_ids={'locked'})
            self.assertIn('gone',{g['id'] for g in self.client.cached_guides()})
            self.client.refresh()  # Incremental updates do not age old records.
            self.assertIn('gone',{g['id'] for g in self.client.cached_guides()})
            self.client.refresh(full=True,protected_ids=lambda:{'locked'})
        self.assertEqual({'locked','present'},{g['id'] for g in self.client.cached_guides()})
        self.assertTrue(all(g.get('last_seen') for g in self.client.cached_guides()))

    def test_legacy_cache_and_interrupted_scan_do_not_age_twice(self):
        from currency_war_assistant.paths import write_json
        write_json(self.client.cache/'guides.json',{'guides':[guide('old')]})
        self.assertEqual(0,self.client.cached_guides()[0]['missing_full_syncs'])
        with patch.object(self.client,'list_page',side_effect=OSError('offline')):self.client.refresh()
        self.assertEqual(0,self.client.cached_guides()[0]['missing_full_syncs'])

    def test_failed_restart_does_not_loop_and_saves_reset(self):
        self.client.cached_guides()
        self.client.coverage={'state':'interrupted','orders':{'Hot':{'page':7,'token':'STALE','done':False}}}
        with patch.object(self.client,'list_page',side_effect=OSError('offline')) as request:self.client.refresh()
        self.assertEqual(2,request.call_count)
        self.assertEqual('interrupted',self.client.coverage['state'])
        self.assertEqual('',self.client.coverage['orders']['Hot']['token'])

    def test_repeated_tokens_never_report_complete(self):
        with patch.object(self.client,'list_page',return_value={'list':[guide('same')],'next_page_token':'same-token'}):
            self.client.refresh()
        self.assertEqual('interrupted',self.client.coverage['state'])
        self.assertIn('分页重复',self.client.error)

    def test_raw_code_is_resolved_beyond_three_pages_and_detail_is_validated(self):
        wanted=guide('Hot6')
        with patch.object(self.client,'list_page',side_effect=self.pages), patch.object(self.client,'detail',return_value=wanted):
            found=self.client.resolve_code(wanted['tourn_detail']['share_code'])
        self.assertEqual(wanted,found)
        self.assertNotEqual('complete',self.client.coverage['state'])
        self.assertEqual(wanted,self.client.cached_guides()[-1])

    def test_official_detail_with_different_code_cannot_be_locked(self):
        wanted=guide('a','Q09ERUE=')
        self.client._merge([wanted])
        with patch.object(self.client,'detail',return_value=guide('a','Q09ERUI=')):
            with self.assertRaisesRegex(RuntimeError,'不一致'):
                self.client.resolve_code('Q09ERUE=')

    def test_missing_code_search_is_full_after_recent_incremental_baseline(self):
        with patch.object(self.client,'list_page',side_effect=self.pages):self.client.refresh()
        self.client.coverage['completed_at']=time.time()-301
        wanted=guide('Hot6','TkVXQ09ERQ==')
        def updated(order,page,token):
            result=self.pages(order,page,token)
            if order=='Hot' and page==6:result['list']=[wanted]
            return result
        with patch.object(self.client,'list_page',side_effect=updated) as request,patch.object(self.client,'detail',return_value=wanted):
            self.assertEqual(wanted,self.client.resolve_code(wanted['tourn_detail']['share_code']))
        self.assertEqual(6,request.call_count)
        self.assertEqual('interrupted',self.client.coverage['state'])

    def test_unsuccessful_code_lookup_preserves_existing_lock_during_full_scan(self):
        with patch.object(self.client,'list_page',side_effect=self.pages):self.client.refresh()
        locked=guide('locked');locked['missing_full_syncs']=1
        self.client._merge([locked]);self.client.coverage['completed_at']=time.time()-301
        with patch.object(self.client,'list_page',side_effect=self.pages):
            self.assertIsNone(self.client.resolve_code('Tk9UUFJFU0VOVA==',protected_ids=lambda:{'locked'}))
        self.assertIn('locked',{g['id'] for g in self.client.cached_guides()})
        self.assertEqual('complete',self.client.coverage['state'])

    def test_detail_refresh_does_not_drop_concurrently_added_guides(self):
        first=guide('a');second=guide('b')
        self.client._merge([first,second])
        with patch.object(self.client,'detail',return_value=first):
            result=self.client.enrich([first],['a'])
        self.assertEqual({'a','b'},{g['id'] for g in result})

    def test_latest_expiry_flag_is_preserved_with_rich_description(self):
        rich=guide('a')
        self.client._merge([rich])
        self.client._merge([{'id':'a','description':'','tourn_detail':{'is_sub_expired':True}}])
        cached=self.client.cached_guides()[0]
        self.assertTrue(cached['tourn_detail']['is_sub_expired'])
        self.assertEqual(rich['description'],cached['description'])

    def test_title_hints_use_config_names_not_similar_substrings_in_code(self):
        config={'trait_info_list':[{'trait_id':'a','trait_name':'贝洛伯格'}, {'trait_id':'b','trait_name':'量子同频'}]}
        self.assertEqual(['a','b'],trait_hints('【4贝洛伯格4量子同频】示例\n##Q09ERQ==##',config))
        self.assertEqual([],trait_hints('Q09ERQ==',config))

    def test_title_filtered_lookup_also_reads_past_three_pages(self):
        wanted=guide('Hot6','Q09ERQ==')
        with patch.object(self.client,'cached_config',return_value={'trait_info_list':[{'trait_id':'a','trait_name':'示例羁绊'}]}), patch.object(self.client,'list_page',side_effect=self.pages) as request, patch.object(self.client,'detail',return_value=wanted):
            # Return the desired code only on filtered page six.
            def filtered(order='Hot',page=1,token='',**filters):
                result=self.pages(order,page,token,**filters)
                if page==6:result['list']=[wanted]
                self.assertEqual(['a'],filters.get('trait_ids'))
                return result
            request.side_effect=filtered
            self.assertEqual(wanted,self.client.resolve_code('示例羁绊攻略 ##Q09ERQ==##'))
        self.assertEqual(6,request.call_count)
        self.assertNotEqual('complete',self.client.coverage['state'])

    def test_lookup_finds_code_while_shared_full_sync_is_still_running(self):
        reached=threading.Event();release=threading.Event()
        wanted=guide('Hot4')
        def progress(summary):
            if summary['coverage']['orders']['Hot']['page']==4:
                reached.set();release.wait(3)
        with patch.object(self.client,'list_page',side_effect=self.pages), patch.object(self.client,'detail',return_value=wanted):
            thread=threading.Thread(target=lambda:self.client.refresh(progress=progress))
            thread.start()
            try:
                self.assertTrue(reached.wait(3))
                found=self.client.resolve_code(wanted['tourn_detail']['share_code'])
                self.assertEqual(wanted,found)
                self.assertTrue(thread.is_alive())
            finally:
                release.set();thread.join(3)
        self.assertFalse(thread.is_alive())

    def test_cancel_before_first_page_does_not_fetch_or_claim_complete(self):
        with patch.object(self.client,'list_page') as request:
            self.client.refresh(cancel=lambda:True)
        request.assert_not_called()
        self.assertEqual('interrupted',self.client.coverage['state'])


class LookupCancellationTests(unittest.TestCase):
    def test_no_code_guide_locks_by_id_offline_and_invalid_guide_does_not(self):
        c=object.__new__(Controller);c._mutex=threading.RLock();c._lookup_generation=0
        c.catalog=SimpleNamespace(version='fixture');c.tracker=SimpleNamespace(state=object())
        c.adviser=Mock();c.client=Mock();c.guides=[];c.emit=Mock();c.recalculate=Mock()
        c.apply_guide_code=Mock();candidate={'id':'offline','title':'Synthetic','tourn_detail':{}}
        self.assertTrue(c.lock_guide(candidate));self.assertEqual('offline',c.locked)
        c.client.detail.assert_not_called();c.apply_guide_code.assert_not_called()
        c.adviser.match.return_value=None
        self.assertFalse(c.lock_guide({'id':'invalid'}));self.assertEqual('offline',c.locked)
        c.lock_guide(guide('with-code','Q09ERQ=='))
        c.apply_guide_code.assert_called_once_with('Q09ERQ==')

    def test_missing_current_details_are_deduplicated_without_list_crawl(self):
        controller=object.__new__(Controller)
        controller._mutex=threading.RLock();controller._enrich_busy=set();controller._enrich_at={}
        controller.closing=False;controller.matches=[SimpleNamespace(guide={'id':'a'})]
        controller.guides=[];controller.client=Mock();controller.emit=Mock();controller.recalculate=Mock()
        entered=threading.Event();release=threading.Event();done=threading.Event()
        def enrich(*args):entered.set();release.wait(3);return []
        controller.client.enrich.side_effect=enrich
        controller.recalculate.side_effect=lambda:done.set()
        controller.enrich_current();self.assertTrue(entered.wait(3))
        controller.enrich_current();release.set();self.assertTrue(done.wait(3))
        controller.enrich_current()
        self.assertEqual(1,controller.client.enrich.call_count)
        controller.client.list_page.assert_not_called()
        controller.client.refresh.assert_not_called()

    def test_unlock_prevents_old_lookup_from_relocking_new_game(self):
        controller=object.__new__(Controller)
        controller._mutex=threading.RLock();controller._lookup_generation=0
        controller.closing=False;controller.lookup={'state':'idle'}
        controller.catalog=SimpleNamespace(roles={'role':{}},version='fixture')
        controller.tracker=SimpleNamespace(state=object())
        controller.adviser=Mock();controller.client=Mock()
        controller.locked='';controller.locked_code='';controller.locked_title=''
        controller.recalculate=Mock();controller.emit=Mock()
        entered=threading.Event();release=threading.Event();finished=threading.Event()
        def resolve(*args,**kwargs):
            entered.set();release.wait(3)
            return guide('old')
        controller.client.resolve_code.side_effect=resolve
        controller.emit.side_effect=lambda kind,value:finished.set() if kind=='network' else None
        controller.apply_guide_code('Q09ERQ==')
        self.assertTrue(entered.wait(3))
        controller.clear_guide_lock();release.set()
        self.assertTrue(finished.wait(3))
        self.assertEqual('',controller.locked)
        self.assertEqual('idle',controller.lookup['state'])


if __name__=='__main__':unittest.main()
