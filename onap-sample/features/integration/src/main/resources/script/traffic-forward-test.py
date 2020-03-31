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

import logging
import time
import datetime
import sys
import json
import argparse
from argparse import RawTextHelpFormatter
import traceback

from stcrestclient import stchttp

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(hdlr=handler)
logger.setLevel(logging.DEBUG)

class SimpleTrafficTest(object):

    def __init__(self, labserver_ip, user_name,
                 stcv_west_mgmt_ip, stcv_west_test_port_ip,
                 stcv_east_mgmt_ip, stcv_east_test_port_ip,
                 dut_left_ip, dut_right_ip):
        self.labserver_ip = labserver_ip
        self.user_name = user_name
        self.result1 = None
        self.result2 = None
        self.testpass = None

        self.west_stcv = {
            "mgmt_ip": stcv_west_mgmt_ip,
            "test_port_ip": stcv_west_test_port_ip,
            "gw_ip": dut_left_ip,
            "port_location": "//" + stcv_west_mgmt_ip + "/1/1",
            "port": None,
            "gen": None,
            "ana": None,
            "result": None
        }
        self.east_stcv = {
            "mgmt_ip": stcv_east_mgmt_ip,
            "test_port_ip": stcv_east_test_port_ip,
            "gw_ip": dut_right_ip,
            "port_location": "//" + stcv_east_mgmt_ip + "/1/1",
            "port": None,
            "gen": None,
            "ana": None,
            "result": None
        }

        self.stc = stchttp.StcHttp(labserver_ip, port=80)

        #self.user_name = "csu_user"
        time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        test_name = "simpletraffic - " + time_str
        sess_id = self.user_name + " - " + test_name
        sess_list = self.stc.sessions()
        logger.debug("sess_list: %s", sess_list)
        if sess_id not in sess_list:
            sess_id = self.stc.new_session(self.user_name, test_name)
        self.stc.join_session(sess_id)

        self.sys = "system1"
        self.project = self.stc.get(self.sys, "children-project")

        return

    def end_session(self):
        self.stc.disconnectall()
        sess_list = self.stc.sessions()
        for sess_id in sess_list:
            self.stc.end_session('kill',sess_id)





    def get_port_location(self):
        port_list = []
        phys_chassis_mgr = self.stc.get("system1", "children-physicalchassismanager")
        phys_chassis_list = self.stc.get(phys_chassis_mgr, "children-physicalchassis").split(" ")
        logger.debug("phys_chassis_list: %s" % phys_chassis_list)

        for phys_chassis in phys_chassis_list:
            hostname = self.stc.get(phys_chassis, "hostname")
            phys_mod_list = self.stc.get(phys_chassis, "children-physicaltestmodule").split()
            for phys_mod in phys_mod_list:
                slot = self.stc.get(phys_mod, "index")
                port_group_list = self.stc.get(phys_mod, "children-physicalportgroup").split()
                for port_group in port_group_list:
                    phys_pg = self.stc.get(port_group, "index")
                    phys_port_list = self.stc.get(port_group, "children-physicalport").split()
                    for phys_port in phys_port_list:
                        port_index = self.stc.get(phys_port, "index")
                        loc = self.stc.get(phys_port, "location")
                        logger.debug("PhysPort: host_name: %s, slot: %s, pg: %s, port_index: %s, location: %s" % (
                            hostname, slot, phys_pg, port_index, loc))
                        port_list.append(loc)
        return port_list

    def connect_chassis(self):
        resp = self.stc.perform("ConnectToChassis",
                                AddrList=[self.west_stcv["mgmt_ip"], self.east_stcv["mgmt_ip"]],
                                TimeoutInSec=120)
        assert resp["Status"] == "Completed!"

        return

    def configure_port(self, stcv):
        port = self.stc.create("port", under=self.project, location=stcv["port_location"])
        self.stc.perform("attachports", autoconnect=False, portList=port)

        dev = self.stc.create("emulateddevice", under=self.project, enablepingresponse=True, devicecount="1")

        ethiiif = self.stc.create("ethiiif", under=dev)
        self.stc.config(ethiiif, useDefaultPhyMac=True)

        ipv4if = self.stc.create("ipv4if",
                                 under=dev,
                                 usePortDefaultIpv4Gateway=False,
                                 resolveGatewayMac=True)
        self.stc.config(ipv4if, address=stcv["test_port_ip"])
        self.stc.config(ipv4if, gateway=stcv["gw_ip"])
        #self.stc.config(ipv4if, prefixLength=prefix_len)

        self.stc.config(dev, affiliatedPort=port)
        self.stc.config(ipv4if, stackedOn=ethiiif)
        self.stc.config(dev, topLevelIf=ipv4if)
        self.stc.config(dev, primaryIf=ipv4if)

        # learn physical mac
        self.stc.perform("DetectSourceMacCommand", portlist=port)
        mac = self.stc.get(ethiiif, "SourceMac")
        if mac == "00:00:00:00:00:00" or mac == "00-00-00-00-00-00":
            logger.error("acquire default phy mac fail on port at %s" % stcv["port_location"])
        else:
            logger.info("acquire default phy mac success. port: %s, mac: %s" % (stcv["port_location"], mac))

        # run arp to get gw mac
        resp = self.stc.perform("ArpNdStartCommand", handlelist=port, waitforarptofinish=True)
        assert resp["ArpNdState"] == "SUCCESSFUL"
        # TODO: show gw mac

        stcv["port"] = port
        stcv["ipv4if"] = ipv4if
        stcv["gen"] = self.stc.get(port, "children-generator")
        stcv["ana"] = self.stc.get(port, "children-analyzer")

        return

    def create_stream_block(self):
        self.west_stcv["strblk"] = self.stc.create("streamblock",
                                           under=self.west_stcv["port"],
                                           srcBinding=self.west_stcv["ipv4if"],
                                           dstBinding=self.east_stcv["ipv4if"])
        self.east_stcv["strblk"] = self.stc.create("streamblock",
                                           under=self.east_stcv["port"],
                                           srcBinding=self.east_stcv["ipv4if"],
                                           dstBinding=self.west_stcv["ipv4if"])

    def configure_traffic_load(self, stcv, port_rate, duration):
        gen = stcv["gen"]
        gen_conf = self.stc.get(gen, "children-generatorconfig")
        self.stc.config(gen_conf,
                        DurationMode="SECONDS",
                        Duration=duration,
                        LoadMode="FIXED",
                        FixedLoad=port_rate,
                        LoadUnit="PERCENT_LINE_RATE",
                        SchedulingMode="PORT_BASED")

    def subscrible_result(self):
        self.stc.perform(command="ResultsSubscribe",
                         parent=self.project,
                         resultparent=self.project,
                         configtype="StreamBlock",
                         resulttype="TxStreamResults")
        self.stc.perform(command="ResultsSubscribe",
                         parent=self.project,
                         resultparent=self.project,
                         configtype="StreamBlock",
                         resulttype="RxStreamSummaryResults")
        self.stc.perform(command="ResultsSubscribe",
                         parent=self.project,
                         resultparent=self.project,
                         configtype="GeneratorConfig",
                         resulttype="GeneratorPortResults")
        self.stc.perform(command="ResultsSubscribe",
                         parent=self.project,
                         resultparent=self.project,
                         configtype="AnalyzerConfig",
                         resulttype="AnalyzerPortResults")

    def run_traffic(self):
        self.stc.perform("resultsclearallcommand")

        gen_list = [self.west_stcv["gen"], self.east_stcv["gen"]]
        ana_list = [self.west_stcv["ana"], self.east_stcv["ana"]]
        self.stc.perform("AnalyzerStartCommand", Analyzerlist=ana_list)
        self.stc.perform("GeneratorStartCommand", GeneratorList=gen_list)

        self.stc.perform("Generatorwaitforstopcommand", GeneratorList=gen_list)

        self.stc.perform("AnalyzerStopCommand", Analyzerlist=ana_list)

    def collect_result(self, stcv):
        gen_res = self.stc.get(stcv["gen"], "children-generatorportresults")
        ana_res = self.stc.get(stcv["ana"], "children-analyzerportresults")

        result = {}
        tx_str_res = self.stc.get(stcv["strblk"], "children-txstreamresults")
        rx_str_res = self.stc.get(stcv["strblk"], "children-rxstreamsummaryresults")
        result["tx_frame_count"] = self.stc.get(tx_str_res, "FrameCount")
        result["tx_bit_count"] = self.stc.get(tx_str_res, "BitCount")
        result["rx_frame_count"] = self.stc.get(rx_str_res, "FrameCount")
        result["rx_bit_count"] = self.stc.get(rx_str_res, "BitCount")

        #stcv["result"] = result
        return result

        #stcv["result"]["tx_count"] = self.stc.get(gen_res, "generatorsigframecount")
        # stcv["result"]["tx_rate"] = self.stc.get(gen_res, "generatorbitrate", "generatorframerate")
        # stcv["result"]["tx_duration"] = self.stc.get(gen_res, "txduration")
        #
        # stcv["result"]["rx_count"] = self.stc.get(ana_res, "sigframecount")
        # stcv["result"]["rx_rate"] = self.stc.get(ana_res, "totalbitrate", "totalframerate")

    def show_result(self):
        logger.info("west stcv result: \n %s", json.dumps(self.west_stcv["result"], indent=2))
        logger.info("east stcv result: \n %s", json.dumps(self.east_stcv["result"], indent=2))

    def check_result(self):
        self.result1 = self.collect_result(self.west_stcv)
        self.result2 = self.collect_result(self.east_stcv)
        pkt_loss1 = (int(self.result1["tx_frame_count"]) - int(self.result2["rx_frame_count"])) / int(self.result1["tx_frame_count"]) 
        pkt_loss2 = (int(self.result2["tx_frame_count"]) - int(self.result1["rx_frame_count"])) / int(self.result2["tx_frame_count"])
        #if self.result1["tx_frame_count"]==self.result2["rx_frame_count"] and self.result2["tx_frame_count"]==self.result1["rx_frame_count"]:
        if pkt_loss1 < 0.1 and pkt_loss2 < 0.1:
            self.testpass = 'PASS'
        else:
            self.testpass = 'FAIL'
        

    def run(self, port_rate=1, duration=10):
        try:
            logger.debug('----------Connec to the 2 chassis----------')
            self.connect_chassis()
            logger.debug('----------configure chassis port----------')
            self.configure_port(self.west_stcv)
            self.configure_port(self.east_stcv)
            logger.debug('----------create stream block----------')
            self.create_stream_block()
            logger.debug('----------confiure traffic for 2 STCv----------')
            self.configure_traffic_load(self.west_stcv, port_rate, duration)
            self.configure_traffic_load(self.east_stcv, port_rate, duration)
            logger.debug('----------subscrib result----------')
            self.subscrible_result()
            logger.debug('----------run traffic----------')
            self.run_traffic()
            logger.debug('----------check result----------')
            self.check_result()
            result_dict = {'Test_result': self.testpass,
                           'Stcv1_tx_frame': self.result1["tx_frame_count"],
                           'Stcv1_tx_bit': self.result1["tx_bit_count"],
                           'Stcv1_rx_frame': self.result1["rx_frame_count"],
                           'Stcv1_rx_bit': self.result1["rx_bit_count"],
                           'Stcv2_tx_frame': self.result2["tx_frame_count"],
                           'Stcv2_tx_bit': self.result2["tx_bit_count"],
                           'Stcv2_rx_frame': self.result2["rx_frame_count"],
                           'Stcv2_rx_bit': self.result2["rx_bit_count"]}
            #self.end_session()
        except Exception as e: 
            print(e)
            result_dict = {}

        finally:
            self.end_session()
            return result_dict

        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="run this script to do traffic forwarding test with stcv and openwrt", formatter_class=RawTextHelpFormatter)
    parser.add_argument('--result-json', action='store', dest='resultjson', help='file path of json file contains result')
    parser.add_argument('--labserver-ip', action='store', dest='labserver_ip', help='labserver_ip')
    parser.add_argument('--username', action='store', dest='username', help='username')
    parser.add_argument('--stcv1-mgmt-ip', action='store', dest='stcv_west_ip', help='stcv_west_ip')
    parser.add_argument('--stcv1-test-ip', action='store', dest='stcv_west_test_port_ip', help='stcv_west_test_port_ip')
    parser.add_argument('--stcv2-mgmt-ip', action='store', dest='stcv_east_ip', help='stcv_east_ip')
    parser.add_argument('--stcv2-test-ip', action='store', dest='stcv_east_test_port_ip', help='stcv_east_test_port_ip')
    parser.add_argument('--dut-left-ip', action='store', dest='dut_left_ip', help='dut_left_ip')
    parser.add_argument('--dut-right-ip', action='store', dest='dut_right_ip', help='dut_right_ip')
    args = parser.parse_args()


    test = SimpleTrafficTest(labserver_ip = args.labserver_ip,
                             user_name = args.username,
                             stcv_west_mgmt_ip = args.stcv_west_ip,
                             stcv_west_test_port_ip = args.stcv_west_test_port_ip,
                             stcv_east_mgmt_ip = args.stcv_east_ip,
                             stcv_east_test_port_ip = args.stcv_east_test_port_ip,
                             dut_left_ip = args.dut_left_ip,
                             dut_right_ip = args.dut_right_ip)
    testresult = {}
    try:
        testresult = test.run()
    except Exception as e:
        logger.debug(e)
        traceback.print_exc()
    finally:
        with open(args.resultjson, "w") as f:
            f.write(json.dumps(testresult, default=lambda x: x.__dict__))
