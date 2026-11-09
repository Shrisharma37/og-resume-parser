"""
tests/test_education_parser.py
Unit tests verifying date range parsing and education parsing accuracy.
"""

from src.parsers.date_parser import parse_date_range
from src.parsers.education_parser import parse_education_section


def test_date_range_no_character_splitting_bug():
    """
    CRITICAL TEST: Ensures 'October 2022 to December 2026' does not split on 't' and 'o'
    into 'Oc' and 'ber'.
    """
    start, end = parse_date_range("October 2022 to December 2026")
    assert start == "Oct 2022"
    assert end == "Dec 2026"


def test_date_range_hyphens_and_present():
    start, end = parse_date_range("June 2023 - Present")
    assert start == "Jun 2023"
    assert end == "Present"

    start, end = parse_date_range("2020 – 2024")
    assert start == "2020"
    assert end == "2024"


def test_single_graduation_year():
    start, end = parse_date_range("Graduated in 2024")
    assert start is None
    assert end == "2024"


def test_education_parsing_degree_first_order():
    """Validates layout where degree is on line 1 and institution is on line 2."""
    sample_text = """
    Bachelor of Technology in Computer Science and Engineering
    LNCT Bhopal
    2022 - 2026
    CGPA: 8.5
    """
    items = parse_education_section(sample_text)
    assert len(items) == 1
    edu = items[0]
    assert edu.institution == "LNCT Bhopal"
    assert "Bachelor of Technology" in edu.degree
    assert "Computer Science" in edu.field_of_study
    assert edu.start_date == "2022"
    assert edu.end_date == "2026"
    assert edu.grade_or_gpa == "8.5"


def test_education_percentage_and_multiple_records():
    """Validates percentage extraction and multiple qualifications."""
    sample_text = """
    B.Tech in Information Technology
    Technocrats Institute of Technology
    2019 - 2023
    Grade: 8.2 / 10

    Class XII
    Delhi Public School
    2018 - 2019
    Percentage: 88.4%
    """
    items = parse_education_section(sample_text)
    assert len(items) == 2

    assert items[0].institution == "Technocrats Institute of Technology"
    assert items[0].grade_or_gpa == "8.2 / 10"

    assert items[1].institution == "Delhi Public School"
    assert "88.4" in items[1].grade_or_gpa