import pytest

@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Provides fake PDF bytes so the speed test has something to test."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 85 >>\nstream\n"
        b"BT\n/F1 12 Tf\n50 720 Td\n(Alex Mercer) Tj\n"
        b"0 -30 Td\n(WORK EXPERIENCE) Tj\n"
        b"0 -20 Td\n(Software Engineer at Acme Corp) Tj\nET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000206 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n341\n%%EOF"
    )