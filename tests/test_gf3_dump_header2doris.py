import os
from typing import Dict
import pytest
from bin import gf3_dump_header2doris as gf3hdr

# alos2_dump_header2doris.py metafile > meta.res
# check if exists meta.res


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            "/home/yuxiao/Data/gf3/sm/GF3_KAS_FSI_003770_E116.3_N39.8_20170428_L1A_HHHV_L10002332082",
            "GF3_KAS_FSI_003770_E116.3_N39.8_20170428_L1A_HHHV_L10002332082.meta.xml",
        )
    ],
)
def test_locate_file(input: str, expected: str):
    sm_test_dir = "/home/yuxiao/Data/gf3/sm/GF3_KAS_FSI_003770_E116.3_N39.8_20170428_L1A_HHHV_L10002332082"
    gf3_meta = gf3hdr.GF3()
    gf3_meta.locate_meta(sm_test_dir)
    output = gf3_meta.meta['path']
    expected = os.path.join(input, expected)
    assert output == expected


def test_read_meta(input: str, expected: Dict):
    pass
