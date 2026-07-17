"""Few-shot examples for the optins table."""
from __future__ import annotations

from .few_shot_models import FewShotExample


_SQLITE_OPTINS_TABLE = ("optins",)

SQLITE_OPTINS_EXAMPLES: tuple[FewShotExample, ...] = (
    FewShotExample(
        input="Get optins for countries UA, US.",
        query="SELECT * FROM optins WHERE countrycode IN ('UA', 'US');",
        tables=_SQLITE_OPTINS_TABLE,
    ),
    FewShotExample(
            input="Get userid from optins for verticals 1,2,3,4,5",
            query="SELECT userid FROM optins WHERE verticalid IN (1,2,3,4,5);",
            tables=_SQLITE_OPTINS_TABLE,
    ),
    FewShotExample(
            input="Get userid and countrycode from optins",
            query="SELECT userid, countrycode FROM optins LIMIT 100;",
            tables=_SQLITE_OPTINS_TABLE,
    ),
    FewShotExample(
            input="Get userid, countrycode, gender from optins",
            query="SELECT userid, countrycode, gender FROM optins LIMIT 100;",
            tables=_SQLITE_OPTINS_TABLE,
    ),
    FewShotExample(
            input="Get optins for verticals 1,2,3,4,5",
            query="SELECT * FROM optins WHERE verticalid IN (1,2,3,4,5);",
            tables=_SQLITE_OPTINS_TABLE,
    ),
    FewShotExample(
            input="Get optins for genders m, f, u",
            query="SELECT * FROM optins WHERE gender IN ('m','f','u');",
            tables=_SQLITE_OPTINS_TABLE,
    ),
    FewShotExample(
            input="Get optins for entered from 1609477200 to 1640581200",
            query="SELECT * FROM optins WHERE dtentered >= 1609477200 AND dtentered <= 1640581200;",
            tables=_SQLITE_OPTINS_TABLE,
    ),
    FewShotExample(
            input="Get optins for entered between 1992-09-25 and 2024-09-25",
            query="SELECT * FROM optins WHERE dtentered >= strftime('%s', '1992-09-25') AND dtentered <= strftime('%s', '2024-09-25');",
            tables=_SQLITE_OPTINS_TABLE,
    ),

)
