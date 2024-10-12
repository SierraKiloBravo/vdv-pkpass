import dataclasses
import datetime
import pytz

class UICException(Exception):
    pass

@dataclasses.dataclass
class Timestamp:
    year: int
    month: int
    day: int
    hour: int
    minute: int

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}"

    def as_datetime(self):
        return pytz.utc.localize(datetime.datetime(self.year, self.month, self.day, self.hour, self.minute, 0))

    @classmethod
    def from_bytes(cls, data: bytes) -> "Timestamp":
        try:
            timestamp = data.decode("ascii")
            day = int(timestamp[0:2], 10)
            month = int(timestamp[2:4], 10)
            year = int(timestamp[4:8], 10)
            hour = int(timestamp[8:10], 10)
            minute = int(timestamp[10:12], 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise UICException("Invalid UIC ticket timestamp") from e

        return cls(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute
        )

def nul_and_space_bidi_strip(input_str: str) -> str:
    return input_str.lstrip().lstrip("\0").rstrip().rstrip("\0")

def replace_substring(input_str: str, replace_at_idx: int, string_to_insert: str) -> str:
    """Replaces a substring of a string with another string.
    Useful for rendering ticket layouts.
    """

    if replace_at_idx > (len(input_str) - 1):
        raise ValueError("Point to replace string at is out of bounds")
    if (replace_at_idx + len(string_to_insert)) > (len(input_str) - 1):
        raise ValueError("String to insert is out of bounds of input string")
    
    input_str_before = input_str[:replace_at_idx]
    input_str_after = input_str[replace_at_idx+len(string_to_insert):]
    output_str = input_str_before + string_to_insert + input_str_after

    assert len(output_str) == len(input_str)

    return output_str