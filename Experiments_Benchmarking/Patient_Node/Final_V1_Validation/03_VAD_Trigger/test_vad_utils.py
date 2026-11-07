"""Tests logic biên khớp với hợp đồng VAD, không phải thực nghiệm trên WAV."""
import unittest
import numpy as np
from vad_utils import VadConfig, pcm16_chunk_mav, simulate


class VadTests(unittest.TestCase):
    def test_mav_int16_boundary_and_strict_comparison(self):
        x=np.r_[np.full(256,75,np.int16),np.full(256,-32768,np.int16)]
        mav,lengths=pcm16_chunk_mav(x)
        self.assertEqual(mav.tolist(),[75,32768]);self.assertEqual(lengths.tolist(),[256,256])
        self.assertEqual(len(simulate([75]*5,[256]*5,VadConfig(threshold=75,consecutive=4),playback_prearmed=True)),0)

    def test_warmup_plus_ring_requirement(self):
        # 100 warmup chunks, 63 chunks to fill 16000 samples, then consecutive=4
        n=180; m=np.full(n,100,dtype=np.uint32);lengths=np.full(n,256)
        events=simulate(m,lengths,VadConfig(),max_triggers=1)
        self.assertEqual(len(events),1)
        self.assertAlmostEqual(events[0]['candidate_onset_s'],162*256/16000,places=6)
        self.assertEqual(events[0]['recovered_samples'],1024)
        self.assertAlmostEqual(events[0]['confirmation_delay_ms'],64,places=6)
        self.assertFalse(events[0]['capture_complete'])

    def test_playback_prearmed_without_poweron_warmup(self):
        m=np.full(100,dtype=np.uint32,fill_value=90)
        l=np.full(100,256,dtype=np.int32)
        ev=simulate(m,l,VadConfig(),playback_prearmed=True)
        self.assertEqual(len(ev),1)
        self.assertAlmostEqual(ev[0]['candidate_onset_s'],62*256/16000,places=6)

    def test_consecutive_reset(self):
        m=np.zeros(70,dtype=np.uint32);m[62:64]=100;m[64]=0;m[65:67]=100
        l=np.full(len(m),256)
        ev=simulate(m,l,VadConfig(),playback_prearmed=True)
        self.assertEqual(ev,[])

    def test_capture_blackout_rearm(self):
        n=1250;m=np.full(n,200,dtype=np.uint32);l=np.full(n,256)
        ev=simulate(m,l,VadConfig(),playback_prearmed=True,max_triggers=3)
        self.assertEqual(len(ev),3)
        self.assertTrue(all(x['capture_complete'] for x in ev))
        self.assertTrue(ev[1]['candidate_onset_s']>ev[0]['capture_end_s']+0.9)
        self.assertTrue(ev[2]['candidate_onset_s']>ev[1]['capture_end_s']+0.9)

    def test_last_partial_chunk_integer_division(self):
        x=np.r_[np.zeros(256,dtype=np.int16),np.array([1,2,3],dtype=np.int16)]
        mav,lengths=pcm16_chunk_mav(x)
        self.assertEqual(mav.tolist(),[0,2]);self.assertEqual(lengths.tolist(),[256,3])

if __name__=='__main__':unittest.main()
