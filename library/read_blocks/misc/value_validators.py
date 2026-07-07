from abc import ABC, abstractmethod


class ValueValidator(ABC):

    # for data validation after read
    @abstractmethod
    def validate(self, value) -> bool:
        raise NotImplementedError

    # for data generation
    @abstractmethod
    def new_data(self):
        raise NotImplementedError

    # for frontend
    @abstractmethod
    def schema(self):
        raise NotImplementedError

    # for documentation
    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    def value_to_docstring(self, value):
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, int):
            return hex(value)
        else:
            return str(value)


class Eq(ValueValidator):

    def __init__(self, expected_value):
        self.expected_value = expected_value

    def validate(self, value):
        return value == self.expected_value

    def new_data(self):
        return self.expected_value

    def schema(self):
        return {'type': 'eq', 'expected_value': self.expected_value}

    def __str__(self) -> str:
        return f'Always == {self.value_to_docstring(self.expected_value)}'


class Or(ValueValidator):

    def __init__(self, possible_values: list):
        self.possible_values = possible_values

    def validate(self, value):
        return value in self.possible_values

    def new_data(self):
        return self.possible_values[0]

    def schema(self):
        return {'type': 'or', 'possible_values': self.possible_values}

    def __str__(self) -> str:
        return f'One of {[self.value_to_docstring(x) for x in self.possible_values]}'
