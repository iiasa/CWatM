rem C:\mingw-w64\x86_64-6.3.0-posix-seh-rt_v5-rev1\mingw64\bin\g++ -c -fPIC -Ofast tx1.cpp -o tx1.o
rem C:\mingw-w64\x86_64-6.3.0-posix-seh-rt_v5-rev1\mingw64\bin\g++ -shared -Ofast -Wl,-soname,tx1.so -o tx1.so  tx1.o
call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\amd64/vcvars64.bat"
cl /LD /O2 t5.cpp

rem c:\Python27_64\python rout1.py

rem cygwin:
rem  cd cygdrive/c/work
rem  g++ -c t4.cpp -o t4_cyg2.o
rem  g++ -shared -Wl,-soname,t4cyg.so -o t4cyg.so  t4_cyg2.o

rem python cwatm.py settings4WDFEI_Rhine2_cyg.ini -l


rem shared: Produce a shared object which can then be linked with other objects to form an executable. Not all systems support this option. For predictable results, you must also specify the same set of options used for compilation (-fpic, -fPIC, or model suboptions) when you specify this linker option.1
rem -Wl,option  Pass option as an option to the linker. If option contains commas, it is split into multiple options at the commas. You can use this syntax to pass an argument to the option. For example, -Wl,-Map,output.map passes -Map output.map to the linker. When using the GNU linker, you can also get the same effect with -Wl,-Map=output.map.

rem maybe on linux supercomputer: g++ -fPIC -c -O2 t4.cpp -o t4_cyg2.o


pause