#!/usr/bin/python
# Copyright 2019 Huawei Technologies Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script uses the ONAP CLI for providing the end-end service creation and termination.
# Used in devops, testing, certification and production
# NOTE: This feature is avaialble as ONAP CLI vnf-tosca-lcm
#
# Author: kanagaraj.manickam@huawei.com 
#

import json
import os
import argparse
import sys
import uuid
import subprocess
import platform
import datetime
import string
import random
import time

from argparse import RawTextHelpFormatter

############copied from spirent script##########
import logging
from onap_api import ONAP as ONAP_api
from simple_traffic import SimpleTrafficTest
from stc_demo_ns import STCDemoNS

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(hdlr=handler)
logger.setLevel(logging.DEBUG)
logger.propagate=True

#labserver_ip = "192.168.235.98"
################################################

if platform.system() == 'Windows':
    CMD_NAME = 'oclip.cmd'
else:
    CMD_NAME = 'oclip.sh'

class OcompException(Exception):
    def __init__(self, code, message):
        super(OcompException, self).__init__()
        self.code = code;
        self.message = message;

class OCOMP:
    def __init__(self,
                 request_id = os.environ.get('OPEN_CLI_REQUEST_ID'),
                 debug = False,
                 format = 'json',
                 product = os.environ.get('OPEN_CLI_PRODUCT_IN_USE'),
                 profile = os.environ.get('OPEN_CLI_PROFILE')):
        if not request_id:
                request_id = str(uuid.uuid4())
        self.request_id = request_id
        self.debug = debug
        self.format = format
        self.product = product
        self.profile = profile

    def __str__(self):
        return  str(vars(self))

    def __repr__(self):
        return  str(self)

    @staticmethod
    def version():
        return os.popen('{} --version'.format(CMD_NAME)).read()

    def run(self, command, params={}, product=None,  profile=None, request_id=None):
        CMD = [CMD_NAME]

        if not request_id:
                request_id = self.request_id

        if request_id:
            CMD.append('--request-id')
            CMD.append(request_id)

        if not product:
            product = self.product

        if product:
            CMD.append('--product')
            CMD.append(product)

        if not profile:
            profile = self.profile

        if profile:
            CMD.append('--profile')
            CMD.append(profile)

        CMD.append(command)

        if self.debug:
            CMD.append('--debug')

        CMD.append('--format')
        CMD.append(self.format)

        for name, value in params.items():
            CMD.append('--{}'.format(name))
            CMD.append(value)

        cmd_string = ' '.join(CMD)
        print (cmd_string)

        try:
            res = subprocess.Popen(CMD, stdout=subprocess.PIPE)
            res.wait()
            result = res.stdout.read().strip()
            print (res.returncode, result)

            if res.returncode != 0:# and res.returncode != 1:
                raise OcompException(9999, result)
            if result:
                return json.loads(result)
            else:
                return {}
        except OSError as e:
            sys.stderr.write(str(e))
            msg = 'failed to executed the command {}'.format(cmd_string)
            print (msg)
            raise OcompException(9999, msg)

class ONAP:
    def __init__(self,
                 product,
                 profile,
                 conf,
                 request_id,
                 debug = False):
        self.conf = conf or {}
        self.ocomp = OCOMP(request_id, debug, product=product, profile=profile)
        self.preload()
        self.tag = 'Powered by Open Command Platform - OCOMP'

    def preload(self):
        if self.conf['ONAP']:
            for attr in self.conf['ONAP']:
                setattr(self, attr, self.conf['ONAP'][attr])
        else:
            self.conf['ONAP'] = {}

    def setup_cloud_and_subscription(self):
        associate = False
        if not self.location_id and not self.location_version:
            location_id = 'ocomp-region-{}'.format(self.conf['ONAP']['uid'])
            logger.debug('----------complex-create----------')
            self.ocomp.run(command='complex-create',
                                    params={'physical-location-id': location_id,
                                            'data-center-code': 'ocomp',
                                            'complex-name': location_id,
                                            'identity-url': self.conf['cloud']['identity-url'],
                                            'physical-location-type': 'phy_type',
                                            'street1': 'ocomp-street1',
                                            'street2': 'ocomp-street2',
                                            'city': 'ocomp-city',
                                            'state': 'ocomp-state',
                                            'postal-code': '001481',
                                            'country': 'abc',
                                            'longitude': '1.0',
                                            'latitude': '1.0',
                                            'region': 'onap',
                                            'elevation': 'ocomp-elelation',
                                            'lata': 'ocomp-lata'})
            self.location_id = location_id
            associate = True

            output = self.ocomp.run(command='complex-list')

            for location in output:
                if location['complex-name'] == self.location_id:
                    self.location_version = location['resource-version']
                    break

        if not self.cloud_id and not self.cloud_version:
            cloud_id = 'OCOMP-{}'.format(self.conf['ONAP']['uid'])
            logger.debug('----------cloud-create----------')
            self.ocomp.run(command='cloud-create',
                                    params={'region-name': self.conf['cloud']['region'],
                                            'complex-name': self.location_id,
                                            'identity-url': self.conf['cloud']['identity-url'],
                                            'cloud-owner': cloud_id,
                                            'cloud-type': 'openstack',
                                            'owner-type': 'ocomp',
                                            'cloud-region-version': self.conf['cloud']['version'],
                                            'cloud-zone': 'az1',
                                            'esr-id': cloud_id,
                                            'service-url': self.conf['cloud']['identity-url'],
                                            'username': self.conf['cloud']['username'],
                                            'password': self.conf['cloud']['password'],
                                            'system-type': 'VIM',
                                            'ssl-insecure': 'true',
                                            'cloud-domain': 'Default',
                                            'default-tenant': self.conf['cloud']['tenant'],
                                            'system-status': "active"})
            self.cloud_id = cloud_id
            associate = True

            output = self.ocomp.run(command='cloud-list')

            for cloud in output:
                if cloud['cloud'] == self.cloud_id:
                    self.cloud_version = cloud['resource-version']
                    break

        if associate:
            logger.debug('----------complex-associate----------')
            self.ocomp.run(command='complex-associate',
                                    params={'complex-name': self.location_id,
                                            'cloud-region': self.conf['cloud']['region'],
                                            'cloud-owner': self.cloud_id})
        
        logger.debug('----------multicloud-register-cloud----------')
        self.ocomp.run(command='multicloud-register-cloud',
                       params={'cloud-region': self.conf['cloud']['region'], 'cloud-owner': self.cloud_id})

        subscribe = False
        if not self.service_type_id and not self.service_type_version:
            service_type_id = '{}-{}'.format(self.conf['subscription']['service-type'], self.conf['ONAP']['uid'])
            self.ocomp.run(command='service-type-create',
                                params={'service-type': service_type_id,
                                        'service-type-id': service_type_id})
            self.service_type_id = service_type_id
            subscribe = True

            output = self.ocomp.run(command='service-type-list')

            for st in output:
                if st['service-type'] == self.service_type_id:
                    self.service_type_version = st['resource-version']
                    break

        if not self.customer_id and not self.customer_version:
            customer_id = '{}-{}'.format(self.conf['subscription']['customer-name'], self.conf['ONAP']['random'])
            logger.debug('----------customer-create----------')
            self.ocomp.run(command='customer-create',
                                params={'customer-name': customer_id,
                                        'subscriber-name': customer_id})
            self.customer_id = customer_id
            subscribe = True

            output = self.ocomp.run(command='customer-list')

            for customer in output:
                if customer['name'] == self.customer_id:
                    self.customer_version = customer['resource-version']
                    break

        # if not self.tenant_id and not self.tenant_version:
        #     tenant_id = str(uuid.uuid4())
        #     self.ocomp.run(command='tenant-create',
        #                         params={'tenant-name': self.conf['cloud']['tenant'],
        #                                 'tenant-id': tenant_id,
        #                                 'cloud':self.cloud_id,
        #                                 'region': self.conf['cloud']['region']})
        #     self.tenant_id = tenant_id
        #     subscribe = True
        #
        logger.debug('----------tenant-list----------')
        output = self.ocomp.run(command='tenant-list', params={
            'cloud': self.cloud_id,
            'region': self.conf['cloud']['region']
        })

        for tenant in output:
            if tenant['tenant-name'] == self.conf['cloud']['tenant']:
                self.tenant_id = tenant['tenant-id']
                break

        if subscribe:
            logger.debug('----------subscription-create----------')
            self.ocomp.run(command='subscription-create',
                                    params={'customer-name': self.customer_id,
                                            'cloud-owner': self.cloud_id,
                                            'cloud-region': self.conf['cloud']['region'],
                                            'cloud-tenant-id': self.tenant_id,
                                            'service-type': self.service_type_id,
                                            'tenant-name': self.conf['cloud']['tenant']})

        if not self.subscription_version:
            output = self.ocomp.run(command='subscription-list', params={
                    'customer-name': self.customer_id
                    })

            for subscription in output:
                if subscription['service-type'] == self.service_type_id:
                    self.subscription_version = subscription['resource-version']
                    break

        if not self.esr_vnfm_id and not self.esr_vnfm_version:
            vnfmdriver = self.conf['ONAP']['vnfm-driver']

            esr_vnfm_id = str(uuid.uuid4())
            logger.debug('----------vnfm-create----------')
            self.ocomp.run(command='vnfm-create',
                                    params={'vim-id': self.cloud_id + "_" + self.conf['cloud']['region'],
                                            'vnfm-id': esr_vnfm_id,
                                            'name': 'OCOMP {}'.format(vnfmdriver),
                                            'type': vnfmdriver,
                                            'vendor': self.conf['vnf']['vendor-name'],
                                            'vnfm-version': self.conf['vnfm'][vnfmdriver]['version'],
                                            'url': self.conf['vnfm'][vnfmdriver]['url'],
                                            'username': self.conf['vnfm'][vnfmdriver]['username'],
                                            'password': self.conf['vnfm'][vnfmdriver]['password']})
            self.esr_vnfm_id = esr_vnfm_id

        output = self.ocomp.run(command='vnfm-list')

        for vnfm in output:
            if vnfm['vnfm-id'] == self.esr_vnfm_id:
                self.esr_vnfm_version = vnfm['resource-version']
                break

#         self.ocomp.run(command='multicloud-register-cloud',
#                                 params={'clouvnfm-driverd-region': self.conf['cloud']['region'],
#                                         'cloud-owner': self.cloud_id})

    def create_vnf(self):
        vnfs = self.conf["vnfs"]
        logger.debug('----------vfc-catalog-onboard-vnf----------')
        for vnf_key, vnf_values in vnfs.items():
            self.ocomp.run(command='vfc-catalog-onboard-vnf',
                           params={'vnf-csar-uuid': vnf_values.get("vnf_uuid")})
        time.sleep(60)
        logger.debug('----------vfc-catalog-onboard-ns----------')
        self.ocomp.run(command='vfc-catalog-onboard-ns',
                                params={'ns-csar-uuid': self.conf['ns']['ns_uuid']})

        '''
        output = self.ocomp.run(command='vfc-nslcm-create',
                                params={'ns-csar-uuid': self.conf['ns']['ns_uuid'],
                                        'ns-csar-name': '{} Service'.format(self.conf['vnf']['name']),
                                        'customer-name': self.customer_id,
                                        'service-type': self.service_type_id})

        self.ns_instance_id = output['ns-instance-id']

        vnfmdriver = self.conf['ONAP']['vnfm-driver']
        self.ocomp.run(command='vfc-nslcm-instantiate',
                                params={'ns-instance-id': self.ns_instance_id,
                                        'location': self.cloud_id,
                                        'sdn-controller-id': self.esr_vnfm_id})
        '''

    def vnf_status_check(self):
        self.vnf_status = 'active'
        self.ns_instance_status = 'active'

    def cleanup(self):
        if self.ns_instance_id:
            logger.debug('----------vfc-nslcm-terminate----------')
            self.ocomp.run(command='vfc-nslcm-terminate',
                              params={'ns-instance-id': self.ns_instance_id})
            logger.debug('----------vfc-nslcm-delete----------')
            self.ocomp.run(command='vfc-nslcm-delete',
                              params={'ns-instance-id': self.ns_instance_id})
            self.ns_instance_id = None

        if self.subscription_version and self.customer_id and self.service_type_id:
            logger.debug('----------subscription-delete----------')
            self.ocomp.run(command='subscription-delete',
                              params={'customer-name': self.customer_id,
                                      'service-type': self.service_type_id,
                                      'resource-version': self.subscription_version})
            self.subscription_version = None

        if self.customer_id and self.customer_version:
            logger.debug('----------customer-delete----------')
            self.ocomp.run(command='customer-delete',
                              params={'customer-id': self.customer_id,
                                      'resource-version': self.customer_version})
            self.customer_id = self.customer_version = None

        if self.service_type_id and self.service_type_version:
            output = self.ocomp.run(command='service-type-list')

            for st in output:
                if st['service-type-id'] == self.service_type_id:
                    self.service_type_version = st['resource-version']
                    break
            logger.debug('----------service-type-delete----------')
            self.ocomp.run(command='service-type-delete',
                              params={'service-type-id': self.service_type_id,
                                      'resource-version': self.service_type_version})
            self.service_type_id = self.service_type_version = None

        # if self.tenant_id and self.tenant_version:
        #     self.ocomp.run(command='tenant-delete',
        #                       params={'cloud': self.cloud_id,
        #                               'region': self.conf['cloud']['region'],
        #                               'tenant-id': self.tenant_id,
        #                               'resource-version': self.tenant_version})
        #     self.tenant_id = self.tenant_version = None

        # if self.cloud_id and self.location_id:
        #     self.ocomp.run(command='complex-disassociate',
        #                       params={'cloud-owner': self.cloud_id,
        #                               'cloud-region': self.conf['cloud']['region'],
        #                               'complex-name': self.location_id})

        # if self.cloud_id and self.cloud_version:
        #     output = self.ocomp.run(command='cloud-list')
        #
        #     for c in output:
        #         if c['cloud'] == self.cloud_id and c['region'] == self.conf['cloud']['region']:
        #             self.cloud_version = c['resource-version']
        #             break
        #
        #     self.ocomp.run(command='cloud-delete',
        #                       params={'cloud-name': self.cloud_id,
        #                               'region-name': self.conf['cloud']['region'],
        #                               'resource-version': self.cloud_version})
        #     self.cloud_id = self.cloud_version = None

        if self.cloud_id:
            logger.debug('----------multicloud-cloud-delete----------')
            self.ocomp.run(command='multicloud-cloud-delete',
                              params={'cloud-owner': self.cloud_id,
                                      'cloud-region': self.conf['cloud']['region']})
            self.cloud_id = self.cloud_version = None

        time.sleep(30)
        if self.location_id and self.location_version:
            logger.debug('----------complex-delete----------')
            self.ocomp.run(command='complex-delete',
                              params={'complex-name': self.location_id,
                                      'resource-version': self.location_version})
            self.location_id = self.location_version = None

        if self.esr_vnfm_id and self.esr_vnfm_version:
            logger.debug('----------vnfm-delete----------')
            self.ocomp.run(command='vnfm-delete',
                              params={'vnfm-id': self.esr_vnfm_id,
                                      'resource-version': self.esr_vnfm_version})
            self.esr_vnfm_id = self.esr_vnfm_version = None

    def __str__(self):
        return  str(vars(self))

#Main
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ONAP TOSCA VNF validation using ONAP CLI and Open Command Platform (OCOMP)", formatter_class=RawTextHelpFormatter)
    parser.add_argument('--product', action='store', dest='product', help='OCOMP product to use, default to onap-dublin',
                        default=os.environ.get('OPEN_CLI_PRODUCT_IN_USE'))
    parser.add_argument('--profile', action='store', dest='profile', help='OCOMP profile to use, default to onap-dublin',
                        default=os.environ.get('OPEN_CLI_PROFILE'))
    parser.add_argument('--request-id', action='store', dest='request_id',
                        help='Request Id to track the progress of running this script',
                        default=os.environ.get('OPEN_CLI_REQUEST_ID'))
    parser.add_argument('--conf', action='store', dest='config_file_path', help='Configuration file path')
    #parser.add_argument('--vsp', action='store', dest='vsp', help='ONAP VSP file path')
    #parser.add_argument('--vnf-csar', action='store', dest='vnf_csar', help='TOSCA VNF CSAR file path')
    #parser.add_argument('--ns-csar', action='store', dest='ns_csar', help='TOSCA VNF CSAR file path')
    parser.add_argument('--vnfm-driver', action='store', dest='vnfm_driver', help='VNFM dirver type one of gvnfmdriver or hwvnfmdriver',
                        choices=('gvnfmdriver', 'hwvnfmdriver'))
    parser.add_argument('--vnf-name', action='store', dest='vnf_name', help='VNF Name')
    parser.add_argument('--vendor-name', action='store', dest='vendor_name', help='VNF Vendor name')
    parser.add_argument('--result-json', action='store', dest='result', help='Result json file. ' \
                                    '\nInstead of creating new ONAP objects while running this script \nand to use the existing ONAP object Ids, '\
                                    'use this \nresult json parameter. Object Id names are provided in configuration \nfile under ONAP section')
    #parser.add_argument('--mode', action='store', dest='mode', help='Supports 5 mode.'\
    #                    '\nsetup - Create the required VLM, service type, cloud, customer and \nsubscription as given in conf file' \
    #                    '\nstandup - Create the VSP, VF Model, Service Model and provision\n the service using VFC'\
    #                    '\ncleanup - Remove the ONAP objects which are either created during \nsetup and standup phase or provided by the user in result-json file ' \
    #                               '\nCAUTION: If required, do not provide the existing ONAP object ids \nin result-json while doing the cleanup, to avoid them getting deleted.'\
    #                    '\ncheckup - Check the deployment weather OCOMP is working properly or not' \
    #                    '\nprovision - Run thru setup -> standup' \
    #                    '\nvalidate -  run thru setup -> standup -> cleanup modes for end to end vnf validation',
    #                               choices=('setup', 'standup', 'cleanup', 'checkup', 'provision', 'validate'))

    args = parser.parse_args()
    print (args)

    if not args.product:
        product = 'onap-dublin'
    else:
        product = args.product

    if not args.profile:
        profile = 'onap-dublin'
    else:
        profile = args.profile

    request_id = args.request_id
    if not request_id:
        request_id = str(uuid.uuid4())

#    vsp_csar = args.vsp
#    vnf_csar = args.vnf_csar
#    ns_csar = args.ns_csar

    #if args.mode:
    #    mode = args.mode
    #else:
    #    mode = 'checkup'

    if args.vnfm_driver:
        vnfm_driver = args.vnfm_driver
    else:
        vnfm_driver = 'gvnfmdriver'

    if args.vnf_name:
        vnf_name = args.vnf_name
    else:
        vnf_name = None

    if args.vendor_name:
        vendor_name = args.vendor_name
    else:
        vendor_name = None

    conf = {}
    config_file = args.config_file_path
    with open(config_file) as json_file:
        conf = json.load(json_file)
        if not 'uid' in conf['ONAP']:
            conf['ONAP']['uid'] = ''.join(random.sample(string.ascii_lowercase,5))
#        if vsp_csar:
#            conf['vnf']['vsp-csar'] = vsp_csar
#        if vnf_csar:
#            conf['vnf']['vnf-csar'] = vnf_csar
#        if ns_csar:
#            conf['vnf']['ns-csar'] = vnf_csar
#        if vnf_name:
#            conf['vnf']['name'] = vnf_name
#        conf['vnf']['name'] = '{}{}'.format(conf['vnf']['name'], conf['ONAP']['uid'])
#        if vendor_name:
#            conf['vnf']['vendor-name'] = vendor_name
#        conf['vnf']['vendor-name'] = '{}-{}'.format(conf['vnf']['vendor-name'], conf['ONAP']['uid'])

    if args.result:
        result_file = args.result
    #    with open(result_file) as r_file:
    #        result_json = json.load(r_file)
    #        for r in result_json:
    #            if r in conf['ONAP']:
    #                conf['ONAP'][r] = result_json[r]
    #else:
        result_file = None

    print (OCOMP.version())

    onap = ONAP(product, profile, conf, request_id)
    onap_api = ONAP_api(conf['vnfm']['gvnfmdriver']['url'], conf)

    try:
        onap.setup_cloud_and_subscription()
        onap.create_vnf() # onboard vnf and onboard ns
        ns = STCDemoNS(conf, onap_api) 
        ns.set_openstack_client()
        ns.instantiate(conf['ns']['ns_uuid'], onap.service_type_id, onap.customer_id, onap.customer_id)
        ns.wait_vnf_ready()
        testresult = None
        test = SimpleTrafficTest(labserver_ip=conf['ONAP']['labserver_ip'],
                                stcv_west_mgmt_ip=ns.stcv_west_ip,
                                stcv_west_test_port_ip=ns.stcv_west_test_port_ip,
                                stcv_east_mgmt_ip=ns.stcv_east_ip,
                                stcv_east_test_port_ip=ns.stcv_east_test_port_ip,
                                dut_left_ip=ns.dut_left_ip,
                                dut_right_ip=ns.dut_right_ip)
        testresult = test.run(port_rate=10, duration=60)

    except Exception as e: 
        print(e)
        
    finally:
        onap.cleanup()
        print ('Done')


        #onap_result = json.dumps(onap, default=lambda x: x.__dict__)
        #print(onap_result)

        if result_file:
            #Remove conf and ocomp from the onap object
            #for attr in ['ocomp', 'tag', 'conf']:
            #    delattr(onap, attr)

            with open(result_file, "w") as f:
                f.write(json.dumps(testresult, default=lambda x: x.__dict__))