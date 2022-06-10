rem coverage run -m pytest test_cwatm3.py --html=report111220.html --settingsfile=test_py_cwatm2.txt --cwatm=C:/GitHub/CWATM_priv/run_cwatm.py
rem coverage html

p:/watmodel/python38/python.exe -m pytest test_cwatm3.py --cov-report=xml --cov=cwatm tests/  --html=pytest_report_cwatm38.html --settingsfile=cwatm_pytests_settings_MS.txt --cwatm=P:/watmodel/CWATM/model/FUSE/CWATM_priv/run_cwatm.py
pause