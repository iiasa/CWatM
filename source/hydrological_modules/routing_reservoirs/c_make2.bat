rem C:\mingw-w64\x86_64-6.3.0-posix-seh-rt_v5-rev1\mingw64\bin\g++ -c -fPIC -Ofast tx1.cpp -o tx1.o
rem C:\mingw-w64\x86_64-6.3.0-posix-seh-rt_v5-rev1\mingw64\bin\g++ -shared -Ofast -Wl,-soname,tx1.so -o tx1.so  tx1.o
call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\amd64/vcvars64.bat"
cl /LD /O2 t5.cpp

rem c:\Python27_64\python rout1.py
pause