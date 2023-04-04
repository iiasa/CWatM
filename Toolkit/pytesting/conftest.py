# conftest.py

from py.xml import html
import pytest
import collections

import sys,os
import importlib


def pytest_addoption(parser):
    parser.addoption("--settingsfile", action="store")
    parser.addoption("--cwatm", action="store")

# HTML
def pytest_configure(config):
    a = config._metadata
    try:
        a.__delitem__('Plugins')
        a.__delitem__('Packages')
        runcwatm = config.option.cwatm
        path = os.path.dirname(runcwatm)
        cwatm = os.path.basename(runcwatm).split(".")[0]
        sys.path.append(path)
        run_cwatm = importlib.import_module(cwatm, package=None)
        authors = run_cwatm.__author__
        version = run_cwatm.__version__
        date = run_cwatm.__date__

    except:
        runcwatm = "../run_cwatm.py"
        authors = ""
        version = ""
        date = ""

    a['CWatM folder'] = runcwatm
    a['CWatM author'] = authors
    a['CWatM version'] = version
    a['CWatM date'] = date
    a['Settingsfile'] = config.option.settingsfile
    a['PyTest'] = config.option.file_or_dir
    a['Report'] = config.option.htmlpath
    config._metadata = collections.OrderedDict(a)
    #config._metadata = None
    #config.getoption('cwatm')
    #config.option

#@pytest.mark.optionalhook
#def pytest_html_results_summary(prefix, summary, postfix):
#    prefix.extend([html.p("CWatM: Hydrological Model")])


@pytest.mark.optionalhook
def pytest_html_report_title(report):
   report.title = "CWatM pytest report"




@pytest.mark.optionalhook
def pytest_html_results_table_header(cells):
    #cells.append(html.th('Server Name'))
    cells.remove(cells[3])

@pytest.mark.optionalhook
def pytest_html_results_table_row(report, cells):
    a = cells[3]
    cells.remove(a)
    #cells.append(html.td(report.server_name))

@pytest.mark.hookwrapper
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.server_name = item.function.__doc__

"""
def pytest_html_results_table_header(cells):
    cells.insert(2, html.th('Description'))
    cells.insert(1, html.th('Time', class_='sortable time', col='time'))
    cells.pop()

def pytest_html_results_table_row(report, cells):
    cells.insert(2, html.td(report.description))
    cells.insert(1, html.td(datetime.utcnow(), class_='col-time'))
    cells.pop()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.description = str(item.function.__doc__)

#@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin('html')
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, 'extra', [])
    if report.when == 'call':
        # always add url to report
        extra.append(pytest_html.extras.url('https://cwatm.iiasa.ac.at/'))
        #xfail = hasattr(report, 'wasxfail')
        #if (report.skipped and xfail) or (report.failed and not xfail):
        #    # only add additional html on failure
        extra.append(pytest_html.extras.html('<div>Additional HTML</div>'))
        report.extra = extra
"""