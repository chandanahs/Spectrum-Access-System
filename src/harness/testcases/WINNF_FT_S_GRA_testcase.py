#    Copyright 2016 SAS Project Authors. All Rights Reserved.
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

# Some parts of this software was developed by employees of
# the National Institute of Standards and Technology (NIST),
# an agency of the Federal Government.
# Pursuant to title 17 United States Code Section 105, works of NIST employees
# are not subject to copyright protection in the United States and are
# considered to be in the public domain. Permission to freely use, copy,
# modify, and distribute this software and its documentation without fee
# is hereby granted, provided that this notice and disclaimer of warranty
# appears in all copies.

# THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND, EITHER
# EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, ANY WARRANTY
# THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND FREEDOM FROM
# INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION WILL CONFORM TO THE
# SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE ERROR FREE. IN NO EVENT
# SHALL NIST BE LIABLE FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT,
# INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM,
# OR IN ANY WAY CONNECTED WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON
# WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED
# BY PERSONS OR PROPERTY OR OTHERWISE, AND WHETHER OR NOT LOSS WAS SUSTAINED
# FROM, OR AROSE OUT OF THE RESULTS OF, OR USE OF, THE SOFTWARE OR SERVICES
# PROVIDED HEREUNDER.

# Distributions of NIST software should also include copyright and licensing
# statements of any third-party software that are legally bundled with the
# code in compliance with the conditions of those licenses.

import json
import os
import sas
import sas_testcase
from util import winnforum_testcase, getRandomLatLongInPolygon, \
  makePpaAndPalRecordsConsistent


class GrantTestcase(sas_testcase.SasTestCase):

  def setUp(self):
    self._sas, self._sas_admin = sas.GetTestingSas()
    self._sas_admin.Reset()

  def tearDown(self):
    pass

  @winnforum_testcase
  def test_WINNF_FT_S_GRA_7(self):
    """Invalid operationFrequencyRange.

    The response should be:
    - 103 (INVALID_VALUE) for first request.
    - 103 or 300 (UNSUPPORTED_SPECTRUM) for second and third requests.
    """
    # Register three devices
    device_a = json.load(
        open(os.path.join('testcases', 'testdata', 'device_a.json')))
    device_c = json.load(
        open(os.path.join('testcases', 'testdata', 'device_c.json')))
    device_e = json.load(
        open(os.path.join('testcases', 'testdata', 'device_e.json')))

    self._sas_admin.InjectFccId({'fccId': device_a['fccId']})
    self._sas_admin.InjectFccId({'fccId': device_c['fccId']})
    self._sas_admin.InjectFccId({'fccId': device_e['fccId']})

    self._sas_admin.InjectUserId({'userId': device_a['userId']})
    self._sas_admin.InjectUserId({'userId': device_c['userId']})
    self._sas_admin.InjectUserId({'userId': device_e['userId']})

    devices = [device_a, device_c, device_e]
    request = {'registrationRequest': devices}
    response = self._sas.Registration(request)

    # Check registration response
    cbsd_ids = []
    for resp in response['registrationResponse']:
      self.assertEqual(resp['response']['responseCode'], 0)
      cbsd_ids.append(resp['cbsdId'])
    del request, response

    # Prepare 3 grant requests.
    # 1. With lowFrequency > highFrequency.
    grant_0 = json.load(
        open(os.path.join('testcases', 'testdata', 'grant_0.json')))
    grant_0['cbsdId'] = cbsd_ids[0]
    grant_0['operationParam']['operationFrequencyRange'] = {
        'lowFrequency': 3650000000.0,
        'highFrequency': 3550000000.0
    }

    # 2. With frequency range completely outside the CBRS band.
    grant_1 = json.load(
        open(os.path.join('testcases', 'testdata', 'grant_0.json')))
    grant_1['cbsdId'] = cbsd_ids[1]
    grant_1['operationParam']['operationFrequencyRange'][
        'lowFrequency'] = 3350000000.0
    grant_1['operationParam']['operationFrequencyRange'][
        'highFrequency'] = 3450000000.0

    # 3. With frequency range partially overlapping with the CBRS band.
    grant_2 = json.load(
        open(os.path.join('testcases', 'testdata', 'grant_0.json')))
    grant_2['cbsdId'] = cbsd_ids[2]
    grant_2['operationParam']['operationFrequencyRange'][
        'lowFrequency'] = 3450000000.0
    grant_2['operationParam']['operationFrequencyRange'][
        'highFrequency'] = 3650000000.0

    request = {'grantRequest': [grant_0, grant_1, grant_2]}
    # Send grant request and get response
    response = self._sas.Grant(request)['grantResponse']

    # Check grant response array
    self.assertEqual(len(response), 3)
    for response_num, resp in enumerate(response):
      self.assertEqual(resp['cbsdId'], cbsd_ids[response_num])
      self.assertFalse('grantId' in resp)
    self.assertEqual(response[0]['response']['responseCode'], 103)
    self.assertTrue(response[1]['response']['responseCode'], 300)
    self.assertTrue(response[2]['response']['responseCode'], 300)

