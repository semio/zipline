#!/usr/bin/env python
#
# Copyright 2014 Quantopian, Inc.
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

import logbook
import sys

from zipline.utils import parse_args, run_pipeline

if __name__ == "__main__":
    logbook.StderrHandler().push_application()
    parsed = parse_args(sys.argv[1:])
    run_pipeline(print_algo=True, **parsed)
    sys.exit(0)
