import pytest
from src.parsers.experience_parser import parse_experience
from src.parsers.projects_parser import parse_projects


def test_experience_parsing_multi_line():
    raw_exp = """
    Software Engineer | Google | Mountain View, CA
    Jan 2021 - Present
    • Built scalable low-latency ingestion pipelines in Go.
    • Decreased API response p99 from 220ms to 45ms.

    Junior Developer
    Acme Solutions
    June 2019 - Dec 2020
    - Maintained PostgreSQL cluster and wrote Django services.
    """
    records = parse_experience(raw_exp)
    assert len(records) == 2

    assert records[0].title == "Software Engineer"
    assert records[0].company == "Google"
    assert records[0].is_current is True
    assert len(records[0].highlights) == 2

    assert records[1].title == "Junior Developer"
    assert records[1].company == "Acme Solutions"
    assert records[1].start_date == "2019-06"
    assert records[1].end_date == "2020-12"


def test_projects_parsing_with_tech_stack():
    raw_proj = """
    Real-Time Chat Engine | React, WebSocket, Redis
    March 2023 - May 2023
    • Architected bidirectional streaming platform handling 10k connections.
    • Tools: Node.js, Docker, AWS EC2
    """
    projects = parse_projects(raw_proj)
    assert len(projects) == 1
    p = projects[0]
    assert p.name == "Real-Time Chat Engine"
    assert "React" in p.technologies
    assert "WebSocket" in p.technologies
    assert "Node.js" in p.technologies or "Docker" in p.technologies
    assert len(p.highlights) >= 1