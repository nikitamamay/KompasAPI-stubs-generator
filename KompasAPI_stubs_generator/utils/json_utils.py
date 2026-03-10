import typing
import json


CLASS_NAME_KEY = "CLASS_NAME"


def construct_class_dict(classes: list):
    class_names = {}
    for c in classes:
        class_names[c.__name__] = c
    return class_names


class JSONable:
    def to_json_base(self):
        return { CLASS_NAME_KEY: self.__class__.__name__ }

    def to_json(self) -> dict:
        d = self.to_json_base()
        v = vars(self).copy()
        for key in v:
            if not key.startswith("_"):
                d[key] = v[key]
        return d

    def from_json_base(self, d: dict):
        if CLASS_NAME_KEY in d:
            del d[CLASS_NAME_KEY]
        for key in d:
            vars(self)[key] = d[key]

    @staticmethod
    def from_json(d: dict):
        raise NotImplementedError("JSONable.from_json(dict) is not implemented. Did you forget to reimplement it in derived class?")

    @staticmethod
    def encode(obj):
        if isinstance(obj, JSONable):
            return obj.to_json()
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

    @staticmethod
    def check_dict(obj):
        return isinstance(obj, dict) and CLASS_NAME_KEY in obj


### ----- DECODERS -----


def decoder_classes(general: list, special: list = []):
    class_names = construct_class_dict(general + special)

    def decode(obj):
        if JSONable.check_dict(obj) \
                and obj[CLASS_NAME_KEY] in class_names:
            class_name = class_names[obj[CLASS_NAME_KEY]]
            # Decoding nested objects
            for key in obj:
                if key == CLASS_NAME_KEY: continue
                obj[key] = decode(obj[key])
            # Special
            if class_name in special:
                return class_name.from_json(obj)
            # General
            else:
                result: JSONable = class_names[obj[CLASS_NAME_KEY]]()
                result.from_json_base(obj)
                return result
        return obj

    return decode


def mix_decoders(*decoders: typing.Callable[[object], typing.Any]):
    def decode(obj):
        old_type = type(obj)
        for f in decoders:
            obj = f(obj)
            if type(obj) != old_type:
                break
        return obj
    return decode


### ----- FILE INTERFACE -----


def save_json(path: str, target: object) -> int:
    """
    Decodes object `target` and saves its JSON to file `path`.

    Automatically uses `JSONable.to_json()`.

    Returns written bytes count.
    """
    s = bytes(json.dumps(target, default=JSONable.encode, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(path, "wb") as f:
        size = f.write(s)
    return size

def load_json(path: str, object_hook: typing.Callable[[object], typing.Any]):
    """
    Loads JSON from file `path` and uses custom `object_hook`.
    """
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f, object_hook=object_hook)
    return obj


def load_json_with_classes(path: str, general: list = [], special: list = []):
    """
    Loads JSON from file `path` and constructs JSONable objects.
    * for `general` classes uses `JSONable.from_json_base()`;
    * for `special` classes uses `special[i].from_json()` (`from_json()` must be reimplemented in derived class of JSONable).
    """
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f, object_hook=decoder_classes(general, special))
    return obj



if __name__ == "__main__":
    def _example():
        class A(JSONable):
            """
            Class of objects that can be constructed without passing arguments to `__init__()`.

            This is **general** class in terms of `load_json_with_classes()`.
            """
            def __init__(self, i = 0) -> None:
                super().__init__()
                self.i = i
                self.x = 20
                self.y = ["hey", "bye"]

            def __repr__(self) -> str:
                return f"<A i={self.i}, x={self.x}, y={self.y}>"

        class B(JSONable):
            """
            Class that requires passing arguments to `__init__()` on object construction.

            Must reimplement `from_json()`.

            This is **special** class in terms of `load_json_with_classes()`.
            """
            def __init__(self, a) -> None:
                super().__init__()
                self.z = [A(), 20, "qwerty"]
                self.a = a
                self._arr = []

            def foo(self):
                for i in range(self.a):
                    self._arr.append(A(i))

            def __repr__(self) -> str:
                return f"<B z={self.z}, a={self.a}, _arr={self._arr}>"

            def to_json(self) -> dict:
                d = super().to_json()
                d["arr"] = self._arr
                return d

            @staticmethod
            def from_json(d: dict):
                b = B(d["a"])
                for el in d["arr"]:
                    b._arr.append(el)
                return b

        a = A()
        b = B(3)

        b.foo()

        d = {
            "a_general": a,
            "b_special": b,
            "basic_int": 10,
            "basic_str": "word",
            "list_with_general_and_special_classes": ["a", A(15), "b", B(2)],
        }

        save_json("test.json", d)


        dd = load_json_with_classes("test.json", [A], [B])

        print(f"dict after load: dd = {{")
        for key, value in dd.items():
            print(f"\t{repr(key)}: {repr(value)},")
        print(f"}}")
        print(f"object A = {dd['a_general']}")
        print(f"object B = {dd['b_special']}")


    _example()
