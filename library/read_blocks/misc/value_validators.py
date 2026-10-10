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


class _Comparison(ValueValidator):
    # `condition` of `value` against `self.value`, e.g. '<='
    condition: str
    type_name: str

    def __init__(self, value):
        self.value = value

    def schema(self):
        return {'type': self.type_name, 'value': self.value}

    # for documentation, without the "Always" of `__str__`
    def condition_str(self) -> str:
        return f'{self.condition} {self.value}'

    def __str__(self) -> str:
        return f'Always {self.condition_str()}'


class Lt(_Comparison):
    condition = '<'
    type_name = 'lt'

    def validate(self, value):
        return value < self.value

    def new_data(self):
        return 0 if 0 < self.value else self.value - 1


class Lte(_Comparison):
    condition = '<='
    type_name = 'lte'

    def validate(self, value):
        return value <= self.value

    def new_data(self):
        return min(0, self.value)


class Gt(_Comparison):
    condition = '>'
    type_name = 'gt'

    def validate(self, value):
        return value > self.value

    def new_data(self):
        return 0 if 0 > self.value else self.value + 1


class Gte(_Comparison):
    condition = '>='
    type_name = 'gte'

    def validate(self, value):
        return value >= self.value

    def new_data(self):
        return max(0, self.value)


class And(ValueValidator):
    def __init__(self, *validators: ValueValidator):
        self.validators = validators

    def validate(self, value):
        return all(v.validate(value) for v in self.validators)

    def new_data(self):
        for v in self.validators:
            value = v.new_data()
            if self.validate(value):
                return value
        raise ValueError(f'No value satisfies "{self}"')

    def schema(self):
        return {'type': 'and', 'validators': [v.schema() for v in self.validators]}

    def __str__(self) -> str:
        if all(isinstance(v, _Comparison) for v in self.validators):
            return 'Always ' + ' and '.join(v.condition_str() for v in self.validators)
        return ' and '.join(f'({v})' for v in self.validators)
