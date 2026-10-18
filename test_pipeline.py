"""Behavioral controls for the errors most likely to corrupt the data gate."""
import copy
import unittest
from pipeline import Excluded, classify_delivery, parse_match, phase_for, losses, predictions, aggregate

def ball(batter=0,extras=None,non_boundary=None):
    extras=extras or {}
    d={'bowler':'Bowler A','runs':{'batter':batter,'extras':sum(extras.values()),'total':batter+sum(extras.values())}}
    if extras:d['extras']=extras
    if non_boundary is not None:d['runs']['non_boundary']=non_boundary
    return d

def match(legal=120,dismissals=0,target_overs=20):
    deliveries=[ball() for _ in range(legal)]
    for d in deliveries[-dismissals:] if dismissals else []:
        d['wickets']=[{'kind':'bowled','player_out':'Batter'}]
    overs=[{'over':i//6,'deliveries':deliveries[i:i+6]} for i in range(0,legal,6)]
    return {'meta':{'data_version':'1.2.0'},'info':{'gender':'male','match_type':'T20','event':{'name':'Indian Premier League'},
        'balls_per_over':6,'overs':20,'season':'2023','dates':['2023-04-01'],'teams':['Team A','Team B'],
        'registry':{'people':{'Bowler A':'id-a'}},'outcome':{'winner':'Team A'}},
        'innings':[{'team':'Team B','overs':overs},{'team':'Team A','target':{'overs':target_overs,'runs':1},'overs':[]}]}

class GateTests(unittest.TestCase):
    def test_legal_categories_and_non_boundary(self):
        self.assertEqual([classify_delivery(ball()),classify_delivery(ball(4)),classify_delivery(ball(6)),
            classify_delivery(ball(4,non_boundary=True)),classify_delivery(ball(extras={'byes':1}))],[0,1,1,2,2])
    def test_wides_noballs_not_in_legal_denominator(self):
        self.assertIsNone(classify_delivery(ball(extras={'wides':1})))
        self.assertIsNone(classify_delivery(ball(4,{'noballs':1})))
    def test_missing_and_inconsistent_runs_rejected(self):
        d=ball();del d['runs']['batter']
        with self.assertRaises(Excluded):classify_delivery(d)
        d=ball();d['runs']['total']=1
        with self.assertRaises(Excluded):classify_delivery(d)
    def test_phase_boundaries(self):
        self.assertEqual([phase_for(x) for x in (0,5,6,14,15,19)],['1-6','1-6','7-15','7-15','16-20','16-20'])
        with self.assertRaises(Excluded):phase_for(20)
    def test_all_out_kept_and_unfinished_rejected(self):
        rows,summary=parse_match(match(93,10),'all-out')
        self.assertEqual(sum(sum(r['counts']) for r in rows),93)
        self.assertTrue(summary['all_out_early'])
        with self.assertRaisesRegex(Excluded,'incomplete'):parse_match(match(93,9),'unfinished')
    def test_reduced_target_rejected_even_without_dl(self):
        with self.assertRaisesRegex(Excluded,'reduced_chase_target'):parse_match(match(84,9,14),'reduced')
    def test_retired_hurt_is_not_tenth_dismissal(self):
        d=match(93,10);d['innings'][0]['overs'][-1]['deliveries'][-1]['wickets'][0]['kind']='retired hurt'
        with self.assertRaisesRegex(Excluded,'incomplete'):parse_match(d,'retired')
    def test_complete_first_no_result_kept(self):
        d=match();d['info']['outcome']={'result':'no result'}
        _,summary=parse_match(d,'complete')
        self.assertTrue(summary['completed_first_no_result'])
    def test_missing_identity_and_miscounted_overs_rejected(self):
        d=match();d['info']['registry']['people']={}
        with self.assertRaisesRegex(Excluded,'registry'):parse_match(d,'identity')
        d=match();d['innings'][0]['miscounted_overs']={'5':{'balls':5}}
        with self.assertRaisesRegex(Excluded,'miscounted'):parse_match(d,'miscount')
    def test_unrelated_missing_fields_do_not_exclude(self):
        d=match();d['info']['missing']=['umpires',{'powerplays':{'1':['mandatory']}}]
        self.assertEqual(parse_match(d,'optional')[1]['legal'],120)
    def test_target_reconciles_runs(self):
        d=match();d['innings'][0]['overs'][0]['deliveries'][0]=ball(4)
        with self.assertRaisesRegex(Excluded,'target_mismatch'):parse_match(d,'bad-total')
        d['innings'][1]['target']['runs']=5
        self.assertEqual(parse_match(d,'fixed-total')[1]['team_total'],4)
    def test_aggregated_brier_equals_explicit_outcomes(self):
        p=[.2,.3,.5];counts=[2,1,3]
        direct=sum(sum((p[k]-int(k==y))**2 for k in range(3)) for y in [0,0,1,2,2,2])
        self.assertAlmostEqual(losses(counts,p)[0],direct)
    def test_shrinkage_and_unseen_normalization(self):
        rows=[{'player_id':'a','phase':'1-6','counts':[2,0,0]},{'player_id':'b','phase':'1-6','counts':[0,2,2]}]
        model=aggregate(rows)
        p=predictions(model,'a','1-6','C',2)
        self.assertEqual(p,[.5,.25,.25])
        self.assertAlmostEqual(sum(predictions(model,'new','1-6','C',2)),1)
        self.assertEqual(predictions(model,'new','1-6','C',2),predictions(model,'a','1-6','B0'))

if __name__=='__main__':unittest.main()
