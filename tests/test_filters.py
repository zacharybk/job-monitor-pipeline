import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.filters import is_relevant


def test_customer_success_remote_passes():
    assert is_relevant("Head of Customer Success", "Remote, US") is True

def test_vp_cx_passes():
    assert is_relevant("VP of CX", "San Francisco, CA") is True

def test_support_director_passes():
    assert is_relevant("Director of Support", "Remote") is True

def test_software_engineer_fails():
    assert is_relevant("Senior Software Engineer", "Remote, US") is False

def test_marketing_manager_fails():
    assert is_relevant("Marketing Manager", "Remote") is False

def test_hr_excluded():
    assert is_relevant("Employee Experience Manager", "Remote, US") is False

def test_uk_location_fails():
    assert is_relevant("Head of Customer Success", "London, UK") is False

def test_remote_no_country_passes():
    assert is_relevant("Customer Operations Lead", "Remote") is True

def test_cx_with_seniority_passes():
    assert is_relevant("CX Manager", "Austin, TX") is True

def test_empty_location_passes():
    assert is_relevant("Head of Support", "") is True

def test_sdr_fails():
    assert is_relevant("SDR Manager", "Remote, US") is False

def test_talent_acquisition_fails():
    assert is_relevant("Talent Acquisition Specialist", "Remote") is False

def test_canada_fails():
    assert is_relevant("Director of Customer Success", "Toronto, Canada") is False

def test_account_management_passes():
    assert is_relevant("Director of Account Management", "Remote, US") is True

def test_client_success_passes():
    assert is_relevant("Client Success Manager", "Remote") is True
