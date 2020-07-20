from enum import Enum


class AccessStatus(Enum):
    success = 'success'
    fail = 'fail'

    def __eq__(self, other):
        return self.value == other

    def __str__(self):
        return self.value
