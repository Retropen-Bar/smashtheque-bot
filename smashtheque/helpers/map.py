from collections import UserDict
from collections.abc import Mapping

class Map(UserDict):
  def __getattr__(self, attr):
    val = self.data[attr]
    if isinstance(val, Mapping):
        return Map(val)
    return val
