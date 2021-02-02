import pytest

from smashtheque.helpers.map import *

# class Map(UserDict):
#   def __getattr__(self, attr):
#     val = self.data[attr]
#     if isinstance(val, Mapping):
#         return Map(val)
#     return val

@pytest.mark.parametrize("test_object,test_expression", [
  (None, "True"),
  ({"a": True}, "m.a"),
  ({"a": {"b": True}}, "m.a.b"),
  ({"a": [False, True]}, "m.a[1]"),
])
def test_is_discord_id(test_object, test_expression):
  m = Map(test_object)
  assert eval(test_expression)
