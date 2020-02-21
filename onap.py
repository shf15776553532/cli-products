
##############################################################################
# Copyright (c) 2018 Spirent Communications and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Author: qiang.dai@spirent.com
#
##############################################################################

import requests
import logging
import json
import sys
import os
import time
import uuid

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(hdlr=handler)
logger.setLevel(logging.DEBUG)

class ONAPError(Exception):
    pass

class ONAP(object):

    def __init__(self, base_url):
        self.base_url = base_url
        self.aai_header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            'X-TransactionId': "9999",
            'Real-Time': "true",
            'X-FromAppId': "jimmy-postman",
            "Authorization": "Basic QUFJOkFBSQ=="
        }
        self.pkg_path = ""
        return

    def create_complex(self):
        self.complex_version = None
        complex_create_string = "oclip complex-create -j {} -r {} -x {} -y {} -lt {} -l {} -i {} -lo {} \
                             -S {} -la {} -g {} -w {} -z {} -k {} -o {} -q {} -m {} -u {} -p {}".format(
            self.config_params["street2"],
            self.config_params["physical_location"], self.config_params["complex_name"],
            self.config_params["data_center_code"], self.config_params["latitude"], self.config_params["region"],
            self.config_params["street1"], self.config_params["longitude"], self.config_params["state"],
            self.config_params["lata"], self.config_params["city"], self.config_params["postal-code"],
            self.config_params["complex_name"], self.config_params["country"], self.config_params["elevation"],
            self.config_params["identity_url"], self.config_params["aai_url"], self.config_params["aai_username"],
            self.config_params["aai_password"])
        os.system(complex_create_string)

        complex_url = self.base_url + "/aai/v11/cloud-infrastructure/complexes"
        complex_list_response = requests.get(url=complex_url, headers=self.aai_header, verify=False)
        if complex_list_response.status_code == 200:
            for complex in (complex_list_response.json())["complex"]:
                if complex['physical-location-id'] == self.config_params["complex_name"]:
                    self.complex_version = complex['resource-version']
                    print("Complex %s resource-version is %s."
                          % (self.config_params["complex_name"], self.complex_version))

    def delete_complex(self):
        complex_delete_string = 'oclip complex-delete -x {} -y {} -m {} -u {} -p {}'.format(
            self.config_params["complex_name"], self.complex_version, self.config_params["aai_url"],
            self.config_params["aai_username"], self.config_params["aai_password"])
        os.system(complex_delete_string)
        print("Delete complex--successful")
        self.complex_version = None

    def show_complexes(self):
        complex_url = self.base_url + "/aai/v11/cloud-infrastructure/complexes"
        resp = requests.get(url=complex_url, headers=self.aai_header, verify=False)
        complex = resp.json()["complex"]
        logger.info("%d complexes: \n %s" % (len(complex), json.dumps(complex, indent=2)))

    def register_cloud(self, cloud_region, values):
        print("Create Cloud--beginning")
        self.cloud_version = None
        cloud_create_string = 'oclip cloud-create -e {} -b {} ' \
                              '-x {} -y {} -j {} -w {} -l {} -url {} -n {} -q {} -r {} -Q {} -i {} -g {} \
                              -z {} -k {} -c {} -m {} -u {} -p {}' \
            .format(values.get("esr-system-info-id"), values.get("user-name"),
                    self.config_params["cloud-owner"],
                    cloud_region, values.get("password"),
                    values.get("cloud-region-version"), values.get("default-tenant"),
                    values.get("service-url"), self.config_params["complex_name"],
                    values.get("cloud-type"), self.config_params["owner-defined-type"],
                    values.get("system-type"), values.get("identity-url"),
                    self.config_params["cloud-zone"], values.get("ssl-insecure"),
                    values.get("system-status"), values.get("cloud-domain"),
                    self.config_params["aai_url"],
                    self.config_params["aai_username"],
                    self.config_params["aai_password"])

        os.system(cloud_create_string)
        print("Create Cloud--successful")

        print("Associate Cloud with complex--beginning")
        complex_associate_string = "oclip complex-associate -x {} -y {} -z {} -m {} -u {} -p {}".format(
            self.config_params["complex_name"],
            cloud_region, self.config_params["cloud-owner"], self.config_params["aai_url"],
            self.config_params["aai_username"],
            self.config_params["aai_password"])
        os.system(complex_associate_string)
        print("Associate Cloud with complex--successful")

        print("Register Cloud with Multicloud--beginning")
        multicloud_register_string = "oclip multicloud-register-cloud -y {} -x {} -m {}".format(
            self.config_params["cloud-owner"], cloud_region, self.config_params["multicloud_url"])
        os.system(multicloud_register_string)
        print("Register Cloud with Multicloud--successful")

        cloud_url = self.base_url + "/aai/v11/cloud-infrastructure/cloud-regions"
        cloud_list_response = requests.get(url=cloud_url, headers=self.aai_header, verify=False)
        if cloud_list_response.status_code == 200:
            for cloud in (cloud_list_response.json())["cloud-region"]:
                if cloud['cloud-owner'] == self.config_params["cloud-owner"]:
                    self.cloud_version = cloud['resource-version']
                    print("Cloud %s resource-version is %s."
                          % (self.config_params["cloud-owner"], self.cloud_version))

    def delete_cloud(self):
        print("Multicloud-cloud-delete--beginning")
        cloud_region = list(self.config_params["cloud_region_data"].keys())[0]
        header = {'content-type': 'application/json', 'accept': 'application/json'}
        multicloud_url = self.base_url + "/api/multicloud-titaniumcloud/v1/{}/{}" \
            .format(self.config_params["cloud-owner"], cloud_region)
        requests.delete(url=multicloud_url, headers=header)
        print("Multicloud-cloud-delete----successful")
        self.customer_version = None

    def show_cloud_regions(self):
        cloud_url = self.base_url + "/aai/v11/cloud-infrastructure/cloud-regions"
        resp = requests.get(url=cloud_url, headers=self.aai_header, verify=False)
        cloud_region = resp.json()["cloud-region"]
        logger.info("%d cloud regions: \n %s" % (len(cloud_region), json.dumps(cloud_region, indent=2)))

    def create_service_type(self):
        self.service_type_version = None
        create_string = "oclip service-type-create -x {} -y {} -m {} -u {} -p {}".format(
            self.config_params["service_name"], self.config_params["service_name"], self.config_params["aai_url"],
            self.config_params["aai_username"], self.config_params["aai_password"])
        os.system(create_string)

        service_tpe_list_url = self.base_url + "/aai/v11/service-design-and-creation/services"
        service_type_list_response = requests.get(url=service_tpe_list_url, headers=self.aai_header, verify=False)
        if service_type_list_response.status_code == 200:
            for service in (service_type_list_response.json())["service"]:
                if service["service-id"] == self.config_params["service_name"]:
                    self.service_type_version = service['resource-version']
                    print("Service type %s resource-version is %s."
                          % (self.config_params["service_name"], self.service_type_version))

    def delete_service_type(self):
        print("delete service type--beginning")
        service_delete_string = 'oclip service-type-delete -x {} -y {} -m {} -u {} -p {}'.format(
            self.config_params["service_name"], self.service_type_version, self.config_params["aai_url"],
            self.config_params["aai_username"], self.config_params["aai_password"])
        os.system(service_delete_string)
        print("delete service type--successful")
        self.service_type_version = None

    def show_service_types(self):
        service_type_list_url = self.base_url + "/aai/v11/service-design-and-creation/services"
        resp = requests.get(url=service_type_list_url, headers=self.aai_header, verify=False)
        logger.info("service types: \n %s" % json.dumps(resp.json(), indent=2))

    def create_customer(self):
        self.customer_version = None
        create_string = "oclip customer-create -x {} -y {} -m {} -u {} -p {}".format(
            self.config_params["customer_name"],
            self.config_params["subscriber_name"],
            self.config_params["aai_url"],
            self.config_params["aai_username"],
            self.config_params["aai_password"])
        os.system(create_string)

        customer_list_url = self.base_url + "/aai/v11/business/customers"
        customer_list_response = requests.get(url=customer_list_url, headers=self.aai_header, verify=False)
        if customer_list_response.status_code == 200:
            for cutsomer in (customer_list_response.json())["customer"]:
                if cutsomer['global-customer-id'] == self.config_params["customer_name"]:
                    self.customer_version = cutsomer['resource-version']
                    print("Customer %s resource-version is %s."
                          % (self.config_params["customer_name"], self.customer_version))

    def delete_customer(self):
        print("delete customer--beginning")
        customer_delete_string = 'oclip customer-delete -x {} -y {} -m {} -u {} -p {}'.format(
            self.config_params["customer_name"], self.customer_version, self.config_params["aai_url"],
            self.config_params["aai_username"], self.config_params["aai_password"])
        os.system(customer_delete_string)
        print("delete customer--successful")
        self.customer_version = None

    def show_customers(self):
        customer_list_url = self.base_url + "/aai/v11/business/customers"
        resp = requests.get(url=customer_list_url, headers=self.aai_header, verify=False)
        logger.info("customers: \n %s" % json.dumps(resp.json(), indent=2))

    def add_customer_subscription(self):
        self.subscription_version = None
        subscription_check = 0
        for cloud_region, cloud_region_values in (self.config_params["cloud_region_data"]).items():
            if subscription_check == 0:
                subscription_string = "oclip subscription-create -x {} -c {} -z {} -e {} " \
                                      "-y {} -r {} -m {} -u {} -p {}" \
                    .format(self.config_params["customer_name"],
                            cloud_region_values.get("tenant-id"),
                            self.config_params["cloud-owner"],
                            self.config_params["service_name"],
                            cloud_region_values.get("default-tenant"),
                            cloud_region, self.config_params["aai_url"],
                            self.config_params["aai_username"],
                            self.config_params["aai_password"])
            else:
                subscription_string = "oclip subscription-cloud-add -x {} -c {} " \
                                      "-z {} -e {} -y {} -r {} -m {} -u {} -p {}" \
                    .format(self.config_params["customer_name"], cloud_region_values.get("tenant-id"),
                            self.config_params["cloud-owner"], self.config_params["service_name"],
                            cloud_region_values.get("default-tenant"), cloud_region,
                            self.config_params["aai_url"],
                            self.config_params["aai_username"],
                            self.config_params["aai_password"])
            os.system(subscription_string)
            subscription_check += 1

        subscription_url = self.base_url + "/aai/v11/business/customers/customer/{}" \
                                           "/service-subscriptions/service-subscription/{}" \
            .format(self.config_params["customer_name"], self.config_params["service_name"])
        resp = requests.get(url=subscription_url, headers=self.aai_header, verify=False)
        if resp.status_code == 200:
            self.subscription_version = resp.json()['resource-version']
            print("Subscription resource-version is %s." % self.subscription_version)

    def remove_customer_subscription(self):
        print("Remove subscription--beginning")
        subscription_delete_string = 'oclip subscription-delete -x {} -y {} -g {} -m {} -u {} -p {}'.format(
            self.config_params["customer_name"], self.config_params["service_name"], self.subscription_version,
            self.config_params["aai_url"],
            self.config_params["aai_username"], self.config_params["aai_password"])
        os.system(subscription_delete_string)
        print("Delete subscription--successful")

    def register_vnfm_helper(self, vnfm_key, values):
        print("Create vnfm--beginning")
        self.esr_vnfm_version = None
        self.esr_vnfm_id = str(uuid.uuid4())
        vnfm_create_string = 'oclip vnfm-create -b {} -c {} -e {} -v {} -g {} -x {} ' \
                             '-y {} -i {} -j {} -q {} -m {} -u {} -p {}' \
            .format(vnfm_key, values.get("type"), values.get("vendor"),
                    values.get("version"), values.get("url"), values.get("vim-id"),
                    self.esr_vnfm_id, values.get("user-name"), values.get("user-password"),
                    values.get("vnfm-version"), self.config_params["aai_url"],
                    self.config_params["aai_username"], self.config_params["aai_password"])

        os.system(vnfm_create_string)
        print("Create vnfm--successful")

        vnfm_url = self.base_url + "/aai/v11/external-system/esr-vnfm-list"
        resp = requests.get(url=vnfm_url, headers=self.aai_header, verify=False)
        if resp.status_code == 200:
            for vnfm in (resp.json())["esr-vnfm"]:
                if vnfm['vnfm-id'] == self.esr_vnfm_id:
                    self.esr_vnfm_version = vnfm['resource-version']
                    print("Vnfm %s resource-version is %s."
                          % (self.esr_vnfm_id, self.esr_vnfm_version))


    def register_vnfm(self):
        vnfm_params = self.config_params["vnfm_params"]
        for vnfm_key, vnfm_values in vnfm_params.items():
            self.register_vnfm_helper(vnfm_key, vnfm_values)

    def unregister_vnfm(self):
        print("Delete vnfm %s" % self.esr_vnfm_id)
        print("Delete vnfm--beginning")
        vnfm_delete_string = 'oclip vnfm-delete -x {} -y {} -m {} -u {} -p {}'.format(
            self.esr_vnfm_id, self.esr_vnfm_version, self.config_params["aai_url"],
            self.config_params["aai_username"], self.config_params["aai_password"])
        os.system(vnfm_delete_string)
        self.esr_vnfm_version = self.esr_vnfm_id = None
        print("Delete vnfm--successful")

    def show_vnfms(self):
        vnfm_url = self.base_url + "/aai/v11/external-system/esr-vnfm-list"
        resp = requests.get(url=vnfm_url, headers=self.aai_header, verify=False)
        logger.info("vnfm list: \n %s" % json.dumps(resp.json(), indent=2))

    def create_vnf_package(self, userDefinedData={}):
        vnf_pkg_id = None
        vnf_url = self.base_url + "/api/vnfpkgm/v1/vnf_packages"
        header = {'content-type': 'application/json', 'accept': 'application/json'}
        resp = requests.post(vnf_url, data=json.dumps(userDefinedData), headers=header)
        if 201 == resp.status_code:
            logger.info("create vnf package successful, vnf package id is %s"
                        % resp.json()["id"])
            vnf_pkg_id = resp.json()["id"]
        else:
            logger.error("create vnf package fail")

        return vnf_pkg_id

    def delete_vnf_package(self, vnf_pkg_id):
        vnf_url = self.base_url + "/api/vnfpkgm/v1/vnf_packages/%s" % vnf_pkg_id
        resp = requests.delete(url=vnf_url)
        if 204 == resp.status_code:
            logger.info("Delete vnf package %s successfully." % vnf_pkg_id)
        else:
            logger.error("Delete vnf package %s failed." % vnf_pkg_id)

    def upload_vnf_package(self, vnf_pkg_id, file_name):
        vnf_upload_url = '{}/api/vnfpkgm/v1/vnf_packages/{}/package_content' \
            .format(self.base_url, vnf_pkg_id)
        file_path = self.pkg_path + "/" + file_name
        vnf_file = open(file_path, 'rb')
        for i in range(10):
            resp = requests.put(vnf_upload_url, files={'file': vnf_file})
            if 202 == resp.status_code:
                logger.info("upload vnf package success")
                break
            else:
                time.sleep(1)
        vnf_file.close()

    def show_vnf_package(self, vnf_pkg_id=None):
        if vnf_pkg_id:
            vnf_package_url = self.base_url + '/api/vnfpkgm/v1/vnf_packages/%s' % vnf_pkg_id
        else:
            vnf_package_url = self.base_url + '/api/vnfpkgm/v1/vnf_packages'
        resp = requests.get(vnf_package_url)
        logger.info("vnf package: \n %s" % json.dumps(resp.json(), indent=2))

    def get_vnfd_id(self, vnf_pkg_id):
        vnf_package_url = self.base_url + '/api/vnfpkgm/v1/vnf_packages/%s' % vnf_pkg_id
        resp = requests.get(vnf_package_url)
        if 200 == resp.status_code:
            logger.debug("vnf pkg info: \n %s" % json.dumps(resp.json(), indent=2))
            vnfdId = resp.json().get("vnfdId")
            return vnfdId
        else:
            return None

    def create_ns_package(self, userDefinedData):
        ns_url = self.base_url + "/api/nsd/v1/ns_descriptors"
        ns_headers = {'content-type': 'application/json', 'accept': 'application/json'}
        ns_data = {'userDefinedData': userDefinedData}
        resp = requests.post(ns_url, data=json.dumps(ns_data), headers=ns_headers)
        ns_pkg_id = None
        if 201 == resp.status_code:
            logger.debug("create ns package resp: \n %s" % json.dumps(resp.json(), indent=2))
            ns_pkg_id = resp.json()["id"]
            logger.info("create ns package successful, ns_pkg_id = %s" % ns_pkg_id)
        else:
            logger.error("create ns package fail.")

        return ns_pkg_id

    def delete_ns_package(self, ns_pkg_id):
        vnf_url = self.base_url + "/api/nsd/v1/ns_descriptors/%s" % ns_pkg_id
        resp = requests.delete(url=vnf_url)
        if 204 == resp.status_code:
            logger.info("Delete ns package %s successfully." % ns_pkg_id)
        else:
            logger.error("Delete ns package %s failed." % ns_pkg_id)

    def upload_ns_package(self, ns_pkg_id, file_name):
        ns_upload_url = '{}/api/nsd/v1/ns_descriptors/{}/nsd_content'. \
            format(self.base_url, ns_pkg_id)
        file_path = self.pkg_path + "/" + file_name
        ns_file = open(file_path, 'rb')
        for i in range(10):
            resp = requests.put(ns_upload_url, files={'file': ns_file})
            if 204 == resp.status_code:
                logger.debug("upload ns package resp: \n %s" % json.dumps(resp.json(), indent=2))
                break
            else:
                time.sleep(1)
        ns_file.close()
        return

    def get_vnf_pkg_id_list(self, ns_pkg_id):
        url = self.base_url + "/api/nsd/v1/ns_descriptors/" + ns_pkg_id
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        resp = requests.get(url, headers=headers)
        return resp.json()["vnfPkgIds"]

    def show_ns_package(self, ns_pkg_id=None):
        if ns_pkg_id:
            url = self.base_url + "/api/nsd/v1/ns_descriptors/" + ns_pkg_id
        else:
            url = self.base_url + "/api/nsd/v1/ns_descriptors"
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        resp = requests.get(url, headers=headers)
        logger.info("ns package: \n %s" % json.dumps(resp.json(), indent=2))

    def create_ns(self, ns_name, ns_desc, ns_pkg_id, service_type, customer_name):
        data = {
            "context": {
                "globalCustomerId": customer_name,  # hpa_cust1
                "serviceType": service_type
            },
            "csarId": ns_pkg_id,
            "nsName": ns_name,
            "description": ns_desc
        }
        ns_header = {'content-type': 'application/json', 'accept': 'application/json'}
        ns_url = self.base_url + "/api/nslcm/v1/ns"
        resp = requests.post(ns_url, data=json.dumps(data), headers=ns_header)
        ns_instance_id = None
        if 201 == resp.status_code:
            logger.debug("create ns instance resp: \n %s" % json.dumps(resp.json(), indent=2))
            ns_instance_id = resp.json().get("nsInstanceId")
            logger.info("create ns successfully, the ns instance id is %s" % ns_instance_id)
        else:
            logger.error("create ns fail. ")

        return ns_instance_id

    def instantiate_ns(self, ns_instance_id, vnfd_id_list):
        locationConstraints = [
            {
                "vnfProfileId": x,
                "locationConstraints": {
                    "vimId": "STC_RegionOne"     # self.config_params["location"]
                }
            } for x in vnfd_id_list ]
        data = {
            "additionalParamForNs": {
                "sdnControllerId": 2    #self.config_params["sdc-controller-id"],
            },
            "locationConstraints": locationConstraints
        }

        header = {'content-type': 'application/json', 'accept': 'application/json'}
        instance_url = self.base_url + "/api/nslcm/v1/ns/" + ns_instance_id + "/instantiate"
        resp = requests.post(instance_url, data=json.dumps(data), headers=header)
        ns_instance_jod_id = None
        if 200 == resp.status_code:
            logger.debug("instantiate ns resp: \n %s" % json.dumps(resp.json(), indent=2))
            ns_instance_jod_id = resp.json().get("jobId")
            logger.info("Instantiate ns successfully, the job id is %s" % ns_instance_jod_id)
        else:
            logger.error("Instantiate ns failed. status_code: %d, error info: %s" % (resp.status_code, resp.content["error"]))
            raise ONAPError("Instantiate ns error")

        return ns_instance_jod_id

    def terminate_ns(self, ns_instance_id):
        ns_url = self.base_url + "/api/nslcm/v1/ns/%s" % ns_instance_id
        d = {
            "gracefulTerminationTimeout": 600,
            "terminationType": "FORCEFUL"
        }
        resp = requests.post(url=ns_url + "/terminate", data=d)
        logger.debug("terminate response: \n %s" % json.dumps(resp.json(), indent=2))
        assert 202 == resp.status_code

        terminate_ns_job_id = resp.json()["jobId"]
        logger.info("Terminate job is %s" % terminate_ns_job_id)
        self.waitProcessFinished(ns_instance_id, terminate_ns_job_id, "terminate")
        # logger.debug("wait terminate response: \n %s" % json.dumps(resp.json(), indent=2))

        return

    def delete_ns(self, ns_instance_id):
        logger.info("Delete ns %s --beginning" % ns_instance_id)
        ns_url = self.base_url + "/api/nslcm/v1/ns/%s" % ns_instance_id
        res = requests.delete(ns_url)
        if 204 == res.status_code:
            logger.info("Ns %s delete successfully." % ns_instance_id)
        else:
            logger.info("Ns %s delete fail." % ns_instance_id)

    def waitProcessFinished(self, ns_instance_id, job_id, action):
        job_url = self.base_url + "/api/nslcm/v1/jobs/%s" % job_id
        progress = 0
        for i in range(500):
            job_resp = requests.get(url=job_url)
            if 200 == job_resp.status_code:
                if "responseDescriptor" in job_resp.json():
                    progress_rep = (job_resp.json())["responseDescriptor"]["progress"]
                    if 100 != progress_rep:
                        if 255 == progress_rep:
                            logger.error("Ns %s %s failed." % (ns_instance_id, action))
                            break
                        elif progress_rep != progress:
                            progress = progress_rep
                            logger.info("Ns %s %s process is %s." % (ns_instance_id, action, progress))
                        time.sleep(0.2)
                    else:
                        logger.info("Ns %s %s process is %s." % (ns_instance_id, action, progress_rep))
                        logger.info("Ns %s %s successfully." % (ns_instance_id, action))
                        break

    def get_vserver(self):
        vserver_url = self.base_url + "/aai/v11/cloud-infrastructure/cloud-regions/cloud-region/VCPE22/RegionOne/tenants/tenant/f7b17b0afd374d48a322e95cf4258eec/vservers/vserver/9147a63a-dc03-4546-a885-38e7bad438fa"
        resp = requests.get(url=vserver_url, headers=self.aai_header, verify=False)
        logger.info(json.dumps(resp.json(), indent=2))

    def show_ns_instance(self, ns_instance_id=None):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        url = self.base_url + "/api/nslcm/v1/ns"
        resp = requests.get(url, headers=headers, verify=False)
        if resp.json() and ns_instance_id:
            ns_instance = [x for x in resp.json() if x["nsInstanceId"] == ns_instance_id][0]
            logger.info("ns instance %s info: \n %s" % (ns_instance_id, json.dumps(ns_instance, indent=2)))
        else:
            logger.info("ns info: num = %d\n %s" % (len(resp.json()), json.dumps(resp.json(), indent=2)))

    def show_vnf_instance(self, vnf_instance_id=None):
        vnf_aai_url = self.base_url + "/aai/v11/network/generic-vnfs"
        resp = requests.get(url=vnf_aai_url, headers=self.aai_header, verify=False)
        vnf_list = resp.json()["generic-vnf"]
        if vnf_list and vnf_instance_id:
            vnf_instance = [x for x in vnf_list if x["vnf-id"] == vnf_instance_id][0]
            logger.info("vnf instance %s info: \n %s" %(vnf_instance_id, json.dumps(vnf_instance, indent=2)))
        else:
            logger.info("vnf info: num = %d \n %s" % (len(vnf_list), json.dumps(vnf_list, indent=2)))

    # def show_vnf_instance(self, vnf_instance_id=None):
    #     if vnf_instance_id:
    #         vnf_aai_url = self.base_url + "/aai/v11/network/generic-vnfs/" + vnf_instance_id
    #     else:
    #         vnf_aai_url = self.base_url + "/aai/v11/network/generic-vnfs"
    #     resp = requests.get(url=vnf_aai_url, headers=self.aai_header, verify=False)
    #     vnf_list = resp.json()["generic-vnf"]
    #     if vnf_list and not vnf_instance_id:
    #         vnf_instance = [x for x in vnf_list if x["vnf-id"] == vnf_instance_id][0]
    #         logger.info("vnf instance %s info: \n %s" %(vnf_instance_id, json.dumps(vnf_resp.json(), indent=2)))
    #     else:
    #         logger.info("vnf info: \n %s" % str(vnf_list))

    def get_vnfid(self, ns_instance_id, vnf_name):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        url = self.base_url + "/api/nslcm/v1/ns/" + ns_instance_id
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
        logger.info("vnf instance %s info: \n %s" %(vnfid, json.dumps(vnf_instance, indent=2)))
        vserver_relationships = [x for x in vnf_instance["relationship-list"]["relationship"] if x["related-to"] == "vserver"]
        server_ids = []
        for vr in vserver_relationships:
            for data in vr["relationship-data"]:
                if data["relationship-key"] == "vserver.vserver-id":
                    server_ids.append(data["relationship-value"])

        return server_ids

    def setup(self):
        return

    def teardown(self):
        return

if __name__  == "__main__":

    onap = ONAP(base_url="http://192.168.235.41:30280")
    #onap.show_vnf_instance(vnf_instance_id="24a8d085-7711-49bf-a27c-dc2779b05793")

    onap.show_ns_instance()

    #onap.terminate_ns(ns_instance_id="88d307e2-35ce-4cb2-a924-a5fc23b6a844")
    onap.delete_ns("88d307e2-35ce-4cb2-a924-a5fc23b6a844")

    exit(0)

    userDefinedData = {
        "path": "vgw.csar",
        "csar-id": "9d3e4a5f-7e21-4714-9953-1376269832ba",
        "vsp-name": "vgw-hpa-vsp",
        "vsp-desc": "vgw-hpa-vsp-desc",
        "vsp-version": "1.0",
        "vf-name": "vgw-hpa-vf",
        "vf-description": "vgw-hpa-vf",
        "vf-remarks": "remarkss",
        "vf-version": "1.0",
        "key": "key2",
        "value": "value2"
    }
    vnf_pkg_id = onap.create_vnf_package(userDefinedData)
    onap.upload_vnf_package(vnf_pkg_id, "stcv")
    vnfd_id = onap.get_vnf_package(vnf_pkg_id)
    onap.delete_vnf_package(vnf_pkg_id)

    ns_data = {
        "userDefinedData": {
            "key": "key1",
            "value": "value1",
            "path": "ns_vgw.csar",
            "name": "vcpe11"
        }
    }
    ns_pkg_id = onap.create_ns_package(ns_data)
    onap.upload_ns_package(ns_pkg_id, "demo_ns")
    #nsd_id = onap.

    #vfc.get_complexes()
    #vfc.get_cloud_regions()
    onap.get_ns_info()
    onap.get_vnfs()
    print("vserver_info")
    onap.get_vserver()

