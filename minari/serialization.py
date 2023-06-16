from __future__ import annotations
from collections import defaultdict

import json
from typing import Callable, Dict, Union
from functools import singledispatch

from gymnasium import spaces
import numpy as np


@singledispatch
def serialize_space(space: spaces.Space, to_string=True) -> Union[Dict, str]:
    raise NotImplementedError(f"No serialization method available for {space}")

@serialize_space.register(spaces.Box)
def _serialize_box(space: spaces.Box, to_string=True) -> Union[Dict, str]:
    result = {}
    result["type"] = "Box"
    result["dtype"] = str(space.dtype)
    result["shape"] = list(space.shape)
    # we have to use python float type to serialze the np.float32 types
    result["low"] = space.low.tolist()
    result["high"] = space.high.tolist()

    if to_string:
        result = json.dumps(result)
    return result

@serialize_space.register(spaces.Discrete)
def _serialize_discrete(space: spaces.Discrete, to_string=True) -> Union[Dict, str]:
    result = {}
    result["type"] = "Discrete"
    result["dtype"] = "int64"  # this seems to be hardcoded in Gymnasium
    # we need to cast from np.int64 to python's int type in order to serialize
    result["start"] = int(space.start)  
    result["n"] = int(space.n)

    if to_string:
        result = json.dumps(result)
    return result

@serialize_space.register(spaces.Dict)
def _serialize_discrete(space: spaces.Dict, to_string=True) -> Union[Dict, str]:
    result = {"type": "Dict", "subspaces": {}}
    for key in space.spaces.keys():
        result["subspaces"][key] = serialize_space(
            space.spaces[key], to_string=False
        )

    if to_string:
        result = json.dumps(result)
    return result

@serialize_space.register(spaces.Tuple)
def _serialize_discrete(space: spaces.Tuple, to_string=True) -> Union[Dict, str]:
    result = {"type": "Tuple", "subspaces": []}
    for subspace in space.spaces:
        result["subspaces"].append(serialize_space(subspace, to_string=False))

    if to_string:
        return json.dumps(result)
    else:
        return result


class type_value_dispatch:

    def __init__(self, func) -> None:
        self.registry = defaultdict(func)

    def register(self, type: str):
        def decorator(method):
            self.registry[type] = method
            return method

        return decorator
    
    def __call__(self, space_dict: Union[Dict, str]) -> spaces.Space:
        if not isinstance(space_dict, Dict):
            space_dict = json.loads(space_dict)
        
        assert isinstance(space_dict, Dict)
        return self.registry[space_dict["type"]](space_dict)


@type_value_dispatch
def deserialize_space(space_dict: Dict) -> spaces.Space:
    raise NotImplementedError(f"No deserialization method available for {space_dict['type']}")

@deserialize_space.register("Tuple")
def _deserialize_tuple(space_dict: Dict) -> spaces.Tuple:
    assert space_dict["type"] == "Tuple"
    subspaces = tuple(deserialize_space(subspace) for subspace in space_dict["subspaces"])
    return spaces.Tuple(subspaces)

@deserialize_space.register("Dict")
def _deserialize_dict(space_dict: Dict) -> spaces.Dict:
    assert space_dict["type"] == "Dict"        
    subspaces = {
            key: deserialize_space(space_dict["subspaces"][key])
            for key in space_dict["subspaces"]
        }
    return spaces.Dict(subspaces)

@deserialize_space.register("Box")
def _deserialize_box(space_dict: Dict) -> spaces.Box:
    assert space_dict["type"] == "Box"   
    shape = tuple(space_dict["shape"])
    low = np.array(space_dict["low"])
    high = np.array(space_dict["high"])
    dtype = np.dtype(space_dict["dtype"])
    return spaces.Box(low=low, high=high, shape=shape, dtype=dtype)  # type: ignore

@deserialize_space.register("Discrete")
def _deserialize_discrete(space_dict: Dict) -> spaces.Discrete:
    assert space_dict["type"] == "Discrete"  
    n = space_dict["n"]
    start = space_dict["start"]
    return spaces.Discrete(n=n, start=start)
