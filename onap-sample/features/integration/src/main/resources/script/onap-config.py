#!/usr/bin/python
#
# Copyright (c) 2020, CMCC Technologies Co., Ltd.
# <p>
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# <p>
# http://www.apache.org/licenses/LICENSE-2.0
# <p>
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import json
import uuid
from argparse import RawTextHelpFormatter


class Config(object):
    """
    This script uses the ONAP CLI for providing the common configurations.
    """

    def __init__(self, file_path, paras={}):
        self.paras = paras
        self.file_name = str(uuid.uuid1()) + ".json"
        self.file_path = file_path + "/data/profiles/" + self.file_name

    def run(self):
        with open(self.file_path, 'w+') as file:
            json.dump(self.paras, file, sort_keys=True, indent=2)

    def __str__(self):
        return str(vars(self))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ONAP configuration using ONAP CLI and Open Command Platform (OCOMP)",
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('--vim', action='store', dest='vim', help='Json string for vim')
    parser.add_argument('--vnfm', action='store', dest='vnfm', help='Json string for vnfm')
    parser.add_argument('--conf', action='store', dest='config_file_path', help='Configuration file path')
    parser.add_argument('--result-json', action='store', dest='result', help='Result json file.')
    args = parser.parse_args()
    print(args)

    try:
        data = {}
        if args.vim:
            for key, value in json.loads(args.vim).items():
                data[key] = value

        if args.vnfm:
            for key, value in json.loads(args.vnfm).items():
                data[key] = value

        result_file = args.result if args.result else None

        conf = Config(args.config_file_path, data)
        conf.run()
    finally:
        onap_result = json.dumps(conf, default=lambda x: x.__dict__)
        print(onap_result)

        if result_file:
            with open(result_file, "w+") as f:
                f.write(onap_result)
