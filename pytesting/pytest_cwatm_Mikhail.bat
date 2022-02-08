call workon iiasa
rem coverage run -m pytest test_cwatm3.py --html=report111220.html --settingsfile=test_py_cwatm2.txt --cwatm=C:/GitHub/CWATM_priv/run_cwatm.py
rem coverage html

rem pytest test_cwatm3.py --html=C:/work/CWATM/report1.html --settingsfile=test_py_cwatm2.txt --cwatm=C:/GitHub/CWATM_priv/run_cwatm.py


pytest test_cwatm3.py --cov-report=xml --cov=cwatm tests/  --html=testingReport.html --settingsfile=test_py_cwatm2.txt --cwatm=C:/GitHub/CWATM_priv/run_cwatm.py

rem pytest test_cwatm3.py --html=report14062021.html --settingsfile=test_py_cwatm2.txt --cwatm=C:/work/CWATM_priv/run_cwatm.py

pause

rem https://coverage.readthedocs.io/en/coverage-5.3/
rem pytest test_cwatm3.py --cov-report=xml --cov=cwatm tests/  --html=report14062021.html --settingsfile=test_py_cwatm5.txt --cwatm=C:/work/CWATM/run_cwatm.py
rem pytest test_cwatm3.py --cov-report=xml --cov=cwatm tests/  --html=report14062021.html --settingsfile=test_py_cwatm5.txt --cwatm=C:/work/CWATM_public/run_cwatm.py
