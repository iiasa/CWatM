rem coverage run -m pytest test_cwatm3.py --html=report111220.html --settingsfile=test_py_cwatm2.txt --cwatm=C:/work/CWATM/run_cwatm.py
rem coverage html

pytest test_cwatm3.py --cov-report=xml --cov=cwatm tests/  --html=report111220.html --settingsfile=test_py_cwatm2.txt --cwatm=C:/work/CWATM/run_cwatm.py

pause

rem https://coverage.readthedocs.io/en/coverage-5.3/