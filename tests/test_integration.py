#!/usr/bin/env python3

import pytest


pytestmark = pytest.mark.skip(reason="libdatachannel media integration test needs a native browser/peer fixture")
