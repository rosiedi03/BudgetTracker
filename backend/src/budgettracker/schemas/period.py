"""Year and month parameters for endpoints that report on one calendar month."""

from typing import Annotated

from pydantic import Field

# Usable as query or path parameters. Out-of-range or non-integer values are rejected with a 422.
Year = Annotated[int, Field(ge=2000, le=2100)]
Month = Annotated[int, Field(ge=1, le=12)]
