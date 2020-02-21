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

    def show_ns_package(self, ns_pkg_id=None):
        if ns_pkg_id:
            url = self.base_url + "/api/nsd/v1/ns_descriptors/" + ns_pkg_id
        else:
            url = self.base_url + "/api/nsd/v1/ns_descriptors"
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        resp = requests.get(url, headers=headers)
        logger.info("ns package: \n %s" % json.dumps(resp.json(), indent=2))

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


# called in std_demo_ns
    def get_vnfd_id(self, vnf_pkg_id):
        vnf_package_url = self.base_url + '/api/vnfpkgm/v1/vnf_packages/%s' % vnf_pkg_id
        resp = requests.get(vnf_package_url)
        if 200 == resp.status_code:
            logger.debug("vnf pkg info: \n %s" % json.dumps(resp.json(), indent=2))
            vnfdId = resp.json().get("vnfdId")
            return vnfdId
        else:
            return None

    def get_vnf_pkg_id_list(self, ns_pkg_id):
        url = self.base_url + "/api/nsd/v1/ns_descriptors/" + ns_pkg_id
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        resp = requests.get(url, headers=headers)
        return resp.json()["vnfPkgIds"]

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

# terminate and delete method
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



