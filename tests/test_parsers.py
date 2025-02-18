from ..utils import parsers

def test_parse_kinds_valid():
    assert parsers.parse_kinds("1,2,3") == [1, 2, 3]

def test_parse_kinds_invalid():
    assert parsers.parse_kinds("1,a,3") == [1, 3]

def test_parse_kinds_list():
    assert parsers.parse_kinds([1, 2, 3]) == [1, 2, 3]
