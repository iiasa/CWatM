rem coverage run -m pytest test_cwatm3.py --html=report111220.html --settingsfile=test_py_cwatm2.txt --cwatm=C:/GitHub/CWATM_priv/run_cwatm.py
rem coverage html

pytest test_cwatm3.py --cov-report=xml --cov=cwatm tests/  --html=pytest_report_cwatm.html --settingsfile=cwatm_pytests_settings.txt --cwatm=C:/GitHub/CWATM_priv/run_cwatm.py
pause