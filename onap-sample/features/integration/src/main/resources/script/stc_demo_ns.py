import logging
import sys
import time

import openstack

logger = logging.getLogger(__name__)

class STCDemoNSError(Exception):
    pass

class STCDemoNS(object):
    # following parameters must be align with the csar package
    stc_west_instance_name = "stcv_west"
    stc_east_instance_name = "stcv_east"
    openwrt_instance_name = "dut"
    mgmt_net_name = "external"
    west_test_net_name = "west_net"
    east_test_net_name = "east_net"

    def __init__(self, conf, onap_api):
        self.conf = conf
        self.onap_api = onap_api
        self.ns_instance_id = None

        self.openstack_client = None

        self._stcv_west_ip = None
        self._stcv_west_test_port_ip = None
        self._stcv_east_ip = None
        self._stcv_east_test_port_ip = None
        self._dut_left_ip = None
        self._dut_right_ip = None

        self.params = {
            "auth_url": self.conf['cloud']['identity-url'],
            "username": self.conf['cloud']['username'],
            "password": self.conf['cloud']['password'],
            "identity_api_version": "3",
            "project_id": self.conf['ONAP']['tenant_id'], 
            "project_domain_id": "default",
            "user_domain_name": "Default",
            "region": self.conf['cloud']['region'],
            "verify": False,
            "auth_type": "password"
    }


    @property
    def stcv_west_ip(self):
        return self._stcv_west_ip

    @property
    def stcv_west_test_port_ip(self):
        return self._stcv_west_test_port_ip

    @property
    def stcv_east_ip(self):
        return self._stcv_east_ip

    @property
    def stcv_east_test_port_ip(self):
        return self._stcv_east_test_port_ip

    @property
    def dut_left_ip(self):
        return self._dut_left_ip

    @property
    def dut_right_ip(self):
        return self._dut_right_ip

    def set_openstack_client(self):
        try:
            client = openstack.connect(**self.params)
            client.authorize()
        except Exception as e:
            logger.error(e)
            raise STCDemoNSError("create openstack client fail.")

        # server = client.get_server(name_or_id="ubuntu1604")
        self.openstack_client = client

    def instantiate(self, ns_pkg_id): 
        vnfd_id_list = []

        # get vnfd id list according to ns_pkg_id
        vnf_pkg_id_list = self.onap_api.get_vnf_pkg_id_list(ns_pkg_id)
        for pkg_id in vnf_pkg_id_list:
            vnfd_id = self.onap_api.get_vnfd_id(pkg_id)
        for pkg_id in vnf_pkg_id_list:
            vnfd_id_list.append(vnfd_id)

        ns_instance_id = self.onap_api.create_ns(ns_name="qdai_demostcns",
                            ns_desc="STC test demo ns",
                            ns_pkg_id=ns_pkg_id,
                            service_type = self.conf['subscription']['service-type'],      
                            customer_name= self.conf['subscription']['customer-name']) 
        try:
            ns_instance_jod_id = self.onap_api.instantiate_ns(ns_instance_id, vnfd_id_list=vnfd_id_list)
            self.onap_api.waitProcessFinished(ns_instance_id, ns_instance_jod_id, "instantiate")
        except Exception as e:
            self.onap_api.delete_ns(ns_instance_id)

        logger.info("instantiate ns success. ")
        self.ns_instance_id = ns_instance_id

        stc_west = self.get_stc_west_instance_info()
        self._stcv_west_ip = stc_west["mgmt_ip"]
        self._stcv_west_test_port_ip = stc_west["test_port_ip"]

        stc_east = self.get_stc_east_instance_info()
        self._stcv_east_ip = stc_east["mgmt_ip"]
        self._stcv_east_test_port_ip = stc_east["test_port_ip"]

        dut = self.get_dut_instance_info()
        self._dut_left_ip = dut["left_port_ip"]
        self._dut_right_ip = dut["right_port_ip"]

    def wait_vnf_ready(self):
        time.sleep(10)
        return

    def get_stc_west_instance_info(self):
        # get server id from ns instance
        vnfid = self.onap_api.get_vnfid(self.ns_instance_id, self.stc_west_instance_name)  #"stcv_west"
        server_id = self.onap_api.get_server_ids(vnfid)[0]
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
        vnfid = self.onap_api.get_vnfid(self.ns_instance_id, self.stc_east_instance_name)
        server_id = self.onap_api.get_server_ids(vnfid)[0]
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
        vnfid = self.onap_api.get_vnfid(self.ns_instance_id, self.openwrt_instance_name)
        server_id = self.onap_api.get_server_ids(vnfid)[0]
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