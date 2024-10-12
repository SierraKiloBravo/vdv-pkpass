import dataclasses
import typing
import re

from . import util

class LayoutV1FieldFormatting:
    def __init__(self, formatting: int):
        self.formatting = formatting

    @property
    def bold(self) -> bool:
        return bool(self.formatting & 1)

    @property
    def italic(self) -> bool:
        return bool(self.formatting & 2)

    @property
    def small_font(self) -> bool:
        return bool(self.formatting & 4)

    def __str__(self):
        return f"LayoutV1FieldFormatting(bold={self.bold}, italic={self.italic}, small_font={self.small_font})"

    def __repr__(self):
        return str(self)

class RCT2Layout():
    """Refer to ERA TSI TD B.12 'DIGITAL SECURITY ELEMENTS FOR RAIL PASSENGER TICKETING'
    Section '10.4.1.1. Extraction of RCT 2 zones'

    Everything apart from the boxes defined in the TSI is optional.
    This place is not a place of honor, no highly esteemed deed is commemorated here, nothing valued is here. 
    """
    typeOfDocumentBox: str
    namesOfTravelersBox: str
    trainWagonSeatBox: str
    ratesAndConditionsBox: str
    ticketValueBox: str
    
    travelFrom: str
    travelTo: str
    departureDate: str
    departureTime: str
    travelClass: int
    arrivalDate: str
    arrivalTime: str
    # I am prepared to take the L here - there are two lines for defining itineraries
    # but I have never seen more than one on the same ticket

    ticketValue: typing.Optional[int] # in cents or equivalent smallest fractions
    ticketCurrency: typing.Optional[str] # ISO currency code
    trainType: typing.Optional[str] # as defined in the 2nd line, i.e. 'Railjet Xpress', 'ICE', etc...
    trainNumber: typing.Optional[int]
    carriageNumber: typing.Optional[int]
    seatNumber: typing.Optional[int]
    nameOfTraveller: typing.Optional[str] # only use if a name is known with no specification of first/last name
    firstNameOfTraveller: typing.Optional[str]
    lastNameOfTraveller: typing.Optional[str]
    honorificOfTraveller: typing.Optional[str] # Mr, Dr, Mx, Prof.Dr.Ing. whatever
    seatType: typing.Optional[str] # grossraum, am fenster, couchette, etc
    ticketType: typing.Optional[str] # use that as pass title when available, I suppose?

    def __init__(self, text_body: typing.List[str]):
        """
        expects a list of strings representing a RCT2 layout with \0 being blank/undefined cells
        see LayoutV1.parse
        __init__ only parses the 'boxes' as per the TSI, an actual attempt at getting useful data
        is in parse()
        """
        self.typeOfDocumentBox = [x[18:51] for x in text_body[0:4]]
        self.namesOfTravelersBox = [x[52:71] for x in text_body[0:2]]
        self.trainWagonSeatBox = [x[1:-1] for x in text_body[8:12]]
        self.ratesAndConditionsBox = [x[1:50] for x in text_body[12:15]]
        self.ticketValueBox = [x[52:71] for x in text_body[13:15]]
        self.parse(text_body)
                # TODO: this probably only should be done when there's no alternative, i.e. no flex data
        return


    def parse(self, text_body):
        """This one _should_ be tested against Benerail (NS/SNCB International), NS domestic, OeBB reservations
        Those ones tend to only have RCT2 data and are the most relevant
        """
        for x in [5,6]:
            # afaict there are currently no issuers that have two itineraries on one ticket
            # one of the two lines just consists of asterisks
            travelFrom = util.nul_and_space_bidi_strip(text_body[x][13:31])
            if travelFrom != '*':
                self.travelFrom = travelFrom

            travelTo = util.nul_and_space_bidi_strip(text_body[x][34:52])
            if travelTo != '*':
                self.travelTo = travelTo

            departureDate = util.nul_and_space_bidi_strip(text_body[x][1:6])
            if departureDate:
                self.departureDate = departureDate

            departureTime = util.nul_and_space_bidi_strip(text_body[x][7:12])
            if departureTime:
                self.departureTime = departureTime

            arrivalDate = util.nul_and_space_bidi_strip(text_body[x][52:57])
            if arrivalDate:
                self.arrivalDate = arrivalDate

            arrivalTime = util.nul_and_space_bidi_strip(text_body[x][58:63])
            if arrivalTime:
                self.arrivalTime = arrivalTime
        
        self.travelClass = int(util.nul_and_space_bidi_strip(text_body[6][67:72]))

        seatNumber = util.nul_and_space_bidi_strip(self.trainWagonSeatBox[2][60:64])
        if seatNumber:
            self.seatNumber = int(seatNumber)

        self.ticketType = util.nul_and_space_bidi_strip(self.typeOfDocumentBox[0])

        trainType = util.nul_and_space_bidi_strip(self.typeOfDocumentBox[1])
        if trainType:
            self.trainType = trainType
        
        try:
            # OeBB
            self.trainNumber, self.carriageNumber = re.search(r"^ZUG (\d+).*WAGEN\s+(\d+)", self.trainWagonSeatBox[0]).groups()
        except AttributeError:
            pass
            
        seatType = util.nul_and_space_bidi_strip(self.trainWagonSeatBox[1][60:])
        if seatType:
            seatType = seatType

        try:
            # OeBB
            self.ticketCurrency, euros, cents = re.search(r"^PREIS\s+(EUR) (\d+),(\d+)$", self.ticketValueBox[0]).groups()
            self.ticketValue = int(euros + cents)
        except AttributeError:
            pass
        
        try:
            # NS national, apparently they use a separate layout element for currency and amount so we can't use \s as there would be a NUL byte between currency and value
            self.ticketCurrency, euros, cents = re.search(r"(EUR)\x00(\d+).(\d+)", self.ticketValueBox[0]).groups()
            self.ticketValue = int(euros + cents)
        except AttributeError:
            pass

        nameOfTraveller = util.nul_and_space_bidi_strip(self.namesOfTravelersBox[0])
        if nameOfTraveller:
            self.nameOfTraveller = nameOfTraveller


@dataclasses.dataclass
class LayoutV1Field:
    line: int
    column: int
    height: int
    width: int
    formatting: LayoutV1FieldFormatting
    text: str

@dataclasses.dataclass
class LayoutV1:
    standard: str
    fields: typing.List[LayoutV1Field]
    text_body: typing.List[str] # plain text, disregarding bold/italic/etc
    rct2_layout: typing.Optional[RCT2Layout]
    # will store the textual representation of the layout. 
    # that could be used when some information is only available in the layout
    # (i.e. ticket only has a paper layout)

    @classmethod
    def parse(cls, data: bytes) -> "LayoutV1":
        if len(data) < 8:
            raise util.UICException("UIC ticket layout too short")

        try:
            standard = data[0:4].decode("ascii")
        except UnicodeDecodeError as e:
            raise util.UICException("Invalid UIC ticket layout standard") from e

        try:
            field_count_str = data[4:8].decode("ascii")
            field_count = int(field_count_str, 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise util.UICException("Invalid UIC ticket layout field count") from e

        fields = []
        offset = 8
        for _ in range(field_count):
            if len(data) < offset + 13:
                raise util.UICException("UIC ticket layout field too short")

            try:
                field_line_str = data[offset:offset + 2].decode("ascii")
                field_line = int(field_line_str, 10)
                field_column_str = data[offset + 2:offset + 4].decode("ascii")
                field_column = int(field_column_str, 10)
                field_height_str = data[offset + 4:offset + 6].decode("ascii")
                field_height = int(field_height_str, 10)
                field_width_str = data[offset + 6:offset + 8].decode("ascii")
                field_width = int(field_width_str, 10)
            except (UnicodeDecodeError, ValueError) as e:
                raise util.UICException("Invalid UIC ticket layout field position") from e

            try:
                field_formatting_str = data[offset + 8:offset + 9].decode("ascii")
                field_formatting = LayoutV1FieldFormatting(int(field_formatting_str, 10))
            except (UnicodeDecodeError, ValueError) as e:
                raise util.UICException("Invalid UIC ticket layout field formatting") from e

            try:
                field_text_length_str = data[offset + 9:offset + 13].decode("ascii")
                field_text_length = int(field_text_length_str, 10)
            except (UnicodeDecodeError, ValueError) as e:
                raise util.UICException("Invalid UIC ticket layout field text length") from e

            if len(data) < offset + 13 + field_text_length:
                raise util.UICException("UIC ticket layout field text too short")

            try:
                field_text = data[offset + 13:offset + 13 + field_text_length].decode("utf-8")\
                    .replace("\\n", "\n")
            except UnicodeDecodeError as e:
                raise util.UICException("Invalid UIC ticket layout field text") from e

            offset += 13 + field_text_length

            fields.append(LayoutV1Field(
                line=field_line,
                column=field_column,
                height=field_height,
                width=field_width,
                formatting=field_formatting,
                text=field_text
            ))
        
        rct2_layout = None
        if standard == "RCT2":
            text_body = ["\0" * 72] * 15
            # insert templated text (i.e. von/nach, CIV etc)
            text_body[2] = util.replace_substring(text_body[2], 1, "CIV")
            text_body[4] = util.replace_substring(text_body[4], 1, "DATUM")
            text_body[4] = util.replace_substring(text_body[4], 7, "ZEIT")
            text_body[4] = util.replace_substring(text_body[4], 13, "VON")
            text_body[4] = util.replace_substring(text_body[4], 34, "NACH")
            text_body[4] = util.replace_substring(text_body[4], 52, "DATUM")
            text_body[4] = util.replace_substring(text_body[4], 58, "ZEIT")
            text_body[4] = util.replace_substring(text_body[4], 67, "KL.")

            for field in fields:
                text = field.text.split('\n')
                row = field.line
                for text_line in text:
                    text_body[row] = util.replace_substring(text_body[row], field.column, text_line)
                    row += 1
            
            text_body = text_body
            rct2_layout = RCT2Layout(text_body)

        return cls(
            standard=standard,
            fields=fields,
            text_body=text_body,
            rct2_layout=rct2_layout
        )