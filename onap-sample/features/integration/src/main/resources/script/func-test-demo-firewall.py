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
import traceback

############copied from spirent script##########
import logging
import requests
import openstack

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(hdlr=handler)
logger.setLevel(logging.DEBUG)
logger.propagate=True

################################################

import SUT_config

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
        self.location_id = None
        self.location_version = None
        self.cloud_id = None
        self.cloud_version = None
        self.service_type_id = None
        self.service_type_version = None
        self.customer_id = None
        self.customer_version = None
        self.subscription_version = None
        self.esr_vnfm_id = None
        self.esr_vnfm_version = None
        self.ns_instance_id = None

    def setup_cloud_and_subscription(self):
        associate = False
        if not self.location_id and not self.location_version:
            location_id = 'ocomp-region-{}'.format('VTP123')
            logger.debug('----------complex-create----------')
            self.ocomp.run(command='complex-create',
                                    params={'physical-location-id': location_id,
                                            'data-center-code': 'ocomp',
                                            'complex-name': location_id,
                                            'identity-url': self.conf['cloud']['identityUrl'],
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
            cloud_id = 'OCOMP-{}'.format('VTP123')
            logger.debug('----------cloud-create----------')
            self.ocomp.run(command='cloud-create',
                                    params={'region-name': self.conf['cloud']['region'],
                                            'complex-name': self.location_id,
                                            'identity-url': self.conf['cloud']['identityUrl'],
                                            'cloud-owner': cloud_id,
                                            'cloud-type': 'openstack',
                                            'owner-type': 'ocomp',
                                            'cloud-region-version': self.conf['cloud']['version'],
                                            'cloud-zone': 'az1',
                                            'esr-id': cloud_id,
                                            'service-url': self.conf['cloud']['identityUrl'],
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
            service_type_id = '{}-{}'.format('tosca_vnf_validation', 'VTP123') # service-type + '-' + uid
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
            customer_id = '{}-{}'.format('ovp','123') # customer-name + - + random
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
            vnfmdriver = self.conf['vnf']['vnfm_driver'] 

            esr_vnfm_id = str(uuid.uuid4())
            logger.debug('----------vnfm-create----------')
            self.ocomp.run(command='vnfm-create',
                                    params={'vim-id': self.cloud_id + "_" + self.conf['cloud']['region'],
                                            'vnfm-id': esr_vnfm_id,
                                            'name': 'OCOMP {}'.format(vnfmdriver),
                                            'type': vnfmdriver,
                                            'vendor': 'onap-dublin',
                                            'vnfm-version': "v1.0",  #self.conf['vnfm'][vnfmdriver]['version'],
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
        vnfs = self.conf["vnf_uuids"]
        logger.debug('----------vfc-catalog-onboard-vnf----------')
        for vnf_key, vnf_value in vnfs.items():
            self.ocomp.run(command='vfc-catalog-onboard-vnf',
                           params={'vnf-csar-uuid': vnf_value })

        time.sleep(60)
        logger.debug('----------vfc-catalog-onboard-ns----------')
        self.ocomp.run(command='vfc-catalog-onboard-ns',
                                params={'ns-csar-uuid': self.conf['ns_uuid']}) 

        logger.debug('----------vfc-nslcm-create----------')
        
        output = self.ocomp.run(command='vfc-nslcm-create',
                                params={'ns-csar-uuid': self.conf['ns_uuid'], 
                                        'ns-csar-name': 'stcv_ns',
                                        'customer-name': self.customer_id,
                                        'service-type': self.service_type_id})

        self.ns_instance_id = output['ns-instance-id']

        vnfmdriver = self.conf['vnf']['vnfm_driver']
        logger.debug('----------vfc-nslcm-instantiate----------')        
        output = self.ocomp.run(command='vfc-nslcm-instantiate',
                                params={'ns-instance-id': self.ns_instance_id,
                                        'location': self.cloud_id+'_'+self.conf['cloud']['region'],
                                        'sdn-controller-id': self.esr_vnfm_id})
        jobid = output['job-id']
        self.waitProcessFinished(jobid)


    def traffic_test(self, labserver, username, stcv1_mgmtip, stcv1_testip, stcv2_mgmtip, stcv2_testip, dut_leftip, dut_rightip):
        logger.debug('---------- execute traffic test script ----------')
        output = self.ocomp.run(command='traffic-forward-test',
                         params={
                                 'labserver-ip': labserver,
                                 'username': username,
                                 'stcv1-mgmt-ip': stcv1_mgmtip,
                                 'stcv1-test-ip': stcv1_testip,
                                 'stcv2-mgmt-ip': stcv2_mgmtip,
                                 'stcv2-test-ip': stcv2_testip,
                                 'dut-left-ip': dut_leftip,
                                 'dut-right-ip': dut_rightip,
                                 'timeout': '600000'
                                 })
        print(output)
        logger.debug('---------- execute traffic test script done ----------')
        return output


    def waitProcessFinished(self, job_id):
        vnfmdriver = self.conf['vnf']['vnfm_driver']
        base_url = self.conf['vnfm'][vnfmdriver]['url']
        job_url = base_url + "/api/nslcm/v1/jobs/%s" % job_id
        progress = 0
        for i in range(500):
            job_resp = requests.get(url=job_url)
            if 200 == job_resp.status_code:
                if "responseDescriptor" in job_resp.json():
                    progress_rep = (job_resp.json())["responseDescriptor"]["progress"]
                    if 100 != progress_rep:
                        if 255 == progress_rep:
                            logger.error("The operation failed.")
                            break
                        elif progress_rep != progress:
                            progress = progress_rep
                            logger.info('The operation process is %s.' % progress)
                        time.sleep(0.2)
                    else:
                        logger.info('The operation process is %s.' % progress_rep)
                        logger.info("The operation successfully finished.")
                        time.sleep(10)  
                        break

    def cleanup(self):
        if self.ns_instance_id:
            logger.debug('----------vfc-nslcm-terminate----------')
            output = self.ocomp.run(command='vfc-nslcm-terminate',
                            params={'ns-instance-id': self.ns_instance_id})
            jobid = output['job-id']
            self.waitProcessFinished(jobid)

            logger.debug('----------vfc-nslcm-delete----------')
            self.ocomp.run(command='vfc-nslcm-delete',
                            params={'ns-instance-id': self.ns_instance_id})
            self.ns_instance_id = None

        self.ocomp.run(command='vfc-catalog-delete-ns',
                       params={'ns-csar-uuid': self.conf['ns_uuid']}) 

        vnfs = self.conf["vnf_uuids"] 
        for vnf_key, vnf_value in vnfs.items():
            self.ocomp.run(command='vfc-catalog-delete-vnf',
                           params={'vnf-csar-uuid': vnf_value})

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


########## Codes below this line moved from stc_demo_ns and onap_api #############
class onap_api:

    def __init__(self, conf, ns_instance_id, tenant_id, topo_info):
        self.conf = conf
        vnfmdriver = self.conf['vnf']['vnfm_driver'] 
        self.base_url = self.conf['vnfm'][vnfmdriver]['url']
        self.ns_instance_id = ns_instance_id
        self.tenant_id = tenant_id        
        self.aai_header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            'X-TransactionId': "9999",
            'Real-Time': "true",
            'X-FromAppId': "jimmy-postman",
            "Authorization": "Basic QUFJOkFBSQ=="
        }
        self.stc_west_instance_name = topo_info['stcv1_name']
        self.stc_east_instance_name = topo_info['stcv2_name']
        self.openwrt_instance_name = topo_info['sut_name']
        self.mgmt_net_name = topo_info['mgmt_network']
        self.west_test_net_name = topo_info['west_network']
        self.east_test_net_name = topo_info['east_network']

    def set_openstack_client(self):
        params = {
            "auth_url": self.conf['cloud']['identityUrl'],
            "username": self.conf['cloud']['username'],
            "password": self.conf['cloud']['password'],
            "identity_api_version": "3",
            "project_id": self.tenant_id, 
            "project_domain_id": "default",
            "user_domain_name": "Default",
            "region": self.conf['cloud']['region'],
            "verify": False,
            "auth_type": "password"
        }
        logger.debug('---------- create openstack client ----------')
        client = openstack.connect(**params)
        client.authorize()
        logger.debug('---------- create openstack client done ----------')
        # server = client.get_server(name_or_id="ubuntu1604")
        self.openstack_client = client

    def get_vnfid(self, vnf_name):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
            }
        url = self.base_url + "/api/nslcm/v1/ns/" + self.ns_instance_id
        resp = requests.get(url, headers=headers, verify=False)
        vnfinfo = [x for x in resp.json()["vnfInfo"] if x["vnfProfileId"]==vnf_name][0]
        if vnfinfo:
            return vnfinfo["vnfInstanceId"]
        else:
            return None

    def get_server_ids(self, vnfid):
        vnf_aai_url = self.base_url + "/aai/v11/network/generic-vnfs"
        resp = requests.get(url=vnf_aai_url, headers=self.aai_header, verify=False)
        vnf_list = resp.json()["generic-vnf"]
        vnf_instance = [x for x in vnf_list if x["vnf-id"] == vnfid][0]
        #logger.info("vnf instance %s info: \n %s" %(vnfid, json.dumps(vnf_instance, indent=2)))
        vserver_relationships = [x for x in vnf_instance["relationship-list"]["relationship"] if x["related-to"] == "vserver"]
        server_ids = []
        for vr in vserver_relationships:
            for data in vr["relationship-data"]:
                if data["relationship-key"] == "vserver.vserver-id":
                    server_ids.append(data["relationship-value"])

        return server_ids            

    def get_stc_west_instance_info(self):
        # get server id from ns instance
        vnfid = self.get_vnfid(self.stc_west_instance_name)  #"stcv_west"
        server_id = self.get_server_ids(vnfid)[0]
        server = self.openstack_client.get_server(server_id)
        server_name = server.name
        mgmt_ip = server.addresses[self.mgmt_net_name][0]["addr"]
        test_port_ip = server.addresses[self.west_test_net_name][0]["addr"]
        instance_info = {
            "name": server_name,
            "id": server_id,
            "mgmt_ip": mgmt_ip,
            "test_port_ip": test_port_ip
        }

        return instance_info

    def get_stc_east_instance_info(self):
        # get server id from ns instance
        vnfid = self.get_vnfid(self.stc_east_instance_name)
        server_id = self.get_server_ids(vnfid)[0]
        server = self.openstack_client.get_server(server_id)
        server_name = server.name
        mgmt_ip = server.addresses[self.mgmt_net_name][0]["addr"]
        test_port_ip = server.addresses[self.east_test_net_name][0]["addr"]
        instance_info = {
            "name": server_name,
            "id": server_id,
            "mgmt_ip": mgmt_ip,
            "test_port_ip": test_port_ip
        }

        return instance_info

    def get_dut_instance_info(self):
        # get server id from ns instance
        vnfid = self.get_vnfid(self.openwrt_instance_name)
        server_id = self.get_server_ids(vnfid)[0]
        server = self.openstack_client.get_server(server_id)
        server_name = server.name
        mgmt_ip = server.addresses[self.mgmt_net_name][0]["addr"]
        left_port_ip = server.addresses[self.west_test_net_name][0]["addr"]
        right_port_ip = server.addresses[self.east_test_net_name][0]["addr"]
        instance_info = {
            "name": server_name,
            "id": server_id,
            "mgmt_ip": mgmt_ip,
            "left_port_ip": left_port_ip,
            "right_port_ip": right_port_ip
        }

        return instance_info

    def get_vnfs_info(self):
        logger.debug('----------get_vnf_info_start----------')
        self.set_openstack_client()
        stc_west = self.get_stc_west_instance_info()
        self._stcv_west_ip = stc_west["mgmt_ip"]
        self._stcv_west_test_port_ip = stc_west["test_port_ip"]
        logger.debug('stcv_west_ip: {} , stcv_west_test_ip: {}'.format(self._stcv_west_ip,self._stcv_west_test_port_ip))        

        stc_east = self.get_stc_east_instance_info()
        self._stcv_east_ip = stc_east["mgmt_ip"]
        self._stcv_east_test_port_ip = stc_east["test_port_ip"]
        logger.debug('stcv_east_ip: {} , stcv_east_test_ip: {}'.format(self._stcv_east_ip,self._stcv_east_test_port_ip))

        dut = self.get_dut_instance_info()
        self._dut_mgmt_ip = dut["mgmt_ip"]
        self._dut_left_ip = dut["left_port_ip"]
        self._dut_right_ip = dut["right_port_ip"]
        logger.debug('dut_mgmt_ip: {} , dut_left_ip: {} , dut_right_ip: {}'.format(self._dut_mgmt_ip,self._dut_left_ip,self._dut_right_ip))
        logger.debug('----------get_vnf_info_done----------')

########## Codes above this line moved from stc_demo_ns and onap_api #############

class FailureException(Exception):
    "this is user's Exception for check the failed test result "
    def __init__(self):
        self.failure = 'Test case execution finished but the testresult is failed.'
    def __str__(self):
        return self.failure


#Main
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ONAP TOSCA VNF validation using ONAP CLI and Open Command Platform (OCOMP)", formatter_class=RawTextHelpFormatter)
    #parser.add_argument('--product', action='store', dest='product', help='OCOMP product to use, default to onap-dublin',
    #                    default=os.environ.get('OPEN_CLI_PRODUCT_IN_USE'))
    parser.add_argument('--profile', action='store', dest='profile', help='OCOMP profile to use, default to onap-dublin', default = 'onap-dublin' )
    parser.add_argument('--request-id', action='store', dest='request_id', help='Request Id to track the progress of running this script')
    

    #parser.add_argument('--vnfm-driver', action='store', dest='vnfm_driver', help='VNFM dirver type one of gvnfmdriver or hwvnfmdriver',
    #                    choices=('gvnfmdriver', 'hwvnfmdriver'))
    #parser.add_argument('--vnf-name', action='store', dest='vnf_name', help='VNF Name')
    #parser.add_argument('--vendor-name', action='store', dest='vendor_name', help='VNF Vendor name')
    parser.add_argument('--conf', action='store', dest='config_file_path', help='Configuration file path')
    #
    parser.add_argument('--stcv1_uuid', action='store', dest='stcv1_uuid', help='The uuid value of stcv1 instrument from SDC')
    parser.add_argument('--stcv2_uuid', action='store', dest='stcv2_uuid', help='The uuid value of stcv2 instrument from SDC')
    parser.add_argument('--sut_uuid', action='store', dest='sut_uuid', help='The uuid value of openwrt from SDC')
    parser.add_argument('--ns_uuid', action='store', dest='ns_uuid', help='The uuid value of Network Service from SDC')
    #
    parser.add_argument('--stcv1_vnfname', action='store', dest='stcv1_vnfname', help='The vnf name of stcv1 instrument from topology designed in SDC')
    parser.add_argument('--stcv2_vnfname', action='store', dest='stcv2_vnfname', help='The vnf name of stcv2 instrument from topology designed in SDC')
    parser.add_argument('--sut_vnfname', action='store', dest='sut_vnfname', help='The vnf name of sut from topology designed in SDC')
    parser.add_argument('--mgmt_netname', action='store', dest='mgmt_netname', help='The network name of MGMT network in topology')
    parser.add_argument('--west_netname', action='store', dest='west_netname', help='The network name of west network in topology, which is between stcv1 and sut')
    parser.add_argument('--east_netname', action='store', dest='east_netname', help='The network name of east network in topology, which is between stcv2 and sut')
    #
    parser.add_argument('--result-json', action='store', dest='result', help='Result json file.')


    args = parser.parse_args()
    print (args)

    product = 'onap-dublin'
    profile = args.profile

    topology_info= {'stcv1_name': args.stcv1_vnfname,
                    'stcv2_name': args.stcv2_vnfname,
                    'sut_name': args.sut_vnfname,
                    'mgmt_network': args.mgmt_netname,
                    'west_network': args.west_netname,
                    'east_network': args.east_netname}

    conf = {}
    config_file = args.config_file_path
    if config_file[0]=='"' and config_file[-1]=='"':
        config_file = config_file[1:-1]

    with open(config_file) as json_file:
        conf = json.load(json_file)
        conf["vnf_uuids"] = {"stcv01": args.stcv1_uuid, "stcv02": args.stcv2_uuid, "openwrt": args.sut_uuid}
        conf["ns_uuid"] = args.ns_uuid


    if args.result:
        result_file = args.result
    else:
        result_file = None


    request_id = args.request_id


    print (OCOMP.version())
    testresult = {}
    onap = ONAP(product, profile, conf, request_id)


    try:
        onap.setup_cloud_and_subscription()
        onap.create_vnf() # onboard vnf,onboard ns,create ns, instantiate ns
        ns = onap_api(conf, onap.ns_instance_id, onap.tenant_id, topology_info)
        ns.get_vnfs_info()

        opwrt = SUT_config(ns._dut_mgmt_ip)
        opwrt.set_passwd_webui()
        opwrt.connect()
        trust_if = opwrt.get_if_name(ns._dut_left_ip)
        opwrt.create_zone('Trust',trust_if)
        ext_if = opwrt.get_if_name(ns._dut_right_ip)
        opwrt.create_zone('External',ext_if) 
        opwrt.create_rule('rule1', 'Trust', 'External', 'all', 'ACCEPT')
        opwrt.create_rule('rule1', 'External', 'Trust', 'all', 'DROP')




        testresult = onap.traffic_test(labserver=conf['instrument']['instrument_mgs']['mnt_address'], 
                                        username = conf['instrument']['instrument_mgs']['username'],
                                        stcv1_mgmtip=ns._stcv_west_ip, 
                                        stcv1_testip=ns._stcv_west_test_port_ip, 
                                        stcv2_mgmtip=ns._stcv_east_ip, 
                                        stcv2_testip=ns._stcv_east_test_port_ip, 
                                        dut_leftip=ns._dut_left_ip, 
                                        dut_rightip=ns._dut_right_ip)

    except Exception as e:
        logger.debug('---------- Exception Happened! ----------') 
        print(e)
        print('traceback.print_exc():')
        traceback.print_exc()
 
    finally:
        #puase = input('stop here before cleanup: ')
        onap.cleanup()
        print ('Done')

        if result_file:
            with open(result_file, "w") as f:
                f.write(json.dumps(testresult, default=lambda x: x.__dict__))

        if 'Test_result' in testresult:
            if testresult['Test_result'] == 'FAIL':
               raise FailureException()
            else:
                pass
        else:
            raise FailureException()


