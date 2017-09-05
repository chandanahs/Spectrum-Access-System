#    Copyright 2017 SAS Project Authors. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
import logging
import numpy as np
import unittest

from reference_models.geo import testutils
from reference_models.geo import terrain
from reference_models.geo import tropoclim
from reference_models.geo import refractivity

from reference_models.propagation import wf_hybrid

TERRAIN_TEST_DIR = os.path.join(os.path.dirname(__file__),
                                '..', 'geo', 'testdata', 'ned')
ITU_TEST_DIR = os.path.join(os.path.dirname(__file__),
                            '..', 'geo', 'testdata', 'itu')

logging.disable(30)
class TestWfHybrid(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.unzip_files = testutils.UnzipTestDir(TERRAIN_TEST_DIR)

  @classmethod
  def tearDownClass(cls):
    testutils.RemoveFiles(TERRAIN_TEST_DIR, cls.unzip_files)

  def setUp(self):
    # Reconfigure the drivers to point to geo/testdata directories
    wf_hybrid.ConfigureTerrainDriver(terrain_dir=TERRAIN_TEST_DIR)
    wf_hybrid.wf_itm.ConfigureItuDrivers(itu_dir=ITU_TEST_DIR)

  def test_100m_mode(self):
    lat1, lng1, height1 = 37.756672, -122.508512, 10.0
    lat2, lng2, height2 = 37.756559, -122.507882, 10.0 # about 50m away
    reliability = 0.5
    res = wf_hybrid.CalcHybridPropagationLoss(
        lat1, lng1, height1, lat2, lng2, height2,
        reliability=reliability, freq_mhz=3625.,
        region='SUBURBAN')
    self.assertAlmostEqual(res.db_loss, 79.167, 3)
    self.assertEqual(res.internals['hybrid_opcode'], wf_hybrid.HybridMode.FSL)

  def test_high_height_mode(self):
    lat1, lng1, height1 = 37.756672, -122.508512, 201.0
    lat2, lng2, height2 = 37.756559, -122.507882, 10.0 # about 50m away
    reliability = 0.5
    res = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                reliability=reliability, freq_mhz=3625.,
                                region='SUBURBAN')
    self.assertEqual(res.db_loss, res.internals['itm_db_loss'])
    self.assertEqual(res.internals['hybrid_opcode'],
                     wf_hybrid.HybridMode.ITM_HIGH_HEIGHT)

  def test_rural_mode(self):
    lat1, lng1, height1 = 37.756672, -122.508512, 50.0
    lat2, lng2, height2 = 37.756559, -122.507882, 10.0 # about 50m away
    reliability = 0.5
    res = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                reliability=reliability, freq_mhz=3625.,
                                region='RURAL')
    self.assertEqual(res.db_loss, res.internals['itm_db_loss'])
    self.assertEqual(res.internals['hybrid_opcode'], wf_hybrid.HybridMode.ITM_RURAL)

  def test_1km_mode(self):
    lat1, lng1, height1 = 37.756672, -122.508512, 20.0
    lat2, lng2, height2 = 37.762314, -122.500973, 10.0  # 912 meters away
    reliability = 0.5
    res = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                reliability=reliability, freq_mhz=3625.,
                                region='URBAN')
    self.assertAlmostEqual(res.db_loss, 143.454, 3)
    self.assertEqual(res.internals['hybrid_opcode'], wf_hybrid.HybridMode.EHATA_FSL_INTERP)

  def test_itm_dominant(self):
    lat1, lng1, height1 = 37.756672, -122.508512, 20.0
    lat2, lng2, height2 = 37.754406, -122.388342, 10.0
    reliabilities = [0.1, 0.5, 0.9]
    expected_itm_losses = [210.79, 211.51, 211.95]

    for rel, exp_loss in zip(reliabilities, expected_itm_losses):
      res = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                  reliability=rel, freq_mhz=3625.,
                                  region='SUBURBAN', climate=5, refractivity=314)
      self.assertAlmostEqual(res.db_loss, exp_loss, 2)
      self.assertEqual(res.db_loss, res.internals['itm_db_loss'])  # ploss == ploss_itm
      self.assertEqual(res.internals['hybrid_opcode'],
                       wf_hybrid.HybridMode.ITM_DOMINANT)
      self.assertEqual(res.internals['itm_err_num'],
                       wf_hybrid.wf_itm.ItmErrorCode.WARNING)

  def test_ehata_dominant(self):
    lat1, lng1, height1 = 37.751985, -122.443890, 20.0
    lat2, lng2, height2 = 37.771594, -122.253895, 10.0
    reliabilities = [0.1, 0.5, 0.9]
    expected_losses = [148.740, 148.740, 148.740]

    for rel, exp_loss in zip(reliabilities, expected_losses):
      res = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                  reliability=rel, freq_mhz=3625.,
                                  region='SUBURBAN', climate=5, refractivity=314)
      self.assertAlmostEqual(res.db_loss, exp_loss, 2)
      self.assertEqual(res.internals['hybrid_opcode'], wf_hybrid.HybridMode.EHATA_DOMINANT)

  def test_ehata_mean(self):
    lat1, lng1, height1 = 37.751985, -122.443890, 20.0
    lat2, lng2, height2 = 37.771594, -122.253895, 10.0
    expected_med_loss = 161.93
    expected_offset = 2.3462
    self.assertAlmostEqual(wf_hybrid._GetMedianToMeanOffsetDb(3625., False),
                           expected_offset, 2)

    res_med = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                    reliability=0.5, freq_mhz=3625.,
                                    region='SUBURBAN', climate=5, refractivity=314)
    res_mean = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                     reliability=-1, freq_mhz=3625.,
                                     region='SUBURBAN', climate=5, refractivity=314)
    self.assertAlmostEqual(res_mean[0], res_med[0] + expected_offset, 2)

  def test_over_80km(self):
    lat1, lng1, height1 = 37.751985, -122.443890, 20.0
    lat2, lng2, height2 = 37.094745, -122.040671, 10.0  # 81km away
    expected_loss = 269.067

    res = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                reliability=0.5, freq_mhz=3625.,
                                region='SUBURBAN', climate=5, refractivity=314)
    self.assertAlmostEqual(res.db_loss, expected_loss, 3)
    self.assertAlmostEqual(res.db_loss, res.internals['itm_db_loss'], 0)
    self.assertEqual(res.internals['hybrid_opcode'], wf_hybrid.HybridMode.ITM_CORRECTED)

  def test_average(self):
    lat1, lng1, height1 = 37.756672, -122.508512, 20.0
    lat2, lng2, height2 = 37.754406, -122.388342, 10.0
    reliabilities = np.arange(0.01, 1.0, 0.01)
    losses = []
    for rel in reliabilities:
      res = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                  reliability=rel, freq_mhz=3625.,
                                  region='SUBURBAN')
      losses.append(res.db_loss)

    avg_res = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                    reliability=-1, freq_mhz=3625.,
                                    region='SUBURBAN')
    self.assertAlmostEqual(avg_res.db_loss, np.mean(losses), 5)

  def test_indoor(self):
    lat1, lng1, height1 = 37.756672, -122.508512, 20.0
    lat2, lng2, height2 = 37.754406, -122.388342, 10.0
    res_outdoor = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                                   cbsd_indoor=False,
                                                   reliability=0.5, freq_mhz=3625.,
                                                   region='SUBURBAN')
    res_indoor = wf_hybrid.CalcHybridPropagationLoss(lat1, lng1, height1, lat2, lng2, height2,
                                                     cbsd_indoor=True,
                                                     reliability=0.5, freq_mhz=3625.,
                                                     region='SUBURBAN')
    self.assertEqual(res_indoor.db_loss, res_outdoor.db_loss + 15)


if __name__ == '__main__':
  unittest.main()