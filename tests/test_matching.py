from copy import deepcopy
from pathlib import Path
import unittest,uuid
from unittest.mock import Mock
import cv2,numpy as np

from currency_war_assistant.models import Catalog,GameState,Seen
from currency_war_assistant.strategy import Adviser,environment_bonds
from currency_war_assistant.portraits import PortraitBank,sync_portraits


def catalog():
    return Catalog({'rpg_game_big_version':'fixture','role_list':[
        {'id':'night','name':'夜系核心','rarity':3,'trait_details':[{'id':'n','name':'夜系'}]},
        {'id':'night2','name':'夜系辅助','rarity':1,'trait_details':[{'id':'n','name':'夜系'}]},
        {'id':'other','name':'其他核心','rarity':3,'trait_details':[{'id':'o','name':'其他'}]},
        {'id':'shared','name':'通用辅助','rarity':1,'trait_details':[]}],
        'portal_list':[{'id':'night-env','title':'夜系环境','desc':'开局获得【夜系】角色，【夜系】角色的刷新概率提高。'},
                       {'id':'other-env','title':'其他环境','desc':'获得1金币。'}]})


def guide(identifier,roles,envs=(),description=''):
    units=[{'id':i,'is_carry':index==0} for index,i in enumerate(roles)]
    return {'id':identifier,'title':identifier,'description':description,'tourn_detail':{
        'rpg_game_big_version':'fixture','portals':[{'id':i} for i in envs],
        'role_stages':[{'stage':s,'front_roles':deepcopy(units),'back_roles':[]} for s in ('Early','Final')]}}


class EnvironmentRankingTests(unittest.TestCase):
    def setUp(self):
        self.catalog=catalog();self.adviser=Adviser(self.catalog)
        self.state=GameState(scene='准备',gold=4,level=3,
                             environment=Seen('night-env','夜系环境','环境','已选',confidence=1))

    def test_unknown_owned_roles_keep_environment_order_despite_same_ten_point_cap(self):
        unrelated=guide('unrelated',['other','shared'])
        relevant=guide('relevant',['night','shared'],['night-env'])
        result=self.adviser.rank([unrelated,relevant],self.state)
        self.assertEqual('relevant',result[0].guide['id'])
        self.assertTrue(all(m.provisional for m in result))
        self.assertTrue(all(m.score<=10 for m in result))
        self.assertIn('已选环境匹配作者推荐',str(result[0].reasons))
        self.assertEqual(set(),self.state.owned_ids())

    def test_owned_and_environment_matched_guide_beats_shop_only_match(self):
        self.state.roles=[Seen('night','夜系核心','角色','备战',confidence=1)]
        self.state.shop=[Seen('other','其他核心','角色','商店',confidence=1)]
        result=self.adviser.rank([guide('shop',['other']),guide('owned',['night'])],self.state)
        self.assertEqual('owned',result[0].guide['id']);self.assertFalse(result[0].provisional)
        self.assertTrue(result[1].provisional)
        self.assertIn('夜系核心',str(result[0].reasons))

    def test_one_incidental_benefiting_support_is_reference_not_environment_recommendation(self):
        self.state.roles=[Seen('other','其他核心','角色','备战',confidence=1)]
        match=self.adviser.match(guide('incidental',['other','night2']),self.state)
        self.assertEqual(1,match.environment_fit);self.assertTrue(match.provisional)

    def test_optional_author_environment_list_is_not_an_explicit_requirement(self):
        self.state.roles=[Seen('night','夜系核心','角色','备战',confidence=1)]
        optional=self.adviser.match(guide('optional',['night'],['other-env']),self.state)
        required=self.adviser.match(guide('required',['night'],['other-env'],'必须选择其他环境。'),self.state)
        self.assertFalse(optional.blocked);self.assertTrue(required.blocked)
        self.assertIn('不在作者推荐列表',str(optional.cautions))

    def test_offered_environment_has_no_confirmed_match_and_locked_guide_remains_explicit(self):
        self.state.environment.zone='待选'
        self.assertEqual(set(),environment_bonds(self.catalog,self.state))
        self.assertEqual(0,self.adviser.match(guide('a',['night'],['night-env']),self.state).environment_fit)
        a,b=guide('a',['other']),guide('b',['night'])
        self.assertEqual('a',self.adviser.rank([a,b],self.state,locked_id='a')[0].guide['id'])

    def test_provisional_candidate_cannot_drive_purchase_advice(self):
        self.state.roles=[Seen('other','其他核心','角色','备战',confidence=1)]
        self.state.shop=[Seen('night','夜系核心','角色','商店',confidence=1)]
        match=self.adviser.match(guide('incompatible',['night']),self.state)
        advice=self.adviser.advice(self.state,match)
        self.assertNotIn('买人',dict(advice))


class PortraitTests(unittest.TestCase):
    def setUp(self):
        self.data=Path(__file__).parent/'_cache'/('portraits-'+uuid.uuid4().hex)
        self.data.mkdir(parents=True)
        self.image=np.random.default_rng(8).integers(0,256,(112,96,4),dtype=np.uint8)
        self.image[:,:,3]=255
        self.content=cv2.imencode('.png',self.image)[1].tobytes()
        self.catalog=Catalog({'role_list':[{'id':'a','name':'A','icon':'https://act-webstatic.mihoyo.com/a.png'}]})

    def test_local_cache_is_reused_and_nonofficial_urls_are_not_fetched(self):
        fetch=Mock(return_value=self.content)
        self.assertEqual(1,sync_portraits(self.data,self.catalog,fetch))
        self.assertEqual(1,sync_portraits(self.data,self.catalog,fetch));fetch.assert_called_once()
        bad=Catalog({'role_list':[{'id':'b','icon':'https://example.com/b.png'}]})
        self.assertEqual(0,sync_portraits(self.data,bad,fetch));fetch.assert_called_once()

    def test_duplicate_owned_cards_are_retained_and_empty_slots_have_no_match(self):
        sync_portraits(self.data,self.catalog,lambda url:self.content)
        bank=PortraitBank(self.data);image=np.zeros((1080,1920,3),dtype=np.uint8)
        for slot in (0,2):
            x=round(.195*1920+slot*(.79-.195)*1920/9)+15
            image[853:965,x:x+96]=self.image[:,:,:3]
        found=bank.bench(image,(.195,.78,.79,.91),{'a'})
        self.assertEqual([0,2],[r['slot'] for r in found]);self.assertTrue(all(r['ids']==['a'] for r in found))
        self.assertEqual([],bank.bench(image,(.195,.78,.79,.91),{'not-present'}))

    def test_identical_portraits_remain_ambiguous_between_character_forms(self):
        self.catalog.roles['b']={'id':'b','name':'B','icon':'https://act-webstatic.mihoyo.com/b.png'}
        sync_portraits(self.data,self.catalog,lambda url:self.content)
        bank=PortraitBank(self.data)
        self.assertEqual(1,len(bank.references));self.assertEqual({'a','b'},set(bank.references[0]['ids']))


if __name__=='__main__':unittest.main()
