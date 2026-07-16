# This is for declaring static getters (properties). @classmethod + @property stopped working on python after 3.12 version
class class_property:
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, owner):
        return self.fget(owner)