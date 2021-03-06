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
import os
from argparse import RawTextHelpFormatter


class Config(object):
    """
    This script uses the ONAP CLI for providing the common configurations.
    """

    def __init__(self, file_path, paras={}):
        self.paras = paras

        file_path = file_path + "/conf/tmp/"
        is_exists = os.path.exists(file_path)
        if not is_exists:
            os.makedirs(file_path)
        self.file_name = file_path + str(uuid.uuid1()) + ".json"

    def run(self):
        with open(self.file_name, 'w+') as file:
            json.dump(self.paras, file, sort_keys=True, indent=2)

    def __str__(self):
        return str(vars(self))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ONAP configuration using ONAP CLI and Open Command Platform (OCOMP)",
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('--content', action='store', dest='content', help='Json string for content')
    parser.add_argument('--conf', action='store', dest='config_file_path', help='Configuration file path')
    parser.add_argument('--result-json', action='store', dest='result', help='Result json file.')
    args = parser.parse_args()
    print(args)

    try:
        data = {}
        if args.content:
            for key, value in json.loads(args.content).items():
                data[key] = value

        result_file = args.result if args.result else None

        conf = Config(args.config_file_path, data)
        conf.run()
    finally:
        onap_result = json.dumps(conf, default=lambda x: x.__dict__)
        # print(onap_result)

        if result_file:
            with open(result_file, "w+") as f:
                f.write(onap_result)
