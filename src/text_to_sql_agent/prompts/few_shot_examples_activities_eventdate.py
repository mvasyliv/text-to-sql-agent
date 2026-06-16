"""Few-shot examples for the activities_eventdate table."""

from __future__ import annotations

from .few_shot_models import FewShotExample


_SQLITE_ACTIVITY_TABLE = ("activities_eventdate",)


SQLITE_ACTIVITIES_EVENTDATE_EXAMPLES: tuple[FewShotExample, ...] = (
    FewShotExample(
        input="Get activities for country UA.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE (countrycode = 'UA' OR countrycodegeo = 'UA');"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get userid from activities for country US.",
        query=(
            "SELECT userid FROM activities_eventdate "
            "WHERE (countrycode = 'US' OR countrycodegeo = 'US');"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities for countries UA, US",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE (countrycode IN ('UA', 'US') OR countrycodegeo IN ('UA', 'US'));"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get userid from activities for countries UA, US",
        query=(
            "SELECT userid FROM activities_eventdate "
            "WHERE (countrycode IN ('UA', 'US') OR countrycodegeo IN ('UA', 'US'));"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities for verticals 1,2,3,4,5",
        query="SELECT * FROM activities_eventdate WHERE verticalid IN (1,2,3,4,5);",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities for isps 2, 3",
        query="SELECT * FROM activities_eventdate WHERE ispid IN (2,3);",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities for entered from 1609477200 to 1640581200",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE dtentered >= 1609477200 AND dtentered <= 1640581200;"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities for entered from 1992-09-25 to 2024-09-25",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE dtentered >= strftime('%s', '1992-09-25') "
            "AND dtentered <= strftime('%s', '2024-09-25');"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by id.",
        query="SELECT * FROM activities_eventdate WHERE id = 123;",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by activity_id.",
        query="SELECT * FROM activities_eventdate WHERE activity_id = 456;",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by exact event date.",
        query="SELECT * FROM activities_eventdate WHERE eventdate = '2024-12-01';",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by event date range.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE eventdate BETWEEN '2024-01-01' AND '2024-12-31';"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get userid from activities for state CA.",
        query=(
            "SELECT userid FROM activities_eventdate "
            "WHERE (statecode = 'CA' OR statecodegeo = 'CA') LIMIT 10;"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get userid from activities for city New York.",
        query=(
            "SELECT userid FROM activities_eventdate "
            "WHERE (city = 'New York' OR citygeo = 'New York') LIMIT 10;"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by region.",
        query="SELECT * FROM activities_eventdate WHERE region = 'Kyivska';",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by city.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE (city = 'Kyiv' OR citygeo = 'Kyiv');"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by latitude/longitude bounding box.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE latitude BETWEEN 49.0 AND 50.0 "
            "AND longitude BETWEEN 30.0 AND 31.0;"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by activity type.",
        query="SELECT * FROM activities_eventdate WHERE activitytype = 'webinar';",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by activity name contains 'conference'.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE LOWER(activityname) LIKE '%conference%';"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities by source.",
        query="SELECT * FROM activities_eventdate WHERE source = 'external';",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities created in a date range.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE created_at BETWEEN '2024-01-01' AND '2024-06-30';"
        ),
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
    FewShotExample(
        input="Get activities updated after a date.",
        query="SELECT * FROM activities_eventdate WHERE updated_at >= '2024-12-01';",
        tables=_SQLITE_ACTIVITY_TABLE,
    ),
)

