# conftest.py

#from py.xml import html
#import pytest

def pytest_addoption(parser):
    parser.addoption("--settingsfile", action="store")
    parser.addoption("--cwatm", action="store")

def pytest_report_header(config):
    return "CWatM testing framework"

# HTML
def pytest_configure(config):
    config._metadata = None

