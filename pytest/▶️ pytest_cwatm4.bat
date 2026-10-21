P:/watmodel/Python312/python.exe -m pytest test_cwatm4.py --verbose --html=pytest_report_cwatm_04.html --settingsfile=cwatm_pytests_settings4.ini --cwatm=../run_cwatm.py --cov-report=xml --cov=cwatm --cov-branch
rem coverage.xml: file paths relative to the repository root (cwatm/...) for Codecov
P:/watmodel/Python312/python.exe fix_coverage_paths.py coverage.xml
pause
