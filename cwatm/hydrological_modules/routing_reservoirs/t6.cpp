/* -------------------------------------------------------------------------
   t6.cpp - CWatM routing library with a level-parallel kinematic wave
            and an own, platform-independent pow()

   Successor of t5.cpp (2023):
   - all functions of the old t5.cpp are included unchanged
     (ups, dirID, repairLdd1, repairLdd2, kinematic, runoffConc)
   - new: kinematicLevels(): computes the "level" of every cell once (initialisation).
          Level 0 = cells without upstream cells (sources),
          level n = cells whose upstream cells all have a level < n.
          Cells of the same level do not depend on each other and can be
          computed at the same time.
     new: kinematicPar(): kinematic wave, the cells of one level are computed
          in parallel by nthreads threads (nthreads = self.var.nodesrouting).
          nthreads <= 1 -> sequential (same as kinematic()).

   Results of kinematicPar() are bit-identical to kinematic() of the same library,
   for any number of threads: the calculation of a cell and the summation order of
   its upstream inflow are unchanged.

   Own pow(): the routing does not call the pow() of the C runtime,
   which rounds the last digit differently on Windows, Linux, macOS and with different
   compilers. It uses an own pow() (port of musl / Arm Optimized Routines), a special
   x^0.6 for chanBeta = 0.6, and Q^(beta-1) = Q^beta / Q in the Newton iteration.
   Results are therefore the same bits with every compiler and platform (tested: zig,
   Intel icx, Microsoft cl on Windows). Compared with version 1 (C runtime pow()) the
   results differ in the last digit (relative ~1e-15).


   Build (64 bit):
     zig    :  zig c++ -shared -O2 -std=c++11 -ffp-contract=off -target x86_64-windows-gnu -o t6.dll t6.cpp
     linux  :  zig c++ -shared -fPIC -O2 -std=c++11 -ffp-contract=off -target x86_64-linux-gnu -o t6_linux.so t6.cpp
               (or g++ -shared -fPIC -O2 -std=c++11 -ffp-contract=off -pthread -o t6_linux.so t6.cpp)
     mac    :  zig c++ -shared -fPIC -O2 -std=c++11 -ffp-contract=off -target aarch64-macos -o t6_mac_arm64.so t6.cpp
               zig c++ -shared -fPIC -O2 -std=c++11 -ffp-contract=off -target x86_64-macos  -o t6_mac_x86_64.so t6.cpp
     intel  :  icx /LD /O2 /fp:precise /Qfma- /EHsc /MT t6.cpp /Fet6.dll
     msvc   :  cl /LD /O2 /fp:precise /EHsc /MT t6.cpp /Fet6.dll


   ------------------------------------------------------------------------- */

#include <math.h>
#include <stdio.h>
#include <vector>
#include <algorithm>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>

#define mmax(x, y) ((x > y) ? (x) : (y))

/* =========================================================================
   Own pow(): the same result, bit for bit, on every platform and compiler.

   The system pow() of Windows, Linux, macOS and of different compilers
   rounds the last digit slightly differently. In models that amplify tiny
   differences (e.g. Bhima) this makes results depend on the platform.

   ========================================================================= */
#if defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#elif defined(_MSC_VER)
#pragma fp_contract(off)
#endif

#include <stdint.h>
#include <string.h>

namespace ownpowlib {

static inline uint64_t asuint64(double x) { uint64_t i; memcpy(&i, &x, sizeof i); return i; }
static inline double asdouble(uint64_t i) { double x; memcpy(&x, &i, sizeof x); return x; }
static inline uint32_t top12(double x) { return (uint32_t)(asuint64(x) >> 52); }
static inline double fp_barrier(double x) { volatile double y = x; return y; }
static inline void fp_force_eval(double x) { volatile double y; y = x; (void)y; }
static inline double math_xflow(uint32_t sign, double y) { y = fp_barrier(sign ? -y : y) * y; return y; }
static inline double math_oflow(uint32_t sign) { return math_xflow(sign, asdouble(0x7000000000000000ULL)); }  /* 0x1p769  */
static inline double math_uflow(uint32_t sign) { return math_xflow(sign, asdouble(0x1000000000000000ULL)); }  /* 0x1p-767 */
static inline double math_invalid(double x) { double y = (x - x) / (x - x); return y; }

/* ---- log table: ln2hi, ln2lo, polynomial, tab[i] = {invc, logc, logctail} ---- */
static const uint64_t LOG_LN2HI = 0x3fe62e42fefa3800ULL;
static const uint64_t LOG_LN2LO = 0x3d2ef35793c76730ULL;
static const uint64_t LOG_POLY[7] = {0xbfe0000000000000ULL, 0xbfe5555555555560ULL, 0x3fe0000000000006ULL, 0x3fe999999959554eULL, 0xbfe555555529a47aULL, 0xbff2495b9b4845e9ULL, 0x3ff0002b8b263fc3ULL};
static const uint64_t LOG_TAB[128][3] = {
    {0x3ff6a00000000000ULL, 0xbfd62c82f2b9c800ULL, 0x3cfab42428375680ULL},
    {0x3ff6800000000000ULL, 0xbfd5d1bdbf580800ULL, 0xbd1ca508d8e0f720ULL},
    {0x3ff6600000000000ULL, 0xbfd5767717455800ULL, 0xbd2362a4d5b6506dULL},
    {0x3ff6400000000000ULL, 0xbfd51aad872df800ULL, 0xbce684e49eb067d5ULL},
    {0x3ff6200000000000ULL, 0xbfd4be5f95777800ULL, 0xbd041b6993293ee0ULL},
    {0x3ff6000000000000ULL, 0xbfd4618bc21c6000ULL, 0x3d13d82f484c84ccULL},
    {0x3ff5e00000000000ULL, 0xbfd404308686a800ULL, 0x3cdc42f3ed820b3aULL},
    {0x3ff5c00000000000ULL, 0xbfd3a64c55694800ULL, 0x3d20b1c686519460ULL},
    {0x3ff5a00000000000ULL, 0xbfd347dd9a988000ULL, 0x3d25594dd4c58092ULL},
    {0x3ff5800000000000ULL, 0xbfd2e8e2bae12000ULL, 0x3d267b1e99b72bd8ULL},
    {0x3ff5600000000000ULL, 0xbfd2895a13de8800ULL, 0x3d15ca14b6cfb03fULL},
    {0x3ff5600000000000ULL, 0xbfd2895a13de8800ULL, 0x3d15ca14b6cfb03fULL},
    {0x3ff5400000000000ULL, 0xbfd22941fbcf7800ULL, 0xbd165a242853da76ULL},
    {0x3ff5200000000000ULL, 0xbfd1c898c1699800ULL, 0xbd1fafbc68e75404ULL},
    {0x3ff5000000000000ULL, 0xbfd1675cababa800ULL, 0x3d1f1fc63382a8f0ULL},
    {0x3ff4e00000000000ULL, 0xbfd1058bf9ae4800ULL, 0xbd26a8c4fd055a66ULL},
    {0x3ff4c00000000000ULL, 0xbfd0a324e2739000ULL, 0xbd0c6bee7ef4030eULL},
    {0x3ff4a00000000000ULL, 0xbfd0402594b4d000ULL, 0xbcf036b89ef42d7fULL},
    {0x3ff4a00000000000ULL, 0xbfd0402594b4d000ULL, 0xbcf036b89ef42d7fULL},
    {0x3ff4800000000000ULL, 0xbfcfb9186d5e4000ULL, 0x3d0d572aab993c87ULL},
    {0x3ff4600000000000ULL, 0xbfcef0adcbdc6000ULL, 0x3d2b26b79c86af24ULL},
    {0x3ff4400000000000ULL, 0xbfce27076e2af000ULL, 0xbd172f4f543fff10ULL},
    {0x3ff4200000000000ULL, 0xbfcd5c216b4fc000ULL, 0x3d21ba91bbca681bULL},
    {0x3ff4000000000000ULL, 0xbfcc8ff7c79aa000ULL, 0x3d27794f689f8434ULL},
    {0x3ff4000000000000ULL, 0xbfcc8ff7c79aa000ULL, 0x3d27794f689f8434ULL},
    {0x3ff3e00000000000ULL, 0xbfcbc286742d9000ULL, 0x3d194eb0318bb78fULL},
    {0x3ff3c00000000000ULL, 0xbfcaf3c94e80c000ULL, 0x3cba4e633fcd9066ULL},
    {0x3ff3a00000000000ULL, 0xbfca23bc1fe2b000ULL, 0xbd258c64dc46c1eaULL},
    {0x3ff3a00000000000ULL, 0xbfca23bc1fe2b000ULL, 0xbd258c64dc46c1eaULL},
    {0x3ff3800000000000ULL, 0xbfc9525a9cf45000ULL, 0xbd2ad1d904c1d4e3ULL},
    {0x3ff3600000000000ULL, 0xbfc87fa06520d000ULL, 0x3d2bbdbf7fdbfa09ULL},
    {0x3ff3400000000000ULL, 0xbfc7ab890210e000ULL, 0x3d2bdb9072534a58ULL},
    {0x3ff3400000000000ULL, 0xbfc7ab890210e000ULL, 0x3d2bdb9072534a58ULL},
    {0x3ff3200000000000ULL, 0xbfc6d60fe719d000ULL, 0xbd10e46aa3b2e266ULL},
    {0x3ff3000000000000ULL, 0xbfc5ff3070a79000ULL, 0xbd1e9e439f105039ULL},
    {0x3ff3000000000000ULL, 0xbfc5ff3070a79000ULL, 0xbd1e9e439f105039ULL},
    {0x3ff2e00000000000ULL, 0xbfc526e5e3a1b000ULL, 0xbd20de8b90075b8fULL},
    {0x3ff2c00000000000ULL, 0xbfc44d2b6ccb8000ULL, 0x3d170cc16135783cULL},
    {0x3ff2c00000000000ULL, 0xbfc44d2b6ccb8000ULL, 0x3d170cc16135783cULL},
    {0x3ff2a00000000000ULL, 0xbfc371fc201e9000ULL, 0x3cf178864d27543aULL},
    {0x3ff2800000000000ULL, 0xbfc29552f81ff000ULL, 0xbd248d301771c408ULL},
    {0x3ff2600000000000ULL, 0xbfc1b72ad52f6000ULL, 0xbd2e80a41811a396ULL},
    {0x3ff2600000000000ULL, 0xbfc1b72ad52f6000ULL, 0xbd2e80a41811a396ULL},
    {0x3ff2400000000000ULL, 0xbfc0d77e7cd09000ULL, 0x3d0a699688e85bf4ULL},
    {0x3ff2400000000000ULL, 0xbfc0d77e7cd09000ULL, 0x3d0a699688e85bf4ULL},
    {0x3ff2200000000000ULL, 0xbfbfec9131dbe000ULL, 0xbd2575545ca333f2ULL},
    {0x3ff2000000000000ULL, 0xbfbe27076e2b0000ULL, 0x3d2a342c2af0003cULL},
    {0x3ff2000000000000ULL, 0xbfbe27076e2b0000ULL, 0x3d2a342c2af0003cULL},
    {0x3ff1e00000000000ULL, 0xbfbc5e548f5bc000ULL, 0xbd1d0c57585fbe06ULL},
    {0x3ff1c00000000000ULL, 0xbfba926d3a4ae000ULL, 0x3d253935e85baac8ULL},
    {0x3ff1c00000000000ULL, 0xbfba926d3a4ae000ULL, 0x3d253935e85baac8ULL},
    {0x3ff1a00000000000ULL, 0xbfb8c345d631a000ULL, 0x3d137c294d2f5668ULL},
    {0x3ff1a00000000000ULL, 0xbfb8c345d631a000ULL, 0x3d137c294d2f5668ULL},
    {0x3ff1800000000000ULL, 0xbfb6f0d28ae56000ULL, 0xbd269737c93373daULL},
    {0x3ff1600000000000ULL, 0xbfb51b073f062000ULL, 0x3d1f025b61c65e57ULL},
    {0x3ff1600000000000ULL, 0xbfb51b073f062000ULL, 0x3d1f025b61c65e57ULL},
    {0x3ff1400000000000ULL, 0xbfb341d7961be000ULL, 0x3d2c5edaccf913dfULL},
    {0x3ff1400000000000ULL, 0xbfb341d7961be000ULL, 0x3d2c5edaccf913dfULL},
    {0x3ff1200000000000ULL, 0xbfb16536eea38000ULL, 0x3d147c5e768fa309ULL},
    {0x3ff1000000000000ULL, 0xbfaf0a30c0118000ULL, 0x3d2d599e83368e91ULL},
    {0x3ff1000000000000ULL, 0xbfaf0a30c0118000ULL, 0x3d2d599e83368e91ULL},
    {0x3ff0e00000000000ULL, 0xbfab42dd71198000ULL, 0x3d1c827ae5d6704cULL},
    {0x3ff0e00000000000ULL, 0xbfab42dd71198000ULL, 0x3d1c827ae5d6704cULL},
    {0x3ff0c00000000000ULL, 0xbfa77458f632c000ULL, 0xbd2cfc4634f2a1eeULL},
    {0x3ff0c00000000000ULL, 0xbfa77458f632c000ULL, 0xbd2cfc4634f2a1eeULL},
    {0x3ff0a00000000000ULL, 0xbfa39e87b9fec000ULL, 0x3cf502b7f526feaaULL},
    {0x3ff0a00000000000ULL, 0xbfa39e87b9fec000ULL, 0x3cf502b7f526feaaULL},
    {0x3ff0800000000000ULL, 0xbf9f829b0e780000ULL, 0xbd2980267c7e09e4ULL},
    {0x3ff0800000000000ULL, 0xbf9f829b0e780000ULL, 0xbd2980267c7e09e4ULL},
    {0x3ff0600000000000ULL, 0xbf97b91b07d58000ULL, 0xbd288d5493faa639ULL},
    {0x3ff0400000000000ULL, 0xbf8fc0a8b0fc0000ULL, 0xbcdf1e7cf6d3a69cULL},
    {0x3ff0400000000000ULL, 0xbf8fc0a8b0fc0000ULL, 0xbcdf1e7cf6d3a69cULL},
    {0x3ff0200000000000ULL, 0xbf7fe02a6b100000ULL, 0xbd19e23f0dda40e4ULL},
    {0x3ff0200000000000ULL, 0xbf7fe02a6b100000ULL, 0xbd19e23f0dda40e4ULL},
    {0x3ff0000000000000ULL, 0x0000000000000000ULL, 0x0000000000000000ULL},
    {0x3ff0000000000000ULL, 0x0000000000000000ULL, 0x0000000000000000ULL},
    {0x3fefc00000000000ULL, 0x3f80101575890000ULL, 0xbd10c76b999d2be8ULL},
    {0x3fef800000000000ULL, 0x3f90205658938000ULL, 0xbd23dc5b06e2f7d2ULL},
    {0x3fef400000000000ULL, 0x3f98492528c90000ULL, 0xbd2aa0ba325a0c34ULL},
    {0x3fef000000000000ULL, 0x3fa0415d89e74000ULL, 0x3d0111c05cf1d753ULL},
    {0x3feec00000000000ULL, 0x3fa466aed42e0000ULL, 0xbd2c167375bdfd28ULL},
    {0x3fee800000000000ULL, 0x3fa894aa149fc000ULL, 0xbd197995d05a267dULL},
    {0x3fee400000000000ULL, 0x3faccb73cdddc000ULL, 0xbd1a68f247d82807ULL},
    {0x3fee200000000000ULL, 0x3faeea31c006c000ULL, 0xbd0e113e4fc93b7bULL},
    {0x3fede00000000000ULL, 0x3fb1973bd1466000ULL, 0xbd25325d560d9e9bULL},
    {0x3feda00000000000ULL, 0x3fb3bdf5a7d1e000ULL, 0x3d2cc85ea5db4ed7ULL},
    {0x3fed600000000000ULL, 0x3fb5e95a4d97a000ULL, 0xbd2c69063c5d1d1eULL},
    {0x3fed400000000000ULL, 0x3fb700d30aeac000ULL, 0x3cec1e8da99ded32ULL},
    {0x3fed000000000000ULL, 0x3fb9335e5d594000ULL, 0x3d23115c3abd47daULL},
    {0x3fecc00000000000ULL, 0x3fbb6ac88dad6000ULL, 0xbd1390802bf768e5ULL},
    {0x3feca00000000000ULL, 0x3fbc885801bc4000ULL, 0x3d2646d1c65aacd3ULL},
    {0x3fec600000000000ULL, 0x3fbec739830a2000ULL, 0xbd2dc068afe645e0ULL},
    {0x3fec400000000000ULL, 0x3fbfe89139dbe000ULL, 0xbd2534d64fa10afdULL},
    {0x3fec000000000000ULL, 0x3fc1178e8227e000ULL, 0x3d21ef78ce2d07f2ULL},
    {0x3febe00000000000ULL, 0x3fc1aa2b7e23f000ULL, 0x3d2ca78e44389934ULL},
    {0x3feba00000000000ULL, 0x3fc2d1610c868000ULL, 0x3d039d6ccb81b4a1ULL},
    {0x3feb800000000000ULL, 0x3fc365fcb0159000ULL, 0x3cc62fa8234b7289ULL},
    {0x3feb400000000000ULL, 0x3fc4913d8333b000ULL, 0x3d25837954fdb678ULL},
    {0x3feb200000000000ULL, 0x3fc527e5e4a1b000ULL, 0x3d2633e8e5697dc7ULL},
    {0x3feae00000000000ULL, 0x3fc6574ebe8c1000ULL, 0x3d19cf8b2c3c2e78ULL},
    {0x3feac00000000000ULL, 0x3fc6f0128b757000ULL, 0xbd25118de59c21e1ULL},
    {0x3feaa00000000000ULL, 0x3fc7898d85445000ULL, 0xbd1c661070914305ULL},
    {0x3fea600000000000ULL, 0x3fc8beafeb390000ULL, 0xbd073d54aae92cd1ULL},
    {0x3fea400000000000ULL, 0x3fc95a5adcf70000ULL, 0x3d07f22858a0ff6fULL},
    {0x3fea000000000000ULL, 0x3fca93ed3c8ae000ULL, 0xbd28724350562169ULL},
    {0x3fe9e00000000000ULL, 0x3fcb31d8575bd000ULL, 0xbd0c358d4eace1aaULL},
    {0x3fe9c00000000000ULL, 0x3fcbd087383be000ULL, 0xbd2d4bc4595412b6ULL},
    {0x3fe9a00000000000ULL, 0x3fcc6ffbc6f01000ULL, 0xbcf1ec72c5962bd2ULL},
    {0x3fe9600000000000ULL, 0x3fcdb13db0d49000ULL, 0xbd2aff2af715b035ULL},
    {0x3fe9400000000000ULL, 0x3fce530effe71000ULL, 0x3cc212276041f430ULL},
    {0x3fe9200000000000ULL, 0x3fcef5ade4dd0000ULL, 0xbcca211565bb8e11ULL},
    {0x3fe9000000000000ULL, 0x3fcf991c6cb3b000ULL, 0x3d1bcbecca0cdf30ULL},
    {0x3fe8c00000000000ULL, 0x3fd07138604d5800ULL, 0x3cf89cdb16ed4e91ULL},
    {0x3fe8a00000000000ULL, 0x3fd0c42d67616000ULL, 0x3d27188b163ceae9ULL},
    {0x3fe8800000000000ULL, 0x3fd1178e8227e800ULL, 0xbd2c210e63a5f01cULL},
    {0x3fe8600000000000ULL, 0x3fd16b5ccbacf800ULL, 0x3d2b9acdf7a51681ULL},
    {0x3fe8400000000000ULL, 0x3fd1bf99635a6800ULL, 0x3d2ca6ed5147bdb7ULL},
    {0x3fe8200000000000ULL, 0x3fd214456d0eb800ULL, 0x3d0a87deba46baeaULL},
    {0x3fe7e00000000000ULL, 0x3fd2bef07cdc9000ULL, 0x3d2a9cfa4a5004f4ULL},
    {0x3fe7c00000000000ULL, 0x3fd314f1e1d36000ULL, 0xbd28e27ad3213cb8ULL},
    {0x3fe7a00000000000ULL, 0x3fd36b6776be1000ULL, 0x3d116ecdb0f177c8ULL},
    {0x3fe7800000000000ULL, 0x3fd3c25277333000ULL, 0x3d183b54b606bd5cULL},
    {0x3fe7600000000000ULL, 0x3fd419b423d5e800ULL, 0x3d08e436ec90e09dULL},
    {0x3fe7400000000000ULL, 0x3fd4718dc271c800ULL, 0xbd2f27ce0967d675ULL},
    {0x3fe7200000000000ULL, 0x3fd4c9e09e173000ULL, 0xbd2e20891b0ad8a4ULL},
    {0x3fe7000000000000ULL, 0x3fd522ae0738a000ULL, 0x3d2ebe708164c759ULL},
    {0x3fe6e00000000000ULL, 0x3fd57bf753c8d000ULL, 0x3d1fadedee5d40efULL},
    {0x3fe6c00000000000ULL, 0x3fd5d5bddf596000ULL, 0xbd0a0b2a08a465dcULL},
};
/* ---- exp table: N/ln2, -ln2/N (hi, lo), shift, polynomial, tab ---- */
static const uint64_t EXP_INVLN2N = 0x40671547652b82feULL;
static const uint64_t EXP_NEGLN2HIN = 0xbf762e42fefa0000ULL;
static const uint64_t EXP_NEGLN2LON = 0xbd0cf79abc9e3b3aULL;
static const uint64_t EXP_SHIFT = 0x4338000000000000ULL;
static const uint64_t EXP_POLY[4] = {0x3fdffffffffffdbdULL, 0x3fc555555555543cULL, 0x3fa55555cf172b91ULL, 0x3f81111167a4d017ULL};
static const uint64_t EXP_TAB[256] = {
    0x0000000000000000ULL, 0x3ff0000000000000ULL,
    0x3c9b3b4f1a88bf6eULL, 0x3feff63da9fb3335ULL,
    0xbc7160139cd8dc5dULL, 0x3fefec9a3e778061ULL,
    0xbc905e7a108766d1ULL, 0x3fefe315e86e7f85ULL,
    0x3c8cd2523567f613ULL, 0x3fefd9b0d3158574ULL,
    0xbc8bce8023f98efaULL, 0x3fefd06b29ddf6deULL,
    0x3c60f74e61e6c861ULL, 0x3fefc74518759bc8ULL,
    0x3c90a3e45b33d399ULL, 0x3fefbe3ecac6f383ULL,
    0x3c979aa65d837b6dULL, 0x3fefb5586cf9890fULL,
    0x3c8eb51a92fdeffcULL, 0x3fefac922b7247f7ULL,
    0x3c3ebe3d702f9cd1ULL, 0x3fefa3ec32d3d1a2ULL,
    0xbc6a033489906e0bULL, 0x3fef9b66affed31bULL,
    0xbc9556522a2fbd0eULL, 0x3fef9301d0125b51ULL,
    0xbc5080ef8c4eea55ULL, 0x3fef8abdc06c31ccULL,
    0xbc91c923b9d5f416ULL, 0x3fef829aaea92de0ULL,
    0x3c80d3e3e95c55afULL, 0x3fef7a98c8a58e51ULL,
    0xbc801b15eaa59348ULL, 0x3fef72b83c7d517bULL,
    0xbc8f1ff055de323dULL, 0x3fef6af9388c8deaULL,
    0x3c8b898c3f1353bfULL, 0x3fef635beb6fcb75ULL,
    0xbc96d99c7611eb26ULL, 0x3fef5be084045cd4ULL,
    0x3c9aecf73e3a2f60ULL, 0x3fef54873168b9aaULL,
    0xbc8fe782cb86389dULL, 0x3fef4d5022fcd91dULL,
    0x3c8a6f4144a6c38dULL, 0x3fef463b88628cd6ULL,
    0x3c807a05b0e4047dULL, 0x3fef3f49917ddc96ULL,
    0x3c968efde3a8a894ULL, 0x3fef387a6e756238ULL,
    0x3c875e18f274487dULL, 0x3fef31ce4fb2a63fULL,
    0x3c80472b981fe7f2ULL, 0x3fef2b4565e27cddULL,
    0xbc96b87b3f71085eULL, 0x3fef24dfe1f56381ULL,
    0x3c82f7e16d09ab31ULL, 0x3fef1e9df51fdee1ULL,
    0xbc3d219b1a6fbffaULL, 0x3fef187fd0dad990ULL,
    0x3c8b3782720c0ab4ULL, 0x3fef1285a6e4030bULL,
    0x3c6e149289cecb8fULL, 0x3fef0cafa93e2f56ULL,
    0x3c834d754db0abb6ULL, 0x3fef06fe0a31b715ULL,
    0x3c864201e2ac744cULL, 0x3fef0170fc4cd831ULL,
    0x3c8fdd395dd3f84aULL, 0x3feefc08b26416ffULL,
    0xbc86a3803b8e5b04ULL, 0x3feef6c55f929ff1ULL,
    0xbc924aedcc4b5068ULL, 0x3feef1a7373aa9cbULL,
    0xbc9907f81b512d8eULL, 0x3feeecae6d05d866ULL,
    0xbc71d1e83e9436d2ULL, 0x3feee7db34e59ff7ULL,
    0xbc991919b3ce1b15ULL, 0x3feee32dc313a8e5ULL,
    0x3c859f48a72a4c6dULL, 0x3feedea64c123422ULL,
    0xbc9312607a28698aULL, 0x3feeda4504ac801cULL,
    0xbc58a78f4817895bULL, 0x3feed60a21f72e2aULL,
    0xbc7c2c9b67499a1bULL, 0x3feed1f5d950a897ULL,
    0x3c4363ed60c2ac11ULL, 0x3feece086061892dULL,
    0x3c9666093b0664efULL, 0x3feeca41ed1d0057ULL,
    0x3c6ecce1daa10379ULL, 0x3feec6a2b5c13cd0ULL,
    0x3c93ff8e3f0f1230ULL, 0x3feec32af0d7d3deULL,
    0x3c7690cebb7aafb0ULL, 0x3feebfdad5362a27ULL,
    0x3c931dbdeb54e077ULL, 0x3feebcb299fddd0dULL,
    0xbc8f94340071a38eULL, 0x3feeb9b2769d2ca7ULL,
    0xbc87deccdc93a349ULL, 0x3feeb6daa2cf6642ULL,
    0xbc78dec6bd0f385fULL, 0x3feeb42b569d4f82ULL,
    0xbc861246ec7b5cf6ULL, 0x3feeb1a4ca5d920fULL,
    0x3c93350518fdd78eULL, 0x3feeaf4736b527daULL,
    0x3c7b98b72f8a9b05ULL, 0x3feead12d497c7fdULL,
    0x3c9063e1e21c5409ULL, 0x3feeab07dd485429ULL,
    0x3c34c7855019c6eaULL, 0x3feea9268a5946b7ULL,
    0x3c9432e62b64c035ULL, 0x3feea76f15ad2148ULL,
    0xbc8ce44a6199769fULL, 0x3feea5e1b976dc09ULL,
    0xbc8c33c53bef4da8ULL, 0x3feea47eb03a5585ULL,
    0xbc845378892be9aeULL, 0x3feea34634ccc320ULL,
    0xbc93cedd78565858ULL, 0x3feea23882552225ULL,
    0x3c5710aa807e1964ULL, 0x3feea155d44ca973ULL,
    0xbc93b3efbf5e2228ULL, 0x3feea09e667f3bcdULL,
    0xbc6a12ad8734b982ULL, 0x3feea012750bdabfULL,
    0xbc6367efb86da9eeULL, 0x3fee9fb23c651a2fULL,
    0xbc80dc3d54e08851ULL, 0x3fee9f7df9519484ULL,
    0xbc781f647e5a3ecfULL, 0x3fee9f75e8ec5f74ULL,
    0xbc86ee4ac08b7db0ULL, 0x3fee9f9a48a58174ULL,
    0xbc8619321e55e68aULL, 0x3fee9feb564267c9ULL,
    0x3c909ccb5e09d4d3ULL, 0x3feea0694fde5d3fULL,
    0xbc7b32dcb94da51dULL, 0x3feea11473eb0187ULL,
    0x3c94ecfd5467c06bULL, 0x3feea1ed0130c132ULL,
    0x3c65ebe1abd66c55ULL, 0x3feea2f336cf4e62ULL,
    0xbc88a1c52fb3cf42ULL, 0x3feea427543e1a12ULL,
    0xbc9369b6f13b3734ULL, 0x3feea589994cce13ULL,
    0xbc805e843a19ff1eULL, 0x3feea71a4623c7adULL,
    0xbc94d450d872576eULL, 0x3feea8d99b4492edULL,
    0x3c90ad675b0e8a00ULL, 0x3feeaac7d98a6699ULL,
    0x3c8db72fc1f0eab4ULL, 0x3feeace5422aa0dbULL,
    0xbc65b6609cc5e7ffULL, 0x3feeaf3216b5448cULL,
    0x3c7bf68359f35f44ULL, 0x3feeb1ae99157736ULL,
    0xbc93091fa71e3d83ULL, 0x3feeb45b0b91ffc6ULL,
    0xbc5da9b88b6c1e29ULL, 0x3feeb737b0cdc5e5ULL,
    0xbc6c23f97c90b959ULL, 0x3feeba44cbc8520fULL,
    0xbc92434322f4f9aaULL, 0x3feebd829fde4e50ULL,
    0xbc85ca6cd7668e4bULL, 0x3feec0f170ca07baULL,
    0x3c71affc2b91ce27ULL, 0x3feec49182a3f090ULL,
    0x3c6dd235e10a73bbULL, 0x3feec86319e32323ULL,
    0xbc87c50422622263ULL, 0x3feecc667b5de565ULL,
    0x3c8b1c86e3e231d5ULL, 0x3feed09bec4a2d33ULL,
    0xbc91bbd1d3bcbb15ULL, 0x3feed503b23e255dULL,
    0x3c90cc319cee31d2ULL, 0x3feed99e1330b358ULL,
    0x3c8469846e735ab3ULL, 0x3feede6b5579fdbfULL,
    0xbc82dfcd978e9db4ULL, 0x3feee36bbfd3f37aULL,
    0x3c8c1a7792cb3387ULL, 0x3feee89f995ad3adULL,
    0xbc907b8f4ad1d9faULL, 0x3feeee07298db666ULL,
    0xbc55c3d956dcaebaULL, 0x3feef3a2b84f15fbULL,
    0xbc90a40e3da6f640ULL, 0x3feef9728de5593aULL,
    0xbc68d6f438ad9334ULL, 0x3feeff76f2fb5e47ULL,
    0xbc91eee26b588a35ULL, 0x3fef05b030a1064aULL,
    0x3c74ffd70a5fddcdULL, 0x3fef0c1e904bc1d2ULL,
    0xbc91bdfbfa9298acULL, 0x3fef12c25bd71e09ULL,
    0x3c736eae30af0cb3ULL, 0x3fef199bdd85529cULL,
    0x3c8ee3325c9ffd94ULL, 0x3fef20ab5fffd07aULL,
    0x3c84e08fd10959acULL, 0x3fef27f12e57d14bULL,
    0x3c63cdaf384e1a67ULL, 0x3fef2f6d9406e7b5ULL,
    0x3c676b2c6c921968ULL, 0x3fef3720dcef9069ULL,
    0xbc808a1883ccb5d2ULL, 0x3fef3f0b555dc3faULL,
    0xbc8fad5d3ffffa6fULL, 0x3fef472d4a07897cULL,
    0xbc900dae3875a949ULL, 0x3fef4f87080d89f2ULL,
    0x3c74a385a63d07a7ULL, 0x3fef5818dcfba487ULL,
    0xbc82919e2040220fULL, 0x3fef60e316c98398ULL,
    0x3c8e5a50d5c192acULL, 0x3fef69e603db3285ULL,
    0x3c843a59ac016b4bULL, 0x3fef7321f301b460ULL,
    0xbc82d52107b43e1fULL, 0x3fef7c97337b9b5fULL,
    0xbc892ab93b470dc9ULL, 0x3fef864614f5a129ULL,
    0x3c74b604603a88d3ULL, 0x3fef902ee78b3ff6ULL,
    0x3c83c5ec519d7271ULL, 0x3fef9a51fbc74c83ULL,
    0xbc8ff7128fd391f0ULL, 0x3fefa4afa2a490daULL,
    0xbc8dae98e223747dULL, 0x3fefaf482d8e67f1ULL,
    0x3c8ec3bc41aa2008ULL, 0x3fefba1bee615a27ULL,
    0x3c842b94c3a9eb32ULL, 0x3fefc52b376bba97ULL,
    0x3c8a64a931d185eeULL, 0x3fefd0765b6e4540ULL,
    0xbc8e37bae43be3edULL, 0x3fefdbfdad9cbe14ULL,
    0x3c77893b4d91cd9dULL, 0x3fefe7c1819e90d8ULL,
    0x3c5305c14160cc89ULL, 0x3feff3c22b8f71f1ULL,
};

/* log(x) = y + tail with ~15 extra bits (variant without FMA). */
static inline double log_inline(uint64_t ix, double *tail)
{
    const uint64_t OFF = 0x3fe6955500000000ULL;
    uint64_t tmp = ix - OFF;
    int i = (int)((tmp >> (52 - 7)) % 128);
    int k = (int)((int64_t)tmp >> 52);                 /* arithmetic shift */
    uint64_t iz = ix - (tmp & (0xfffULL << 52));
    double z = asdouble(iz);
    double kd = (double)k;

    double invc = asdouble(LOG_TAB[i][0]);
    double logc = asdouble(LOG_TAB[i][1]);
    double logctail = asdouble(LOG_TAB[i][2]);
    double Ln2hi = asdouble(LOG_LN2HI), Ln2lo = asdouble(LOG_LN2LO);
    double A0 = asdouble(LOG_POLY[0]), A1 = asdouble(LOG_POLY[1]), A2 = asdouble(LOG_POLY[2]);
    double A3 = asdouble(LOG_POLY[3]), A4 = asdouble(LOG_POLY[4]), A5 = asdouble(LOG_POLY[5]);
    double A6 = asdouble(LOG_POLY[6]);

    /* Split z such that rhi, rlo and rhi*rhi are exact and |rlo| <= |r|. */
    double zhi = asdouble((iz + (1ULL << 31)) & 0xffffffff00000000ULL);
    double zlo = z - zhi;
    double rhi = zhi * invc - 1.0;
    double rlo = zlo * invc;
    double r = rhi + rlo;

    /* k*Ln2 + log(c) + r. */
    double t1 = kd * Ln2hi + logc;
    double t2 = t1 + r;
    double lo1 = kd * Ln2lo + logctail;
    double lo2 = t1 - t2 + r;

    double ar = A0 * r;
    double ar2 = r * ar;
    double ar3 = r * ar2;
    double arhi = A0 * rhi;
    double arhi2 = rhi * arhi;
    double hi = t2 + arhi2;
    double lo3 = rlo * (ar + arhi);
    double lo4 = t2 - hi + arhi2;
    /* p = log1p(r) - r - A[0]*r*r. */
    double p = (ar3 * (A1 + r * A2 + ar2 * (A3 + r * A4 + ar2 * (A5 + r * A6))));
    double lo = lo1 + lo2 + lo3 + lo4 + p;
    double y = hi + lo;
    *tail = hi - y + lo;
    return y;
}

/* Result scale*(1+tmp) that may overflow or underflow. */
static inline double specialcase(double tmp, uint64_t sbits, uint64_t ki)
{
    double scale, y;
    if ((ki & 0x80000000) == 0) {
        /* k > 0, the exponent of scale might have overflowed by <= 460. */
        sbits -= 1009ULL << 52;
        scale = asdouble(sbits);
        y = asdouble(0x7f00000000000000ULL) * (scale + scale * tmp);      /* 0x1p1009 */
        return y;
    }
    /* k < 0, need special care in the subnormal range. */
    sbits += 1022ULL << 52;
    scale = asdouble(sbits);
    y = scale + scale * tmp;
    if (asdouble(asuint64(y) & 0x7fffffffffffffffULL) < 1.0) {           /* fabs(y) < 1 */
        double hi, lo, one = 1.0;
        if (y < 0.0)
            one = -1.0;
        lo = scale - y + scale * tmp;
        hi = one + y;
        lo = one - hi + y + lo;
        y = (hi + lo) - one;
        if (y == 0.0)
            y = asdouble(sbits & 0x8000000000000000ULL);
        fp_force_eval(fp_barrier(asdouble(0x0010000000000000ULL)) * asdouble(0x0010000000000000ULL));
    }
    y = asdouble(0x0010000000000000ULL) * y;                              /* 0x1p-1022 */
    return y;
}

#define OWNPOW_SIGN_BIAS (0x800 << 7)

/* sign * exp(x + xtail). */
static inline double exp_inline(double x, double xtail, uint32_t sign_bias)
{
    uint32_t abstop;
    uint64_t ki, idx, top, sbits;
    double kd, z, r, r2, scale, tail, tmp;
    double InvLn2N = asdouble(EXP_INVLN2N), Shift = asdouble(EXP_SHIFT);
    double NegLn2hiN = asdouble(EXP_NEGLN2HIN), NegLn2loN = asdouble(EXP_NEGLN2LON);
    double C2 = asdouble(EXP_POLY[0]), C3 = asdouble(EXP_POLY[1]);
    double C4 = asdouble(EXP_POLY[2]), C5 = asdouble(EXP_POLY[3]);

    abstop = top12(x) & 0x7ff;
    /* top12(0x1p-54) = 0x3c9, top12(512.0) = 0x408, top12(1024.0) = 0x409 */
    if (abstop - 0x3c9u >= 0x408u - 0x3c9u) {
        if (abstop - 0x3c9u >= 0x80000000u) {
            double one = 1.0 + x;                           /* WANT_ROUNDING */
            return sign_bias ? -one : one;
        }
        if (abstop >= 0x409u) {
            if (asuint64(x) >> 63)
                return math_uflow(sign_bias);
            else
                return math_oflow(sign_bias);
        }
        abstop = 0;
    }

    z = InvLn2N * x;
    kd = z + Shift;
    ki = asuint64(kd);
    kd -= Shift;
    r = x + kd * NegLn2hiN + kd * NegLn2loN;
    r += xtail;
    idx = 2 * (ki % 128);
    top = (ki + sign_bias) << (52 - 7);
    tail = asdouble(EXP_TAB[idx]);
    sbits = EXP_TAB[idx + 1] + top;
    r2 = r * r;
    tmp = tail + r + r2 * (C2 + r * C3) + r2 * r2 * (C4 + r * C5);
    if (abstop == 0)
        return specialcase(tmp, sbits, ki);
    scale = asdouble(sbits);
    return scale + scale * tmp;
}

/* 0 if not int, 1 if odd int, 2 if even int. */
static inline int checkint(uint64_t iy)
{
    int e = (int)(iy >> 52 & 0x7ff);
    if (e < 0x3ff)
        return 0;
    if (e > 0x3ff + 52)
        return 2;
    if (iy & ((1ULL << (0x3ff + 52 - e)) - 1))
        return 0;
    if (iy & (1ULL << (0x3ff + 52 - e)))
        return 1;
    return 2;
}

/* 1 if i is the bit representation of 0, infinity or nan. */
static inline int zeroinfnan(uint64_t i)
{
    return 2 * i - 1 >= 2 * 0x7ff0000000000000ULL - 1;
}

static inline double pow(double x, double y)
{
    const uint64_t ONE = 0x3ff0000000000000ULL, INF = 0x7ff0000000000000ULL;
    uint32_t sign_bias = 0;
    uint64_t ix, iy;
    uint32_t topx, topy;

    ix = asuint64(x);
    iy = asuint64(y);
    topx = top12(x);
    topy = top12(y);
    if (topx - 0x001u >= 0x7ffu - 0x001u || (topy & 0x7ff) - 0x3beu >= 0x43eu - 0x3beu) {
        if (zeroinfnan(iy)) {
            if (2 * iy == 0)
                return 1.0;
            if (ix == ONE)
                return 1.0;
            if (2 * ix > 2 * INF || 2 * iy > 2 * INF)
                return x + y;
            if (2 * ix == 2 * ONE)
                return 1.0;
            if ((2 * ix < 2 * ONE) == !(iy >> 63))
                return 0.0;
            return y * y;
        }
        if (zeroinfnan(ix)) {
            double x2 = x * x;
            if (ix >> 63 && checkint(iy) == 1)
                x2 = -x2;
            return iy >> 63 ? fp_barrier(1 / x2) : x2;
        }
        /* Here x and y are non-zero finite. */
        if (ix >> 63) {
            int yint = checkint(iy);
            if (yint == 0)
                return math_invalid(x);
            if (yint == 1)
                sign_bias = OWNPOW_SIGN_BIAS;
            ix &= 0x7fffffffffffffffULL;
            topx &= 0x7ff;
        }
        if ((topy & 0x7ff) - 0x3beu >= 0x43eu - 0x3beu) {
            if (ix == ONE)
                return 1.0;
            if ((topy & 0x7ff) < 0x3be) {
                return ix > ONE ? 1.0 + y : 1.0 - y;          /* WANT_ROUNDING */
            }
            return (ix > ONE) == (topy < 0x800) ? math_oflow(0) : math_uflow(0);
        }
        if (topx == 0) {
            /* Normalize subnormal x so exponent becomes negative. */
            ix = asuint64(x * asdouble(0x4330000000000000ULL));             /* x * 0x1p52 */
            ix &= 0x7fffffffffffffffULL;
            ix -= 52ULL << 52;
        }
    }

    double lo;
    double hi = log_inline(ix, &lo);
    double yhi = asdouble(iy & 0xfffffffff8000000ULL);                    /* iy & -1ULL << 27 */
    double ylo = y - yhi;
    double lhi = asdouble(asuint64(hi) & 0xfffffffff8000000ULL);
    double llo = hi - lhi + lo;
    double ehi = yhi * lhi;
    double elo = ylo * lhi + y * llo;                                     /* |elo| < |ehi| * 2^-25 */
    return exp_inline(ehi, elo, sign_bias);
}

#undef OWNPOW_SIGN_BIAS
}  /* namespace ownpowlib */

/* pow() used everywhere in this file */
static inline double ownpow(double x, double y) { return ownpowlib::pow(x, y); }
/* ========================= end of own pow() ============================= */


#ifdef __unix__
   #define OS_Windows 0
   #define DLLEXPORT  extern "C" __attribute__ ((visibility("default")))
#elif defined(_WIN32) || defined(WIN32)
   #define OS_Windows 1
   #define DLLEXPORT extern "C" __declspec(dllexport)
#else
   #define OS_Windows 0
   #define DLLEXPORT  extern "C" __attribute__ ((visibility("default")))
#endif

DLLEXPORT void ups(long long* in_array,long long* dirshort, double * out_array, int size);
DLLEXPORT void dirID(long long* lddorder, long long* ldd, long long* out_array, int sizei, int sizej);
DLLEXPORT void repairLdd1(long long * ldd, int sizei, int sizej);
DLLEXPORT void repairLdd2(long long* ldd, long long* dir,long long* check, int sizei);
DLLEXPORT void kinematic(double * Qold, double * q,long long* dirDown,long long* dirUpLen, long long* dirUpID, double * Qnew,double * alpha, double beta, double deltaT, double * deltaX, int size);
DLLEXPORT void runoffConc(double * conc, double * peak, double * fraction, double * flow, int maxlag, int size);

DLLEXPORT int  kinematicLevels(long long* dirDown, long long* dirUpLen, long long* dirUpID, int size, int ncells,
                               long long* levelOrder, long long* levelStart);
DLLEXPORT void kinematicPar(double * Qold, double * q, long long* levelOrder, long long* levelStart, int nlevels,
                            long long* dirUpLen, long long* dirUpID, double * Qnew, double * alpha, double beta,
                            double deltaT, double * deltaX, int nthreads);
DLLEXPORT int  kinematicParVersion(void);
DLLEXPORT int  kinematicParMaxThreads(void);
DLLEXPORT double ownPow(double x, double y);
DLLEXPORT double ownPow06(double x);


/* =========================================================================
   unchanged functions from t5.cpp
   ========================================================================= */

/*  Compute the upstream area storing the result in *  out_array. */
void ups(long long* in_array,long long* dirshort, double * out_array, int size){
    int i;
    int j;
    int k;

    for(i=0;i<size;i++){
        j = in_array[i];
        k = dirshort[j];
        if(k > -1)
           out_array[k] =  out_array[k] + out_array[j];
    }
}


void repairLdd1(long long * ldd, int sizei, int sizej){

    int i,j,k;
    long long lddvalue;
    int x,y,xy;

    int dirX [10] = { 0, -1,0,1, -1,0,1, -1, 0, 1 };
    int dirY [10] = { 0, 1, 1,1,  0,0,0, -1,-1,-1 };

    for(i=0;i<sizei;i++){
        for(j=0;j<sizej;j++){

           k = i * sizej + j;
           lddvalue = ldd[k];
           if (lddvalue > 9) {
               lddvalue = 0;
           }

           if ((lddvalue != 0) && (lddvalue != 5)) {
               x = j  + dirX[lddvalue];
               y = i  + dirY[lddvalue];
               if ((y < 0) || (y == sizei))
                   ldd[k]=5;
               if ((x < 0) || (x == sizej))
                   ldd[k]=5;
               if (ldd[k] != 5) {
                   xy = y * sizej + x;
                   if (ldd[xy] == 0)
                     ldd[k]=5;
               }
           }

        }
    }

}


void repairLdd2(long long* ldd, long long* dir,long long* check, int sizei){

    int i,j,k,id;
    std::vector<int> path;

    for(i=0;i<sizei;i++){
        path.clear();
        k = 0;
        j = i;
        while( 1 ) {
           if(std::find(path.begin(), path.end(), j) != path.end()) {
              id = path[k-1];
              ldd[id] = 5;
              dir[id] = -1;
              break;
           }
           if ((ldd[j] == 5) || (check[j] == 1))
              break;
           path.push_back (j);
           k++;
           j = dir[j];
        }
        for(std::vector<int>::size_type kk = 0; kk != path.size(); kk++) {
            id = path[kk];
            check[id] = 1;
        }
    }
}


void dirID(long long * lddorder, long long * ldd, long long* out_array, int sizei, int sizej){

    int i, j,k;
    long long lddvalue;
    int x,y,xy;

    int dirX [10] = { 0, -1,0,1, -1,0,1, -1, 0, 1 };
    int dirY [10] = { 0, 1, 1,1,  0,0,0, -1,-1,-1 };

    for(i=0;i<sizei;i++){
        for(j=0;j<sizej;j++){
           k = i * sizej + j;
           lddvalue = ldd[k];
           if (lddvalue > 9) {
               lddvalue = 0;
           }

           if ((lddvalue != 0) && (lddvalue != 5)) {
               x = j  + dirX[lddvalue];
               y = i  + dirY[lddvalue];
               xy = y * sizej + x;
               out_array[k] = lddorder[xy];
           }
        }
    }
}



/* =========================================================================
   Special x^0.6 (chanBeta = 0.6 in all settings files), faster than the
   general pow(). The same function as pow(x, 0.6), only computed differently:

   x = m * 2^e, m in [1,2).  x^0.6 = x^(3/5) * x^(-d),  d = 3/5 - 0.6(double) ~ 2.2e-17
   x^(3/5) = m^(3/5) * 2^(3e/5);  3e = 5k + j  ->  2^(3e/5) = 2^k * 2^(j/5)  (5 constants)
   m^(3/5) = c^(3/5) * (1+r)^(3/5): c = centre of one of 256 intervals, |r| <= 1/512,
             (1+r)^(3/5) - 1 by its binomial series (degree 6, error < 2e-19)
   x^(-d)  = 1 - d*ln(x)   (d*ln(x) < 2e-14, ln(x) = e*ln2 + ln(c) + r is accurate enough)
   Tables: c^(3/5)*2^(j/5) as hi + lo, 1/c, ln(c) - all as exact 64-bit patterns.
   Only +, -, * and integer operations -> the same bits on every platform and compiler.
   x = 0, x < 0 and nan: the value of pow() directly (see powbeta).
   Any other exponent, subnormal and inf: the general ownpow().
   ========================================================================= */
namespace pow06lib {
using ownpowlib::asuint64;
using ownpowlib::asdouble;

static const uint64_t INVC[256] = {
    0x3feff007fc01ff00ULL, 0x3fefd04794a10e6aULL, 0x3fefb0c610d5e939ULL, 0x3fef9182b6813bafULL,
    0x3fef727cce5f530aULL, 0x3fef53b3a3fa204eULL, 0x3fef3526859b8cecULL, 0x3fef16d4c4401f17ULL,
    0x3feef8bdb389ebadULL, 0x3feedae0a9b3d3a5ULL, 0x3feebd3cff850b0cULL, 0x3fee9fd21044e799ULL,
    0x3fee829f39aef509ULL, 0x3fee65a3dbe74d6bULL, 0x3fee48df596f3394ULL, 0x3fee2c511719ee16ULL,
    0x3fee0ff87c01e100ULL, 0x3fedf3d4f17de4dbULL, 0x3fedd7e5e316d94cULL, 0x3fedbc2abe7d71d4ULL,
    0x3feda0a2f3803b41ULL, 0x3fed854df401d855ULL, 0x3fed6a2b33ef7448ULL, 0x3fed4f3a293769caULL,
    0x3fed347a4bc01d34ULL, 0x3fed19eb155f08a4ULL, 0x3fecff8c01cff8c0ULL, 0x3fece55c8eac7900ULL,
    0x3feccb5c3b636e3aULL, 0x3fecb18a8930de60ULL, 0x3fec97e6fb15e44dULL, 0x3fec7e7115d0ce95ULL,
    0x3fec65285fd56843ULL, 0x3fec4c0c61456a8eULL, 0x3fec331ca3e91679ULL, 0x3fec1a58b327f576ULL,
    0x3fec01c01c01c01cULL, 0x3febe9526d0769faULL, 0x3febd10f365451b6ULL, 0x3febb8f609879493ULL,
    0x3feba10679bd8488ULL, 0x3feb89401b89401cULL, 0x3feb71a284ee6b34ULL, 0x3feb5a2d4d5b081fULL,
    0x3feb42e00da17007ULL, 0x3feb2bba5ff26a23ULL, 0x3feb14bbdfd760e6ULL, 0x3feafde42a2cb482ULL,
    0x3feae732dd1c2a09ULL, 0x3fead0a798177693ULL, 0x3feaba41fbd2e5b1ULL, 0x3feaa401aa401aa4ULL,
    0x3fea8de64688ebabULL, 0x3fea77ef750a56daULL, 0x3fea621cdb4f8fdfULL, 0x3fea4c6e200d2637ULL,
    0x3fea36e2eb1c432dULL, 0x3fea217ae575ff2fULL, 0x3fea0c35b92ecdf1ULL, 0x3fe9f713117200d0ULL,
    0x3fe9e2129a7d5f0aULL, 0x3fe9cd34019cd340ULL, 0x3fe9b876f5262dd1ULL, 0x3fe9a3db2474fb98ULL,
    0x3fe98f603fe670a0ULL, 0x3fe97b05f8d56652ULL, 0x3fe966cc01966cc0ULL, 0x3fe952b20d73ee97ULL,
    0x3fe93eb7d0aa6759ULL, 0x3fe92add0064ab74ULL, 0x3fe9172152b841ddULL, 0x3fe903847ea1cec1ULL,
    0x3fe8f0063c018f00ULL, 0x3fe8dca64397e408ULL, 0x3fe8c9644f01efbcULL, 0x3fe8b64018b64019ULL,
    0x3fe8a3395c018a34ULL, 0x3fe8904fd503744bULL, 0x3fe87d8340ab6e97ULL, 0x3fe86ad35cb59a84ULL,
    0x3fe8583fe7a7c018ULL, 0x3fe845c8a0ce5129ULL, 0x3fe8336d48397a24ULL, 0x3fe8212d9eba4018ULL,
    0x3fe80f0965dfabcbULL, 0x3fe7fd005ff40180ULL, 0x3fe7eb124ffa053bULL, 0x3fe7d93ef9aa4b46ULL,
    0x3fe7c7862170949fULL, 0x3fe7b5e78c693733ULL, 0x3fe7a463005e918cULL, 0x3fe792f843c689c3ULL,
    0x3fe781a71dc01782ULL, 0x3fe7706f5610d8d0ULL, 0x3fe75f50b522b17cULL, 0x3fe74e4b040174e5ULL,
    0x3fe73d5e0c5899f7ULL, 0x3fe72c899870f91fULL, 0x3fe71bcd732e940aULL, 0x3fe70b29680e66faULL,
    0x3fe6fa9d43244380ULL, 0x3fe6ea28d118b474ULL, 0x3fe6d9cbdf26eaefULL, 0x3fe6c9863b1ab429ULL,
    0x3fe6b957b34e7803ULL, 0x3fe6a94016a94017ULL, 0x3fe6993f349cc726ULL, 0x3fe68954dd2390baULL,
    0x3fe67980e0bf08c7ULL, 0x3fe669c31075ab40ULL, 0x3fe65a1b3dd13357ULL, 0x3fe64a893adcd25fULL,
    0x3fe63b0cda236e1cULL, 0x3fe62ba5eeade65eULL, 0x3fe61c544c0161c5ULL, 0x3fe60d17c61da198ULL,
    0x3fe5fdf0317b5c6fULL, 0x3fe5eedd630a9fb3ULL, 0x3fe5dfdf303137b6ULL, 0x3fe5d0f56ec91e57ULL,
    0x3fe5c21ff51ef005ULL, 0x3fe5b35e99f06714ULL, 0x3fe5a4b1346add2bULL, 0x3fe596179c29d2ceULL,
    0x3fe58791a9357cceULL, 0x3fe5791f34015792ULL, 0x3fe56ac0156ac015ULL, 0x3fe55c7426b79286ULL,
    0x3fe54e3b4194ce66ULL, 0x3fe5401540154015ULL, 0x3fe53201fcb02fb1ULL, 0x3fe5240152401524ULL,
    0x3fe516131c015161ULL, 0x3fe508373590ec9cULL, 0x3fe4fa6d7aeb597cULL, 0x3fe4ecb5c86b3d24ULL,
    0x3fe4df0ffac83c01ULL, 0x3fe4d17bef15cb4eULL, 0x3fe4c3f982c20723ULL, 0x3fe4b68893948d1cULL,
    0x3fe4a928ffad5b5cULL, 0x3fe49bdaa583b401ULL, 0x3fe48e9d63e504d1ULL, 0x3fe4817119f3d325ULL,
    0x3fe47455a726abf2ULL, 0x3fe4674aeb4717e9ULL, 0x3fe45a50c670938fULL, 0x3fe44d67190f8b43ULL,
    0x3fe4408dc3e05b22ULL, 0x3fe433c4a7ee52b4ULL, 0x3fe4270ba692bc4dULL, 0x3fe41a62a173e821ULL,
    0x3fe40dc97a843ae8ULL, 0x3fe4014014014014ULL, 0x3fe3f4c65072bf74ULL, 0x3fe3e85c12a9d651ULL,
    0x3fe3dc013dc013dcULL, 0x3fe3cfb5b51698ebULL, 0x3fe3c3795c553afbULL, 0x3fe3b74c1769aa5cULL,
    0x3fe3ab2dca869b81ULL, 0x3fe39f1e5a22f36eULL, 0x3fe3931daaf8f721ULL, 0x3fe3872ba2057e04ULL,
    0x3fe37b4824872744ULL, 0x3fe36f7317fd9212ULL, 0x3fe363ac622898b1ULL, 0x3fe357f3e9078e5bULL,
    0x3fe34c4992d87fd9ULL, 0x3fe340ad461776d3ULL, 0x3fe3351ee97dbfc6ULL, 0x3fe3299e6401329aULL,
    0x3fe31e2b9cd37dc2ULL, 0x3fe312c67b6173eeULL, 0x3fe3076ee7525c2cULL, 0x3fe2fc24c8874486ULL,
    0x3fe2f0e8071a5703ULL, 0x3fe2e5b88b5e3104ULL, 0x3fe2da963ddd3cfbULL, 0x3fe2cf8107590e67ULL,
    0x3fe2c478d0c9c013ULL, 0x3fe2b97d835d548eULL, 0x3fe2ae8f087718d0ULL, 0x3fe2a3ad49af0907ULL,
    0x3fe298d830d13780ULL, 0x3fe28e0fa7dd35a3ULL, 0x3fe2835399057efdULL, 0x3fe278a3eeaee650ULL,
    0x3fe26e009370049cULL, 0x3fe263697210aa18ULL, 0x3fe258de75895121ULL, 0x3fe24e5f89029305ULL,
    0x3fe243ec97d49eaeULL, 0x3fe239858d86b11fULL, 0x3fe22f2a55ce8fc5ULL, 0x3fe224dadc900489ULL,
    0x3fe21a970ddc5ba7ULL, 0x3fe2105ed5f1e336ULL, 0x3fe20632213b6c6dULL, 0x3fe1fc10dc4fce8bULL,
    0x3fe1f1faf3f16b64ULL, 0x3fe1e7f0550db594ULL, 0x3fe1ddf0ecbcb841ULL, 0x3fe1d3fca840a074ULL,
    0x3fe1ca13750547feULL, 0x3fe1c035409fc1dfULL, 0x3fe1b661f8cde833ULL, 0x3fe1ac998b75eb90ULL,
    0x3fe1a2dbe6a5e3e4ULL, 0x3fe19928f89362b7ULL, 0x3fe18f80af9b06dcULL, 0x3fe185e2fa401186ULL,
    0x3fe17c4fc72bfcb9ULL, 0x3fe172c7052e1316ULL, 0x3fe16948a33b08faULL, 0x3fe15fd4906c96f1ULL,
    0x3fe1566abc011567ULL, 0x3fe14d0b155b19aeULL, 0x3fe143b58c01143bULL, 0x3fe13a6a0f9cf01eULL,
    0x3fe131288ffbb3b6ULL, 0x3fe127f0fd0d2295ULL, 0x3fe11ec346e36092ULL, 0x3fe1159f5db29606ULL,
    0x3fe10c8531d0952eULL, 0x3fe10374b3b480aaULL, 0x3fe0fa6dd3f67322ULL, 0x3fe0f170834f27faULL,
    0x3fe0e87cb297a51eULL, 0x3fe0df9252c8e5e6ULL, 0x3fe0d6b154fb86f9ULL, 0x3fe0cdd9aa677344ULL,
    0x3fe0c50b446391f3ULL, 0x3fe0bc4614657569ULL, 0x3fe0b38a0c010b39ULL, 0x3fe0aad71ce84d16ULL,
    0x3fe0a22d38eaf2bfULL, 0x3fe0998c51f624d5ULL, 0x3fe090f45a1430aaULL, 0x3fe08865436c3cf7ULL,
    0x3fe07fdf0041ff7cULL, 0x3fe0776182f57386ULL, 0x3fe06eecbe029155ULL, 0x3fe06680a4010668ULL,
    0x3fe05e1d27a3ee9cULL, 0x3fe055c23bb98e2aULL, 0x3fe04d6fd32b0c7bULL, 0x3fe04525e0fc2fcbULL,
    0x3fe03ce4584b19a0ULL, 0x3fe034ab2c50040dULL, 0x3fe02c7a505cffbfULL, 0x3fe02451b7ddb2d2ULL,
    0x3fe01c315657186bULL, 0x3fe014191f674111ULL, 0x3fe00c0906c513cfULL, 0x3fe0040100401004ULL,
};
static const uint64_t LNC[256] = {
    0x3f5ff802a9ab10e6ULL, 0x3f77ee11ebd82e94ULL, 0x3f83e7295d25a7d9ULL, 0x3f8bcf712c74384cULL,
    0x3f91d7f7eb9eebe7ULL, 0x3f95c45a51b8d389ULL, 0x3f99ace7551cc514ULL, 0x3f9d91a66c543cc4ULL,
    0x3fa0b94f7c196176ULL, 0x3fa2a7ec2214e873ULL, 0x3fa494acc34d911cULL, 0x3fa67f94f094bd98ULL,
    0x3fa868a83083f6cfULL, 0x3faa4fe9ffa3d235ULL, 0x3fac355dd0921f2dULL, 0x3fae19070c276016ULL,
    0x3faffae9119b9303ULL, 0x3fb0ed839b5526feULL, 0x3fb1dcb263db1944ULL, 0x3fb2cb0283f5de1fULL,
    0x3fb3b87598b1b6eeULL, 0x3fb4a50d3aa1b040ULL, 0x3fb590cafdf01c28ULL, 0x3fb67bb0726ec0fcULL,
    0x3fb765bf23a6be13ULL, 0x3fb84ef898e8282aULL, 0x3fb9375e55595edeULL, 0x3fba1ef1d8061cd4ULL,
    0x3fbb05b49bee43feULL, 0x3fbbeba818146765ULL, 0x3fbcd0cdbf8c13e1ULL, 0x3fbdb5270187d927ULL,
    0x3fbe98b549671467ULL, 0x3fbf7b79fec37ddfULL, 0x3fc02ebb42bf3d4bULL, 0x3fc09f561ee719c3ULL,
    0x3fc10f8e422539b1ULL, 0x3fc17f6458fca611ULL, 0x3fc1eed90e2dc2c3ULL, 0x3fc25ded0abc6ad2ULL,
    0x3fc2cca0f5f5f251ULL, 0x3fc33af575770e4fULL, 0x3fc3a8eb2d31a376ULL, 0x3fc41682bf727bc0ULL,
    0x3fc483bccce6e3ddULL, 0x3fc4f099f4a230b2ULL, 0x3fc55d1ad4232d6fULL, 0x3fc5c940075972b9ULL,
    0x3fc6350a28aaa758ULL, 0x3fc6a079d0f7aad2ULL, 0x3fc70b8f97a1aa75ULL, 0x3fc7764c128f2127ULL,
    0x3fc7e0afd630c274ULL, 0x3fc84abb75865139ULL, 0x3fc8b46f8223625bULL, 0x3fc91dcc8c340bdeULL,
    0x3fc986d3228180caULL, 0x3fc9ef83d2769a34ULL, 0x3fca57df28244dcdULL, 0x3fcabfe5ae46124cULL,
    0x3fcb2797ee46320cULL, 0x3fcb8ef670420c3bULL, 0x3fcbf601bb0e44e2ULL, 0x3fcc5cba543ae425ULL,
    0x3fccc320c0176502ULL, 0x3fcd293581b6b3e7ULL, 0x3fcd8ef91af31d5eULL, 0x3fcdf46c0c722d2fULL,
    0x3fce598ed5a87e2fULL, 0x3fcebe61f4dd7b0bULL, 0x3fcf22e5e72f105dULL, 0x3fcf871b28955045ULL,
    0x3fcfeb0233e607ccULL, 0x3fd0274dc16c232fULL, 0x3fd058f3c703ebc6ULL, 0x3fd08a73667c57afULL,
    0x3fd0bbccdb0d24bdULL, 0x3fd0ed005f657da4ULL, 0x3fd11e0e2dad9cb7ULL, 0x3fd14ef67f88685aULL,
    0x3fd17fb98e15095dULL, 0x3fd1b05791f07b49ULL, 0x3fd1e0d0c33716beULL, 0x3fd211255986160cULL,
    0x3fd241558bfd1404ULL, 0x3fd27161913f853dULL, 0x3fd2a1499f762bc9ULL, 0x3fd2d10dec508583ULL,
    0x3fd300aead06350cULL, 0x3fd3302c16586588ULL, 0x3fd35f865c93293eULL, 0x3fd38ebdb38ed321ULL,
    0x3fd3bdd24eb14b6aULL, 0x3fd3ecc460ef5f50ULL, 0x3fd41b941cce0beeULL, 0x3fd44a41b463c47cULL,
    0x3fd478cd5959b3d9ULL, 0x3fd4a7373cecf997ULL, 0x3fd4d57f8fefe27fULL, 0x3fd503a682cb1cb3ULL,
    0x3fd531ac457ee77eULL, 0x3fd55f9107a43ee2ULL, 0x3fd58d54f86e02f2ULL, 0x3fd5baf846aa1b19ULL,
    0x3fd5e87b20c2954aULL, 0x3fd615ddb4bec13cULL, 0x3fd64320304447c0ULL, 0x3fd67042c0983e31ULL,
    0x3fd69d4592a0362cULL, 0x3fd6ca28d2e34985ULL, 0x3fd6f6ecad8b2292ULL, 0x3fd723914e6500e1ULL,
    0x3fd75016e0e2ba62ULL, 0x3fd77c7d901bb914ULL, 0x3fd7a8c586cdf544ULL, 0x3fd7d4eeef5eec6eULL,
    0x3fd800f9f3dc94cbULL, 0x3fd82ce6bdfe4d9dULL, 0x3fd858b57725cc43ULL, 0x3fd8846648600624ULL,
    0x3fd8aff95a661780ULL, 0x3fd8db6ed59e272dULL, 0x3fd906c6e21c4754ULL, 0x3fd93201a7a35337ULL,
    0x3fd95d1f4da5ca0aULL, 0x3fd9881ffb46a6f0ULL, 0x3fd9b303d75a361fULL, 0x3fd9ddcb0866e742ULL,
    0x3fda0875b4a61d17ULL, 0x3fda33040204fa63ULL, 0x3fda5d7616252c37ULL, 0x3fda87cc165db199ULL,
    0x3fdab20627bba0a0ULL, 0x3fdadc246f02e8ffULL, 0x3fdb062710af141bULL, 0x3fdb300e30f402a3ULL,
    0x3fdb59d9f3bea7c2ULL, 0x3fdb838a7cb5c1f0ULL, 0x3fdbad1fef3a9165ULL, 0x3fdbd69a6e698c47ULL,
    0x3fdbfffa1d1b1084ULL, 0x3fdc293f1de4137cULL, 0x3fdc52699316cf6bULL, 0x3fdc7b799ec36eb0ULL,
    0x3fdca46f62b8b4e7ULL, 0x3fdccd4b0084a5efULL, 0x3fdcf60c99752adaULL, 0x3fdd1eb44e98b4c9ULL,
    0x3fdd474240beddd6ULL, 0x3fdd6fb6907907eaULL, 0x3fdd98115e1af9b6ULL, 0x3fddc052c9bb79acULL,
    0x3fdde87af334e71bULL, 0x3fde1089fa25d168ULL, 0x3fde387ffdf18d76ULL, 0x3fde605d1dc0c92fULL,
    0x3fde882178821d52ULL, 0x3fdeafcd2cea9d71ULL, 0x3fded7605976663bULL, 0x3fdefedb1c692a08ULL,
    0x3fdf263d93cebbb7ULL, 0x3fdf4d87dd7b97e6ULL, 0x3fdf74ba170d6c7dULL, 0x3fdf9bd45deb9ea4ULL,
    0x3fdfc2d6cf47cf1aULL, 0x3fdfe9c1881e5cffULL, 0x3fe0084a529b7386ULL, 0x3fe01ba8219265a4ULL,
    0x3fe02efa3f23d29cULL, 0x3fe04240b965e54cULL, 0x3fe0557b9e55634eULL, 0x3fe068aafbd5e9daULL,
    0x3fe07bcedfb229fdULL, 0x3fe08ee7579c2413ULL, 0x3fe0a1f4712d6292ULL, 0x3fe0b4f639e73429ULL,
    0x3fe0c7ecbf32e533ULL, 0x3fe0dad80e61f87bULL, 0x3fe0edb834ae5f5eULL, 0x3fe1008d3f3ab146ULL,
    0x3fe113573b126282ULL, 0x3fe126163529fa7aULL, 0x3fe138ca3a5f494fULL, 0x3fe14b7357799cd1ULL,
    0x3fe15e119929f4e4ULL, 0x3fe170a50c0b374aULL, 0x3fe1832dbca262d9ULL, 0x3fe195abb75ec21aULL,
    0x3fe1a81f089a1d56ULL, 0x3fe1ba87bc98ec1bULL, 0x3fe1cce5df8a8622ULL, 0x3fe1df397d8953bfULL,
    0x3fe1f182a29afdb0ULL, 0x3fe203c15ab09c7aULL, 0x3fe215f5b1a6e729ULL, 0x3fe2281fb346619fULL,
    0x3fe23a3f6b438a53ULL, 0x3fe24c54e53f0793ULL, 0x3fe25e602cc5d447ULL, 0x3fe270614d516c38ULL,
    0x3fe282585247f7d3ULL, 0x3fe2944546fc777aULL, 0x3fe2a62836aeee59ULL, 0x3fe2b8012c8c8cc1ULL,
    0x3fe2c9d033afda0fULL, 0x3fe2db955720de23ULL, 0x3fe2ed50a1d54a5aULL, 0x3fe2ff021eb0a221ULL,
    0x3fe310a9d8846312ULL, 0x3fe32247da102ca6ULL, 0x3fe333dc2e01e776ULL, 0x3fe34566def5ec14ULL,
    0x3fe356e7f7772978ULL, 0x3fe3685f81ff4b07ULL, 0x3fe379cd88f6de2bULL, 0x3fe38b3216b5778eULL,
    0x3fe39c8d3581d7ecULL, 0x3fe3addeef92107fULL, 0x3fe3bf274f0ba70dULL, 0x3fe3d0665e03b98fULL,
    0x3fe3e19c267f2182ULL, 0x3fe3f2c8b27296ceULL, 0x3fe403ec0bc2d256ULL, 0x3fe415063c44b02cULL,
    0x3fe426174dbd5167ULL, 0x3fe4371f49e23d9dULL, 0x3fe4481e3a59840eULL, 0x3fe4591428b9dc68ULL,
    0x3fe46a011e8ac745ULL, 0x3fe47ae52544ae44ULL, 0x3fe48bc0465103d8ULL, 0x3fe49c928b0a62beULL,
    0x3fe4ad5bfcbcad23ULL, 0x3fe4be1ca4a52b78ULL, 0x3fe4ced48bf2aaf4ULL, 0x3fe4df83bbc59bc8ULL,
    0x3fe4f02a3d302f06ULL, 0x3fe500c819367434ULL, 0x3fe5115d58ce769cULL, 0x3fe521ea04e05a45ULL,
    0x3fe5326e264678adULL, 0x3fe542e9c5cd7d2fULL, 0x3fe5535cec348128ULL, 0x3fe563c7a22d27ccULL,
    0x3fe57429f05bb9b9ULL, 0x3fe58483df574044ULL, 0x3fe594d577a9a07eULL, 0x3fe5a51ec1cfb5f4ULL,
    0x3fe5b55fc6396d2bULL, 0x3fe5c5988d49dddeULL, 0x3fe5d5c91f5764f0ULL, 0x3fe5e5f184abbe28ULL,
    0x3fe5f611c5841d9fULL, 0x3fe60629ea1148fdULL, 0x3fe61639fa77b069ULL, 0x3fe62641fecf8743ULL,
};
static const uint64_t HT[5][256][2] = {
  {
    {0x3ff004cc52082890ULL, 0xbc86afc04987aa7fULL}, {0x3ff00e62177e502eULL, 0xbc9283f8a43f5e19ULL},
    {0x3ff017f40deb2372ULL, 0x3c8e9f948d3cd5b8ULL}, {0x3ff021823a9571eaULL, 0xbc97a37ff3c736a2ULL},
    {0x3ff02b0ca2b78f59ULL, 0xbc8d8f8e3e276937ULL}, {0x3ff034934b7f7d6bULL, 0x3c69eefb626f5ae6ULL},
    {0x3ff03e163a0f14adULL, 0xbc84ba0569f28e7dULL}, {0x3ff04795737c2cd6ULL, 0x3c8a7c0b4663e908ULL},
    {0x3ff05110fcd0c46aULL, 0xbc9aba98a7513de0ULL}, {0x3ff05a88db0b27aaULL, 0xbc8c83750af72e6dULL},
    {0x3ff063fd131e16ebULL, 0xbc822ff6fd8130bcULL}, {0x3ff06d6da9f0ec41ULL, 0x3c875d3b9d9cbf15ULL},
    {0x3ff076daa45fc092ULL, 0xbc7fc15123977005ULL}, {0x3ff08044073b9008ULL, 0xbc726f2b813eb3c6ULL},
    {0x3ff089a9d74a5df1ULL, 0x3c5aa48d21f322dcULL}, {0x3ff0930c19475805ULL, 0x3c8468c08634d212ULL},
    {0x3ff09c6ad1e2f91cULL, 0xbc637e220b7ef274ULL}, {0x3ff0a5c605c32b53ULL, 0xbc93fd8c35898fb9ULL},
    {0x3ff0af1db98369a6ULL, 0xbc9661a4c90cb051ULL}, {0x3ff0b871f1b4e100ULL, 0xbc7cd7baa0e24c68ULL},
    {0x3ff0c1c2b2de90c4ULL, 0xbc901c1cdf49cfd0ULL}, {0x3ff0cb10017d6acfULL, 0x3c65fb98c7166716ULL},
    {0x3ff0d459e20472fdULL, 0x3c94cdb9b36e850eULL}, {0x3ff0dda058dcde2bULL, 0xbc860c115e9a2b6cULL},
    {0x3ff0e6e36a6630bbULL, 0xbc9f69a43907a13aULL}, {0x3ff0f0231af65ca2ULL, 0xbc98e34f92abd433ULL},
    {0x3ff0f95f6ed9defbULL, 0x3c7423ed9be81eaaULL}, {0x3ff102986a53dd25ULL, 0x3c815a4ba0b5af05ULL},
    {0x3ff10bce119e416bULL, 0x3c908c78fe47ed17ULL}, {0x3ff1150068e9d73fULL, 0xbc906c625db3a039ULL},
    {0x3ff11e2f745e6700ULL, 0x3c37411b091765c4ULL}, {0x3ff1275b381ad15bULL, 0xbc925e5ddad118a1ULL},
    {0x3ff13083b8352a37ULL, 0xbc8a0bd3f6159792ULL}, {0x3ff139a8f8bad340ULL, 0x3c962c11e8a40ad2ULL},
    {0x3ff142cafdb09608ULL, 0x3c966a9fd58521a9ULL}, {0x3ff14be9cb12bdc0ULL, 0x3c885a343c5485fbULL},
    {0x3ff1550564d53092ULL, 0xbc8ce058ed7e93d0ULL}, {0x3ff15e1dcee38896ULL, 0x3c8123fe7a1a7bd7ULL},
    {0x3ff167330d212c6cULL, 0x3c91f5e56fd8fec6ULL}, {0x3ff1704523696772ULL, 0x3c74297a0754181bULL},
    {0x3ff17954158f81a1ULL, 0xbc83931aaaf9eceeULL}, {0x3ff1825fe75ed70fULL, 0x3c97c1650e442013ULL},
    {0x3ff18b689c9aef1bULL, 0xbc5fe12346e5ea6eULL}, {0x3ff1946e38ff9339ULL, 0x3c8bbd1599b05751ULL},
    {0x3ff19d70c040e574ULL, 0xbc76a738e8b97815ULL}, {0x3ff1a670360b7691ULL, 0xbc88b82e46253433ULL},
    {0x3ff1af6c9e045be7ULL, 0xbc978783955348fdULL}, {0x3ff1b865fbc944e1ULL, 0xbc8089615b8b52d5ULL},
    {0x3ff1c15c52f09034ULL, 0xbc90ba3be9f796f1ULL}, {0x3ff1ca4fa70960c2ULL, 0xbc8bc8c5ba599362ULL},
    {0x3ff1d33ffb9bb234ULL, 0x3c9ebd9bcfe75030ULL}, {0x3ff1dc2d54286d49ULL, 0x3c88b485c9915c5eULL},
    {0x3ff1e517b4297bd4ULL, 0xbc885abd73eb6c4fULL}, {0x3ff1edff1f11dc78ULL, 0x3c97c61c6ea44037ULL},
    {0x3ff1f6e3984db61dULL, 0xbc66ffa2b048ba14ULL}, {0x3ff1ffc523426b15ULL, 0x3c6fa25050e3deb5ULL},
    {0x3ff208a3c34eac08ULL, 0xbc912b927ce29451ULL}, {0x3ff2117f7bca8a92ULL, 0xbc9ad238c070110dULL},
    {0x3ff21a5850078ba4ULL, 0xbc713e3f78e88bb5ULL}, {0x3ff2232e4350b9a2ULL, 0x3c887254e3d50dbfULL},
    {0x3ff22c0158eab63fULL, 0xbc9ac5711778c4b6ULL}, {0x3ff234d19413cc17ULL, 0x3c972d916fb1ba76ULL},
    {0x3ff23d9ef8040016ULL, 0xbc9ada5333b2fd07ULL}, {0x3ff2466987ed228eULL, 0x3c9c41b95c46f732ULL},
    {0x3ff24f3146fae028ULL, 0x3c94576167337bfaULL}, {0x3ff257f63852d284ULL, 0x3c9ae415fef0477cULL},
    {0x3ff260b85f1490aeULL, 0x3c8006492afa66d0ULL}, {0x3ff26977be59bf51ULL, 0xbc706c72f5f43210ULL},
    {0x3ff27234593620b6ULL, 0x3c60352df8ba62ddULL}, {0x3ff27aee32b7a48aULL, 0x3c96361e602621b4ULL},
    {0x3ff283a54de6776eULL, 0x3c78f314e23a0911ULL}, {0x3ff28c59adc5124fULL, 0xbc9617522cef13e4ULL},
    {0x3ff2950b5550498cULL, 0xbc95f853435ed9e8ULL}, {0x3ff29dba477f5be8ULL, 0x3c8b9f4b8a6fd3f8ULL},
    {0x3ff2a66687440149ULL, 0x3c746ca0476e64f2ULL}, {0x3ff2af10178a7941ULL, 0xbc9b2c0b537438c7ULL},
    {0x3ff2b7b6fb399969ULL, 0x3c83bb0e5de6ddeaULL}, {0x3ff2c05b3532db8fULL, 0x3c95d00f9576c228ULL},
    {0x3ff2c8fcc8526bacULL, 0xbc804f4b184e8e91ULL}, {0x3ff2d19bb76f35afULL, 0xbc89ca76153e1f38ULL},
    {0x3ff2da38055af31cULL, 0x3c930668995338d1ULL}, {0x3ff2e2d1b4e2387cULL, 0xbc672fd9b0919917ULL},
    {0x3ff2eb68c8cc829bULL, 0x3c8d6b610ed98d90ULL}, {0x3ff2f3fd43dc43a4ULL, 0xbc869a28be7d007dULL},
    {0x3ff2fc8f28cef007ULL, 0xbc965fe287fc2f1bULL}, {0x3ff3051e7a5d0b3cULL, 0x3c7a9340662c2586ULL},
    {0x3ff30dab3b3a345aULL, 0x3c9240e354cce3e5ULL}, {0x3ff316356e153282ULL, 0xbc816b2187ff540aULL},
    {0x3ff31ebd15980122ULL, 0x3c8b87f6dd7bff60ULL}, {0x3ff327423467dc15ULL, 0x3c9e5ef51f32bc36ULL},
    {0x3ff32fc4cd254b95ULL, 0x3c81799bb9998b8eULL}, {0x3ff33844e26c3008ULL, 0xbc887862cc7ee49dULL},
    {0x3ff340c276d3cda9ULL, 0xbc915cac70cdbddfULL}, {0x3ff3493d8ceed80aULL, 0xbc97924244a2030fULL},
    {0x3ff351b6274b7d70ULL, 0xbc9c832a7a11c5bcULL}, {0x3ff35a2c4873720bULL, 0x3c824f102de1e508ULL},
    {0x3ff3629ff2ebfb0dULL, 0x3c5a5bf33b89f07bULL}, {0x3ff36b112935f997ULL, 0xbc894f08942110eeULL},
    {0x3ff3737fedcdf589ULL, 0x3c88127e6edd0a66ULL}, {0x3ff37bec432c2830ULL, 0xbc83d7c590fd34a8ULL},
    {0x3ff384562bc486cbULL, 0x3c9ad36a39919ff5ULL}, {0x3ff38cbdaa06ccfaULL, 0x3c930adc21fa4175ULL},
    {0x3ff39522c05e8701ULL, 0xbc9a86091d07c414ULL}, {0x3ff39d8571331bf0ULL, 0xbc89aa7f39be9163ULL},
    {0x3ff3a5e5bee7d7afULL, 0xbc8efc482d40a401ULL}, {0x3ff3ae43abdbf4e2ULL, 0x3c83108c8911518fULL},
    {0x3ff3b69f3a6aa6b6ULL, 0x3c8eb9cd943ad166ULL}, {0x3ff3bef86ceb228aULL, 0x3c8869ea23528010ULL},
    {0x3ff3c74f45b0a97dULL, 0x3c9acdbf59907625ULL}, {0x3ff3cfa3c70a91dfULL, 0x3c9db0998efa9c8eULL},
    {0x3ff3d7f5f3445083ULL, 0xbc8baacd926978daULL}, {0x3ff3e045cca581f3ULL, 0xbc768b41d278872cULL},
    {0x3ff3e8935571f38eULL, 0x3c9952a208d29718ULL}, {0x3ff3f0de8fe9ac85ULL, 0xbc71d8f11f7f2259ULL},
    {0x3ff3f9277e48f6baULL, 0x3c77dc62462b0ebfULL}, {0x3ff4016e22c8678dULL, 0x3c741aa98a84526aULL},
    {0x3ff409b27f9ce886ULL, 0xbc868d838699dc58ULL}, {0x3ff411f496f7bfe8ULL, 0xbc75db0a9b2b1ee3ULL},
    {0x3ff41a346b06992cULL, 0xbc96a88841b9d87fULL}, {0x3ff42271fdf38d5eULL, 0xbc98ca22cce3ceddULL},
    {0x3ff42aad51e52b65ULL, 0x3c88fcac10914ca8ULL}, {0x3ff432e668fe8032ULL, 0x3c933dfcee33a5a8ULL},
    {0x3ff43b1d455f1ed3ULL, 0xbc9266ee1358f782ULL}, {0x3ff44351e923286fULL, 0x3c996a0932440ecaULL},
    {0x3ff44b8456635432ULL, 0x3c7bf82f4f0a3bd9ULL}, {0x3ff453b48f34f714ULL, 0xbc978cee17d50cbaULL},
    {0x3ff45be295aa0b93ULL, 0xbc5209dcbd3e9de7ULL}, {0x3ff4640e6bd13956ULL, 0xbc77c139dd4d20ceULL},
    {0x3ff46c3813b5dcb3ULL, 0xbc45f6dd4df93692ULL}, {0x3ff4745f8f600e26ULL, 0xbc94a1828a42c561ULL},
    {0x3ff47c84e0d4a9adULL, 0xbc9cb5b161e3acd6ULL}, {0x3ff484a80a155612ULL, 0x3c7ef0e74c53ac13ULL},
    {0x3ff48cc90d208c20ULL, 0x3c9dc111455273e3ULL}, {0x3ff494e7ebf19dc0ULL, 0xbc12f7e23ebed86eULL},
    {0x3ff49d04a880bd02ULL, 0xbc95a7fb11302986ULL}, {0x3ff4a51f44c30315ULL, 0xbc88b0a16f4585e7ULL},
    {0x3ff4ad37c2aa7729ULL, 0x3c743e1d49993872ULL}, {0x3ff4b54e2426153dULL, 0xbc9d1b602f0d41a1ULL},
    {0x3ff4bd626b21d4d6ULL, 0x3c971943f3831e35ULL}, {0x3ff4c5749986afaeULL, 0x3c8d59c659500857ULL},
    {0x3ff4cd84b13aa841ULL, 0xbc74a7e5d2acff7aULL}, {0x3ff4d592b420d052ULL, 0x3c799b35906430a7ULL},
    {0x3ff4dd9ea4194f5cULL, 0xbc90578c99ff1fc1ULL}, {0x3ff4e5a8830168ebULL, 0x3c96a7a989acc063ULL},
    {0x3ff4edb052b382edULL, 0x3c8f541daecef0baULL}, {0x3ff4f5b615072be6ULL, 0x3c82899e52ea0d04ULL},
    {0x3ff4fdb9cbd1211bULL, 0x3c954d56592ced0aULL}, {0x3ff505bb78e354aaULL, 0xbc9c60e8a30c2f71ULL},
    {0x3ff50dbb1e0cf38bULL, 0xbc645b2b517237a6ULL}, {0x3ff515b8bd1a6b8cULL, 0x3c8facadb9d1fe22ULL},
    {0x3ff51db457d57131ULL, 0x3c93673fe6f36f97ULL}, {0x3ff525adf0050589ULL, 0x3c9f9d6c8c82c888ULL},
    {0x3ff52da5876d7bf4ULL, 0xbc81868a5d368672ULL}, {0x3ff5359b1fd07fd3ULL, 0x3c9bb1e0a5ab4a6dULL},
    {0x3ff53d8ebaed1a34ULL, 0xbc86943c1d9ff947ULL}, {0x3ff545805a7fb75eULL, 0x3c996c69481ffaaaULL},
    {0x3ff54d7000422c60ULL, 0x3c7febee302d3401ULL}, {0x3ff5555dadebbc80ULL, 0x3c98636ab6cec882ULL},
    {0x3ff55d4965311ea9ULL, 0xbc818d77935a1064ULL}, {0x3ff5653327c482bfULL, 0xbc86cf925e672dbcULL},
    {0x3ff56d1af75596eeULL, 0xbc88dee3584c27daULL}, {0x3ff57500d5918ce4ULL, 0x3c783b8f0e100daeULL},
    {0x3ff57ce4c4231f01ULL, 0x3c514fae10701c52ULL}, {0x3ff584c6c4b29575ULL, 0x3c94eb75566e9c2cULL},
    {0x3ff58ca6d8e5cb56ULL, 0xbc8672f7533ffbe1ULL}, {0x3ff59485026033a0ULL, 0x3c992b0ee26c85e4ULL},
    {0x3ff59c6142c2de34ULL, 0xbc97ca26e6d5db8fULL}, {0x3ff5a43b9bac7cb9ULL, 0x3c8d7627d5281ba7ULL},
    {0x3ff5ac140eb96783ULL, 0x3c950a587600c6acULL}, {0x3ff5b3ea9d83a25dULL, 0xbc781a52bdc6f79cULL},
    {0x3ff5bbbf49a2e14dULL, 0x3c9eaf364a109700ULL}, {0x3ff5c39214ac8d50ULL, 0x3c8b005ea6654396ULL},
    {0x3ff5cb630033c8ffULL, 0xbc99fa22a80a334cULL}, {0x3ff5d3320dc9752fULL, 0xbc7e2ead1dedffdbULL},
    {0x3ff5daff3efc3586ULL, 0x3c9a0a591d52bccfULL}, {0x3ff5e2ca95587500ULL, 0xbc6d658d21091e06ULL},
    {0x3ff5ea9412686a66ULL, 0x3c90cd42bab3d656ULL}, {0x3ff5f25bb7b41cc3ULL, 0x3c6308f75b6397a5ULL},
    {0x3ff5fa2186c167c2ULL, 0x3c8beed0cfe96890ULL}, {0x3ff601e58114000aULL, 0x3c6a87f3b027d65cULL},
    {0x3ff609a7a82d7788ULL, 0xbc81ae642ad30586ULL}, {0x3ff61167fd8d41b2ULL, 0xbc907e5f0ee166fbULL},
    {0x3ff6192682b0b7bdULL, 0x3c92e1ebba141273ULL}, {0x3ff620e339131cccULL, 0xbc9ce13dc44b552aULL},
    {0x3ff6289e222da20aULL, 0x3c886df6c14335f7ULL}, {0x3ff630573f776acaULL, 0x3c8f3fd0d443e655ULL},
    {0x3ff6380e9265908cULL, 0x3c9445f14eb80cc8ULL}, {0x3ff63fc41c6b2703ULL, 0xbc9c9b2a196d7620ULL},
    {0x3ff64777def94008ULL, 0x3c9a3d4541857f9cULL}, {0x3ff64f29db7eef90ULL, 0x3c988fee1691bb31ULL},
    {0x3ff656da13694f88ULL, 0xbc88adcb1c6b7a55ULL}, {0x3ff65e88882383b1ULL, 0xbc84a9598442289bULL},
    {0x3ff666353b16bd73ULL, 0xbc8ea9289ab72a96ULL}, {0x3ff66de02daa3fa1ULL, 0xbc92eb51320bb6b9ULL},
    {0x3ff6758961436237ULL, 0xbc753d21bd6b7151ULL}, {0x3ff67d30d745960fULL, 0xbc946c426590a1d0ULL},
    {0x3ff684d691126889ULL, 0x3c13d0cd2e6aeb33ULL}, {0x3ff68c7a90098730ULL, 0x3c85af3b8a7356c8ULL},
    {0x3ff6941cd588c350ULL, 0x3c93efe027bb0719ULL}, {0x3ff69bbd62ec1587ULL, 0x3c5d59d09ef24427ULL},
    {0x3ff6a35c398da14aULL, 0x3c8e1d3a21420385ULL}, {0x3ff6aaf95ac5b866ULL, 0x3c93216173cad02eULL},
    {0x3ff6b294c7eade74ULL, 0xbc9a9609110c2f60ULL}, {0x3ff6ba2e8251cc44ULL, 0xbc9fb66c029f11fcULL},
    {0x3ff6c1c68b4d7345ULL, 0x3c8627b589a76cd8ULL}, {0x3ff6c95ce42f00e2ULL, 0xbc8df43e01c10890ULL},
    {0x3ff6d0f18e45e1d1ULL, 0xbc948338afc32036ULL}, {0x3ff6d8848adfc564ULL, 0xbc9a7453ed5dcdbeULL},
    {0x3ff6e015db48a0caULL, 0x3c9efb221633a3e2ULL}, {0x3ff6e7a580cab250ULL, 0xbc86b1ef1140f183ULL},
    {0x3ff6ef337cae848dULL, 0xbc87caa806ca3092ULL}, {0x3ff6f6bfd03af196ULL, 0x3c2b3d60a823db85ULL},
    {0x3ff6fe4a7cb52620ULL, 0x3c892c8daea31678ULL}, {0x3ff705d38360a49eULL, 0xbc8549cb18899832ULL},
    {0x3ff70d5ae57f4855ULL, 0xbc7c602516982ad3ULL}, {0x3ff714e0a451486dULL, 0x3c990d7bdaf451b7ULL},
    {0x3ff71c64c1153af9ULL, 0xbc96f2937269bb99ULL}, {0x3ff723e73d0817f1ULL, 0x3c8b987d591ed7bfULL},
    {0x3ff72b6819653c34ULL, 0xbc8517154ca955cdULL}, {0x3ff732e757666c71ULL, 0x3c877aaae925f74cULL},
    {0x3ff73a64f843d819ULL, 0xbc900b5e22bfb8ccULL}, {0x3ff741e0fd341c3dULL, 0xbc8c4d1e6ee99295ULL},
    {0x3ff7495b676c466fULL, 0x3c9a44d50e1bd6fcULL}, {0x3ff750d4381fd799ULL, 0x3c72301252f03663ULL},
    {0x3ff7584b7080c6c8ULL, 0x3c8aedad511ccba7ULL}, {0x3ff75fc111bf83faULL, 0x3c9c94e8e884e269ULL},
    {0x3ff767351d0afadfULL, 0x3c8956dcdbd0965fULL}, {0x3ff76ea793909594ULL, 0xbc8034bc90291144ULL},
    {0x3ff77618767c3f5aULL, 0xbc939dfa5e210342ULL}, {0x3ff77d87c6f86745ULL, 0x3c8b4e264bb8383fULL},
    {0x3ff784f5862e02e8ULL, 0xbc98856029b5715fULL}, {0x3ff78c61b54490f2ULL, 0xbc82ef9a7b371394ULL},
    {0x3ff793cc55621bd2ULL, 0xbc94cc5e221e8fc6ULL}, {0x3ff79b3567ab3c49ULL, 0xbc95194fffa06645ULL},
    {0x3ff7a29ced431bfdULL, 0x3c9419fa290c5c9bULL}, {0x3ff7aa02e74b7806ULL, 0x3c8296a1dcc91fb3ULL},
    {0x3ff7b16756e4a36fULL, 0x3c7c167fb53d7644ULL}, {0x3ff7b8ca3d2d89b9ULL, 0x3c82217f6f52fadeULL},
    {0x3ff7c02b9b43b154ULL, 0x3c668ff2335067e7ULL}, {0x3ff7c78b72433e13ULL, 0xbc91273296d1f71aULL},
    {0x3ff7cee9c346f39aULL, 0xbc79e88b34adaacfULL}, {0x3ff7d6468f6837c9ULL, 0x3c855be237b411dcULL},
    {0x3ff7dda1d7bf151fULL, 0xbc8be60eb337bd33ULL}, {0x3ff7e4fb9d623d16ULL, 0xbc76ba845d61accdULL},
    {0x3ff7ec53e1670a80ULL, 0xbc9984e150581d1cULL}, {0x3ff7f3aaa4e183d6ULL, 0x3c9d3df2216ae51aULL},
    {0x3ff7faffe8e45d8dULL, 0x3c7827b06617d8faULL}, {0x3ff80253ae80fc57ULL, 0x3c9b51ee2820d7e3ULL},
    {0x3ff809a5f6c7776fULL, 0xbc84c8813ee10874ULL}, {0x3ff810f6c2c69ad1ULL, 0x3c92da0543776aa1ULL},
    {0x3ff81846138be97bULL, 0x3c9d85084e9fa6e3ULL}, {0x3ff81f93ea239f9eULL, 0xbc8247ff39ef9544ULL},
    {0x3ff826e04798b4cdULL, 0x3c7eb6863467a889ULL}, {0x3ff82e2b2cf4de2dULL, 0x3c9afbc71a5a6ab5ULL},
    {0x3ff835749b409099ULL, 0x3c770da27c1a6cd9ULL}, {0x3ff83cbc938302c2ULL, 0x3c9f2779f2695e47ULL},
  },
  {
    {0x3ff266947ef6e3f0ULL, 0x3c9428ebc88a62e6ULL}, {0x3ff271972398c4edULL, 0xbc9d203ebceb8c71ULL},
    {0x3ff27c956834d269ULL, 0xbc9d1371b41f5ffcULL}, {0x3ff2878f52dab8f4ULL, 0xbc376829a5fffa8dULL},
    {0x3ff29284e98bce22ULL, 0x3c8d6a36b2db1059ULL}, {0x3ff29d76323b406bULL, 0xbc93a9dd1c498a36ULL},
    {0x3ff2a86332ce463bULL, 0x3c92bdec399c9e28ULL}, {0x3ff2b34bf11c4c41ULL, 0xbc6e14ce0e3716a5ULL},
    {0x3ff2be3072ef22eaULL, 0x3c985d7e7394efa6ULL}, {0x3ff2c910be032b29ULL, 0x3c962dcf352b9d01ULL},
    {0x3ff2d3ecd8078276ULL, 0xbc3510508ea0369aULL}, {0x3ff2dec4c69e2e18ULL, 0x3c9c1fc553e3ca27ULL},
    {0x3ff2e9988f5c45bcULL, 0x3c82db8ce745af7eULL}, {0x3ff2f46837ca1d51ULL, 0xbc82c3e0d1067464ULL},
    {0x3ff2ff33c5636e3dULL, 0xbc9baaa315fffda2ULL}, {0x3ff309fb3d977fe2ULL, 0x3c8513f37452164bULL},
    {0x3ff314bea5c94f80ULL, 0xbc63f41f5c0d13b6ULL}, {0x3ff31f7e034fb76aULL, 0xbc98fb70ec77110bULL},
    {0x3ff32a395b7595a1ULL, 0xbc9c4460c7e97749ULL}, {0x3ff334f0b379f1ceULL, 0x3c8f9de43a8c7d06ULL},
    {0x3ff33fa4109022a3ULL, 0x3c825b66a4ab5d9fULL}, {0x3ff34a5377dff29eULL, 0xbc96b737ad98bbcfULL},
    {0x3ff354feee85c43cULL, 0xbc88d258fe14e362ULL}, {0x3ff35fa67992b59bULL, 0xbc8c447f92aa893cULL},
    {0x3ff36a4a1e0cc387ULL, 0xbc89fad24b73e7bbULL}, {0x3ff374e9e0eeebfeULL, 0x3c9d014e21a1b081ULL},
    {0x3ff37f85c729502cULL, 0xbc555042b747357bULL}, {0x3ff38a1dd5a155d7ULL, 0x3c83c0b1e623da3cULL},
    {0x3ff394b21131c852ULL, 0x3c9b30371c813570ULL}, {0x3ff39f427eaaf8e6ULL, 0xbc8fe6fb3026e40aULL},
    {0x3ff3a9cf22d2debaULL, 0xbc96d40314b6df3bULL}, {0x3ff3b45802653645ULL, 0xbc89ab60d918fafbULL},
    {0x3ff3bedd2213a03fULL, 0xbc93f55bab593177ULL}, {0x3ff3c95e8685c019ULL, 0x3c98ea139557571bULL},
    {0x3ff3d3dc34595a05ULL, 0xbc704793b17c8a45ULL}, {0x3ff3de563022707eULL, 0x3c974f75dc1b4a8fULL},
    {0x3ff3e8cc7e6b616dULL, 0xbc98b5991ecba796ULL}, {0x3ff3f33f23b502cdULL, 0x3c99ba430abbcfa8ULL},
    {0x3ff3fdae2476bef4ULL, 0x3c7cd8c6d248c5f9ULL}, {0x3ff40819851eb05dULL, 0xbc9157da441f217eULL},
    {0x3ff412814a11bd15ULL, 0xbc8ce717bf1ad869ULL}, {0x3ff41ce577abb1bcULL, 0x3c889f45e379e64cULL},
    {0x3ff42746123f5c20ULL, 0x3c6cc497ed4231d3ULL}, {0x3ff431a31e16a571ULL, 0xbc6a4be17f4bebb2ULL},
    {0x3ff43bfc9f72ac17ULL, 0xbc8637a9866fa018ULL}, {0x3ff446529a8bdd24ULL, 0x3c813575cea857cfULL},
    {0x3ff450a513920d6aULL, 0xbc78dce959c13f79ULL}, {0x3ff45af40eac922fULL, 0xbc9e96e97faea8adULL},
    {0x3ff4653f8ffa5989ULL, 0xbc82a76f50c8c322ULL}, {0x3ff46f879b920261ULL, 0x3c93ace28148b1f1ULL},
    {0x3ff479cc3581f41aULL, 0x3c9d7884d7af52d7ULL}, {0x3ff4840d61d075e3ULL, 0xbc89ce30c75df09dULL},
    {0x3ff48e4b247bc5b1ULL, 0x3c74d3004d7b2821ULL}, {0x3ff49885817a2eedULL, 0xbc844abed3b81339ULL},
    {0x3ff4a2bc7cba20c4ULL, 0x3c9e0e51026e79c6ULL}, {0x3ff4acf01a224432ULL, 0x3c94c38d6242357cULL},
    {0x3ff4b7205d9191b2ULL, 0x3c910f41514fb05dULL}, {0x3ff4c14d4adf66a9ULL, 0xbc3f866408003621ULL},
    {0x3ff4cb76e5db9a7fULL, 0xbc9f2dab0d8b2553ULL}, {0x3ff4d59d324e936dULL, 0x3c78ff2cf4e38841ULL},
    {0x3ff4dfc033f95b06ULL, 0xbc5a4151871ddc89ULL}, {0x3ff4e9dfee95b26dULL, 0x3c6a0cf8d5118c6dULL},
    {0x3ff4f3fc65d6264dULL, 0xbc798fcd24fa5510ULL}, {0x3ff4fe159d662284ULL, 0x3c8c91199434d4f7ULL},
    {0x3ff5082b98ea058eULL, 0xbc52ffb993dac0acULL}, {0x3ff5123e5bff33a5ULL, 0x3c976e7274c07937ULL},
    {0x3ff51c4dea3c29a7ULL, 0xbc901cf8c6c44261ULL}, {0x3ff5265a47308fafULL, 0xbc9130b1be514284ULL},
    {0x3ff5306376654b78ULL, 0x3c9a00a839398e7aULL}, {0x3ff53a697b5c927cULL, 0xbc7d8ec58ebf0737ULL},
    {0x3ff5446c5991fbceULL, 0x3c8596513335e23eULL}, {0x3ff54e6c147a91c3ULL, 0x3c992fa19e00929aULL},
    {0x3ff55868af84e354ULL, 0x3c9d24437b8ad1f7ULL}, {0x3ff562622e191549ULL, 0x3c57dddb6a99adacULL},
    {0x3ff56c589398f327ULL, 0xbc76c2bd7ddc74f5ULL}, {0x3ff5764be35fffe8ULL, 0xbc8e111391f5e9d5ULL},
    {0x3ff5803c20c38676ULL, 0x3c425dcb3622c694ULL}, {0x3ff58a294f12a9f2ULL, 0xbc61e3272fc31afbULL},
    {0x3ff59413719675c0ULL, 0x3c6cf18aff4ddc36ULL}, {0x3ff59dfa8b91ed61ULL, 0xbc58cc060682b9b7ULL},
    {0x3ff5a7dea0421c15ULL, 0xbc93ebb909c5b6ddULL}, {0x3ff5b1bfb2de2449ULL, 0x3c804da5ab6650efULL},
    {0x3ff5bb9dc6974ed5ULL, 0x3c9a0eb9bb917526ULL}, {0x3ff5c578de991a02ULL, 0x3c98f5b89895a808ULL},
    {0x3ff5cf50fe094861ULL, 0x3c997945f00868a3ULL}, {0x3ff5d9262807ef72ULL, 0xbc80e0b496d1294aULL},
    {0x3ff5e2f85faf8617ULL, 0xbc91bd2f1d531bd2ULL}, {0x3ff5ecc7a814f2dcULL, 0x3c8be51441311810ULL},
    {0x3ff5f69404479a0fULL, 0x3c4cdb5030e96161ULL}, {0x3ff6005d77516ba5ULL, 0x3c8a321e18029c58ULL},
    {0x3ff60a240436f0faULL, 0x3c53b09d81524d97ULL}, {0x3ff613e7adf75a5dULL, 0xbc775336aeffbf59ULL},
    {0x3ff61da8778c8c75ULL, 0xbc92d195d4f9e408ULL}, {0x3ff6276663eb2d78ULL, 0xbc9d86f52efbf0f3ULL},
    {0x3ff631217602b238ULL, 0x3c8587ee570c5459ULL}, {0x3ff63ad9b0bd6b09ULL, 0x3c99e321f8723ddeULL},
    {0x3ff6448f17009078ULL, 0x3c8f1ee4b1691af5ULL}, {0x3ff64e41abac4fddULL, 0x3c96d6927904f789ULL},
    {0x3ff657f1719bd7c7ULL, 0xbc9c18281d4dec29ULL}, {0x3ff6619e6ba56439ULL, 0xbc8183fd8d7e429dULL},
    {0x3ff66b489c9a4accULL, 0xbc938e1d8f994411ULL}, {0x3ff674f00747069eULL, 0xbc76b740a84f6062ULL},
    {0x3ff67e94ae734425ULL, 0x3c8260a679cc492aULL}, {0x3ff6883694e1ecd8ULL, 0x3c6d4bfad1f811beULL},
    {0x3ff691d5bd5132b4ULL, 0x3c7637dada1631feULL}, {0x3ff69b722a7a9b9fULL, 0x3c87cd4199e9b9e4ULL},
    {0x3ff6a50bdf130ca6ULL, 0x3c80f4f9b7a93b1dULL}, {0x3ff6aea2ddcad518ULL, 0xbc7597344d7c9367ULL},
    {0x3ff6b837294db97fULL, 0xbc91a0226d4fddf4ULL}, {0x3ff6c1c8c442fe77ULL, 0x3c67e0b95abd6e78ULL},
    {0x3ff6cb57b14d7365ULL, 0x3c981749e37d0e21ULL}, {0x3ff6d4e3f30b7d0bULL, 0x3c5bf28bbe19660fULL},
    {0x3ff6de6d8c171ffbULL, 0xbc9e34000537d9a1ULL}, {0x3ff6e7f47f060aecULL, 0x3c7480908ba9c74fULL},
    {0x3ff6f178ce69a0f3ULL, 0xbc9d62e0b99a010dULL}, {0x3ff6fafa7ccf0391ULL, 0x3c9926456bfc8838ULL},
    {0x3ff704798cbf1cb4ULL, 0x3c830e0461478ca4ULL}, {0x3ff70df600bea888ULL, 0xbc976b9351bcd88dULL},
    {0x3ff7176fdb4e3f36ULL, 0xbc9a9a93cc6abae9ULL}, {0x3ff720e71eea5e83ULL, 0xbc4fa2bcf6d29a79ULL},
    {0x3ff72a5bce0b7352ULL, 0xbc9b85db182720b3ULL}, {0x3ff733cdeb25e305ULL, 0xbc78e759d45e29ebULL},
    {0x3ff73d3d78aa14cbULL, 0x3c9b92b2a7a08cfaULL}, {0x3ff746aa79047accULL, 0xbc72575f83800fdbULL},
    {0x3ff75014ee9d9b38ULL, 0xbc928ddc5a681261ULL}, {0x3ff7597cdbda1942ULL, 0x3c3b6be42188611bULL},
    {0x3ff762e2431abdfdULL, 0xbc7eb687e8bfc605ULL}, {0x3ff76c4526bc811cULL, 0x3c6aaa6770a918e1ULL},
    {0x3ff775a58918919eULL, 0x3c4de45da684c265ULL}, {0x3ff77f036c845e5cULL, 0xbc8c1c001324eb8eULL},
    {0x3ff7885ed3519e80ULL, 0xbc9795ca1b8d4524ULL}, {0x3ff791b7bfce59e3ULL, 0x3c8b44b047b3795dULL},
    {0x3ff79b0e3444f155ULL, 0x3c9444c28ce29f28ULL}, {0x3ff7a46232fc26c8ULL, 0xbc93c7eb2a324c24ULL},
    {0x3ff7adb3be372565ULL, 0x3c8af27f4b02645dULL}, {0x3ff7b702d8358991ULL, 0xbc9123676fa7c61dULL},
    {0x3ff7c04f833368cdULL, 0xbc65c072235ae62fULL}, {0x3ff7c999c169598eULL, 0xbc985e20b21ec6d3ULL},
    {0x3ff7d2e1950c7af2ULL, 0x3c935e1f33cbafdbULL}, {0x3ff7dc27004e7c6bULL, 0x3c8a78ec986390efULL},
    {0x3ff7e56a055da548ULL, 0x3c82fc806ba66e28ULL}, {0x3ff7eeaaa664dc32ULL, 0x3c7a1d7150968615ULL},
    {0x3ff7f7e8e58bae90ULL, 0xbc9b6ef4f7935fa4ULL}, {0x3ff80124c4f657d4ULL, 0x3c7322a642555804ULL},
    {0x3ff80a5e46c5c8bbULL, 0x3c5e901b32089de8ULL}, {0x3ff813956d17ae6eULL, 0x3c94130cb908a882ULL},
    {0x3ff81cca3a067999ULL, 0xbc8d3ae0779b1dd4ULL}, {0x3ff825fcafa96565ULL, 0xbc6c6167867edd21ULL},
    {0x3ff82f2cd0147e68ULL, 0x3c91c9def9d42842ULL}, {0x3ff8385a9d58a97bULL, 0x3c7300681d52733dULL},
    {0x3ff841861983aa7dULL, 0x3c9c6ed359c2bfa2ULL}, {0x3ff84aaf46a02b0aULL, 0xbc9f57d0d96e5e3bULL},
    {0x3ff853d626b5c113ULL, 0x3c7bc81e8c661990ULL}, {0x3ff85cfabbc8f575ULL, 0x3c8e433d5d76b9c0ULL},
    {0x3ff8661d07db4a6dULL, 0x3c9eff6cdfdf54eeULL}, {0x3ff86f3d0ceb4206ULL, 0xbc93e41474fe97faULL},
    {0x3ff8785accf4646cULL, 0x3c660f17e06e8821ULL}, {0x3ff8817649ef463aULL, 0xbc7d21e559f9ab61ULL},
    {0x3ff88a8f85d18ea9ULL, 0x3c9a4579069c2e98ULL}, {0x3ff893a6828dfdbaULL, 0x3c9fc1aa4793d7b8ULL},
    {0x3ff89cbb42147247ULL, 0xbc797071db751d81ULL}, {0x3ff8a5cdc651f006ULL, 0x3c4e55a37c3d3573ULL},
    {0x3ff8aede1130a580ULL, 0x3c99a11611f8935fULL}, {0x3ff8b7ec2497f1f3ULL, 0x3c9440af9660e1b4ULL},
    {0x3ff8c0f8026c6b24ULL, 0x3c9c36cb20e523beULL}, {0x3ff8ca01ac8fe326ULL, 0xbc41e9b04f3fe033ULL},
    {0x3ff8d30924e16e0bULL, 0x3c9c601f291c6526ULL}, {0x3ff8dc0e6d3d678fULL, 0x3c66bd3912a018ddULL},
    {0x3ff8e511877d78a8ULL, 0x3c942e23822bf0dfULL}, {0x3ff8ee1275789d14ULL, 0xbc911fc367fb06a5ULL},
    {0x3ff8f711390328ccULL, 0xbc8c8f78cc9b40e5ULL}, {0x3ff9000dd3eecd74ULL, 0xbc9da9b0f908af9cULL},
    {0x3ff90908480a9fb3ULL, 0x3c6629447f1f3932ULL}, {0x3ff9120097231c86ULL, 0xbc9e640263d1e0edULL},
    {0x3ff91af6c3022e7aULL, 0xbc8ffe2ada2155f6ULL}, {0x3ff923eacd6f32e5ULL, 0xbc974a9f1ff66102ULL},
    {0x3ff92cdcb82eff06ULL, 0x3c932b0cae2f2af0ULL}, {0x3ff935cc8503e522ULL, 0xbc9289c249ba387cULL},
    {0x3ff93eba35adb987ULL, 0x3c7f27ab1cd481b5ULL}, {0x3ff947a5cbe9d791ULL, 0x3c9c012e408471a6ULL},
    {0x3ff9508f49732697ULL, 0xbc946d70c9a5b09cULL}, {0x3ff95976b0021eccULL, 0xbc91dd7406c17985ULL},
    {0x3ff9625c014cce1bULL, 0x3c9ac4a3fcb1d363ULL}, {0x3ff96b3f3f06dcf1ULL, 0x3c95d48d5c9ea5eaULL},
    {0x3ff974206ae192f8ULL, 0x3c8a58a4c7901db4ULL}, {0x3ff97cff868bdbccULL, 0x3c88af84bdbb870fULL},
    {0x3ff985dc93b24ba1ULL, 0x3c9241ebb3ba56a6ULL}, {0x3ff98eb793ff23deULL, 0xbc8c938ea41c7122ULL},
    {0x3ff99790891a57a9ULL, 0x3c77b10752a0caffULL}, {0x3ff9a06774a9906fULL, 0x3c70cdd453005f1fULL},
    {0x3ff9a93c58503258ULL, 0xbc889b645fa6e863ULL}, {0x3ff9b20f35af60b4ULL, 0x3c940c0440e40481ULL},
    {0x3ff9bae00e660260ULL, 0xbc7182c0521f2f58ULL}, {0x3ff9c3aee410c617ULL, 0xbc841dd2fe4b1ef1ULL},
    {0x3ff9cc7bb84a26c2ULL, 0xbc95495c039efa72ULL}, {0x3ff9d5468caa6fb6ULL, 0x3c95d44f846053d5ULL},
    {0x3ff9de0f62c7c0eeULL, 0x3c988738278b1bcfULL}, {0x3ff9e6d63c361333ULL, 0xbc942cf5644514d7ULL},
    {0x3ff9ef9b1a873c3dULL, 0xbc6e83e59d51785aULL}, {0x3ff9f85dff4af2cfULL, 0xbc8356c7f781f1d3ULL},
    {0x3ffa011eec0ed2bfULL, 0x3c89d010246d69c3ULL}, {0x3ffa09dde25e60fdULL, 0xbc54d35444fe437aULL},
    {0x3ffa129ae3c30f89ULL, 0xbc9b15affe0b6ae3ULL}, {0x3ffa1b55f1c44163ULL, 0x3c90fd7d0bb13f63ULL},
    {0x3ffa240f0de74e75ULL, 0x3c53ba9e0a55d52bULL}, {0x3ffa2cc639af8769ULL, 0xbc88dd40f097037cULL},
    {0x3ffa357b769e397fULL, 0x3c9d7d0a05538f1cULL}, {0x3ffa3e2ec632b259ULL, 0x3c90448b3fa5ea67ULL},
    {0x3ffa46e029ea43b6ULL, 0x3c905bc08740278dULL}, {0x3ffa4f8fa340472eULL, 0xbc992c696e217d12ULL},
    {0x3ffa583d33ae21dcULL, 0xbc88dd9578f6c5deULL}, {0x3ffa60e8dcab4808ULL, 0x3c7bd46f9fe3eeedULL},
    {0x3ffa69929fad40c1ULL, 0x3c83056b723845deULL}, {0x3ffa723a7e27a971ULL, 0xbc7ff80fe82081beULL},
    {0x3ffa7ae0798c3968ULL, 0xbc76076ab3897354ULL}, {0x3ffa8384934ac560ULL, 0x3c9c6e25b82e7b88ULL},
    {0x3ffa8c26ccd142f9ULL, 0xbc93c21d0e32c35fULL}, {0x3ffa94c7278bcc25ULL, 0x3c80b2e90934fbb6ULL},
    {0x3ffa9d65a4e4a29aULL, 0x3c9fc69457180334ULL}, {0x3ffaa60246443330ULL, 0xbc93bc7b30c9e3abULL},
    {0x3ffaae9d0d111938ULL, 0xbc9431dab9a8884dULL}, {0x3ffab735fab021d3ULL, 0x3c9f61b314cfd61dULL},
    {0x3ffabfcd10844f3cULL, 0x3c94a5cb1cb1cc81ULL}, {0x3ffac8624feedc06ULL, 0x3c2ad219648508f1ULL},
    {0x3ffad0f5ba4f3e5aULL, 0xbc91ecd3556d1b82ULL}, {0x3ffad98751032b29ULL, 0x3c8b8d668900c9c4ULL},
    {0x3ffae2171566995aULL, 0x3c9f990c79285d4dULL}, {0x3ffaeaa508d3c4ecULL, 0x3c80876e968e1727ULL},
    {0x3ffaf3312ca33212ULL, 0x3c90605f26ee22ceULL}, {0x3ffafbbb822bb04cULL, 0x3c94cf399de3a972ULL},
    {0x3ffb04440ac25d74ULL, 0xbc92c5da3225a13cULL}, {0x3ffb0ccac7baa8c3ULL, 0x3c8b923d71ecc5d4ULL},
    {0x3ffb154fba6655d8ULL, 0xbc96f47f5a10beddULL}, {0x3ffb1dd2e4157fa9ULL, 0x3c9708d292df04b6ULL},
    {0x3ffb265446169b7fULL, 0x3c796cdb07984346ULL}, {0x3ffb2ed3e1b67bdaULL, 0xbc6ed5459dc697f2ULL},
    {0x3ffb3751b840535bULL, 0xbc985a6ba004a47aULL}, {0x3ffb3fcdcafdb7a0ULL, 0x3c8c30d0859714c1ULL},
    {0x3ffb48481b36a420ULL, 0x3c938c605fc95d64ULL}, {0x3ffb50c0aa317cf9ULL, 0xbc9ac54e875124f4ULL},
    {0x3ffb5937793311baULL, 0x3c83d09d22cc7800ULL}, {0x3ffb61ac897ea02eULL, 0x3c9cc48552cd18d3ULL},
    {0x3ffb6a1fdc55d716ULL, 0xbc81a9130cebb29bULL}, {0x3ffb729172f8d8e0ULL, 0x3c8b4898f41cabd9ULL},
    {0x3ffb7b014ea63e5fULL, 0x3c7193538ef98003ULL}, {0x3ffb836f709b1972ULL, 0xbc3a79ac246a1542ULL},
    {0x3ffb8bdbda12f7adULL, 0xbc88f07c3c47a5f4ULL}, {0x3ffb94468c47e4f8ULL, 0xbc7c364d03be5eb7ULL},
    {0x3ffb9caf88726e2bULL, 0xbc96a445a6e7999aULL}, {0x3ffba516cfc9a3a0ULL, 0x3c7e8655c4a92f27ULL},
    {0x3ffbad7c63831bc6ULL, 0xbc7d6b27a106518cULL}, {0x3ffbb5e044d2f5a5ULL, 0x3c900188244b0467ULL},
    {0x3ffbbe4274ebdb67ULL, 0xbc86a8129c7d3d3bULL}, {0x3ffbc6a2f4ff04d1ULL, 0xbc9eadd9a0d5e679ULL},
    {0x3ffbcf01c63c39beULL, 0x3c70eb7a74039ff0ULL}, {0x3ffbd75ee9d1d494ULL, 0x3c63223368bdb144ULL},
  },
  {
    {0x3ff523091b074d49ULL, 0xbc8777a0015db4f5ULL}, {0x3ff52faee0530575ULL, 0xbc962e0b0da0d5f6ULL},
    {0x3ff53c4f9f0d4181ULL, 0xbc9eab5670d92ca4ULL}, {0x3ff548eb5e2c6938ULL, 0xbc796313b82dfa96ULL},
    {0x3ff5558224966b8bULL, 0x3c95936feb788521ULL}, {0x3ff56213f920f58fULL, 0x3c98b8eff97f8ca7ULL},
    {0x3ff56ea0e291a88fULL, 0xbc827a8193278348ULL}, {0x3ff57b28e79e4f35ULL, 0x3c88ac13634f1325ULL},
    {0x3ff587ac0eed11d6ULL, 0xbc8cd38ea17167a1ULL}, {0x3ff5942a5f14a9d5ULL, 0xbc913e8641685eadULL},
    {0x3ff5a0a3de9c9436ULL, 0xbc877718bf70d3d0ULL}, {0x3ff5ad1893fd4356ULL, 0xbc8e9b98d3634cf1ULL},
    {0x3ff5b98885a04fd2ULL, 0x3c984cd0a6a4edf8ULL}, {0x3ff5c5f3b9e0a8a6ULL, 0xbc94c5afd1feb160ULL},
    {0x3ff5d25a370ac278ULL, 0x3c51e844557897b9ULL}, {0x3ff5debc035cc62dULL, 0x3c9a9c7a8ed35d3dULL},
    {0x3ff5eb192506beb2ULL, 0xbc899181758a7dacULL}, {0x3ff5f771a22ac608ULL, 0x3c8051beb92cf0b0ULL},
    {0x3ff603c580dd31a0ULL, 0x3c68735ac614b85aULL}, {0x3ff61014c724bdf6ULL, 0xbc8c91f6992dba45ULL},
    {0x3ff61c5f7afab980ULL, 0xbc91067a67b9ce8eULL}, {0x3ff628a5a24b2eedULL, 0x3c9b2eed316fe338ULL},
    {0x3ff634e742f50ebbULL, 0xbc618dab6ef9ab0bULL}, {0x3ff6412462ca581dULL, 0xbc9b57afef1453dbULL},
    {0x3ff64d5d07904145ULL, 0x3c9063fc7125f8faULL}, {0x3ff6599136ff5f0cULL, 0xbc7b78923ef834c2ULL},
    {0x3ff665c0f6c3cbf2ULL, 0xbc8ce16cb3cf1e56ULL}, {0x3ff671ec4c7d4e8eULL, 0xbc95ca0a0586f6b4ULL},
    {0x3ff67e133dbf7f5eULL, 0x3c9274a318a45f91ULL}, {0x3ff68a35d011ee07ULL, 0x3c904c0ad7a5bb20ULL},
    {0x3ff6965408f045fbULL, 0x3c70138634040b29ULL}, {0x3ff6a26dedca7295ULL, 0x3c8152f7c7e0d765ULL},
    {0x3ff6ae838404c2a6ULL, 0x3c9e5dba400e23a5ULL}, {0x3ff6ba94d0f80b78ULL, 0xbc98362d4bfdaa2bULL},
    {0x3ff6c6a1d9f1cb43ULL, 0xbc9ff06198bcce48ULL}, {0x3ff6d2aaa4344b27ULL, 0xbc94e288a7c7c9c1ULL},
    {0x3ff6deaf34f6c09aULL, 0x3c9ea4c42416c44bULL}, {0x3ff6eaaf91656e5bULL, 0x3c9e845b11ff6787ULL},
    {0x3ff6f6abbea1c4e1ULL, 0xbc9be8bc3622ed2aULL}, {0x3ff702a3c1c28250ULL, 0x3c7239b3f74b9eefULL},
    {0x3ff70e979fd3d1fcULL, 0x3c7d1c2ca317e24dULL}, {0x3ff71a875dd76b67ULL, 0x3c99eeeea70e2a59ULL},
    {0x3ff7267300c4b0d5ULL, 0xbc92c4620cb11dafULL}, {0x3ff7325a8d88cd63ULL, 0x3c5ffd57c18dc60dULL},
    {0x3ff73e3e0906d2b9ULL, 0xbc947b51676a9319ULL}, {0x3ff74a1d7817d63fULL, 0x3c826f286587d83cULL},
    {0x3ff755f8df8b0df2ULL, 0xbc820858d6fd8d46ULL}, {0x3ff761d04425ecc2ULL, 0xbc8e84f796bf0c11ULL},
    {0x3ff76da3aaa43e90ULL, 0xbc9cbcc7da72a269ULL}, {0x3ff7797317b843bfULL, 0xbc9e540ea05238fbULL},
    {0x3ff7853e900acc62ULL, 0xbc86f2789788e14aULL}, {0x3ff79106183b5306ULL, 0xbc85fe2f28068ee7ULL},
    {0x3ff79cc9b4e01718ULL, 0xbc9bba947eca99cfULL}, {0x3ff7a8896a8636ecULL, 0xbc932965a0169dc6ULL},
    {0x3ff7b4453db1c967ULL, 0xbc7a6db1557bc6edULL}, {0x3ff7bffd32ddf749ULL, 0x3c84dac88bdc1d54ULL},
    {0x3ff7cbb14e7d141eULL, 0xbc8c6cbf19d66a8dULL}, {0x3ff7d76194f8b6d1ULL, 0x3c992c037a2a4c93ULL},
    {0x3ff7e30e0ab1d1f0ULL, 0xbc82ea08f95547b3ULL}, {0x3ff7eeb6b400cb8bULL, 0x3c8ecf9554078da7ULL},
    {0x3ff7fa5b953594ceULL, 0xbc96104277ec4c94ULL}, {0x3ff805fcb297c137ULL, 0x3c821120e149d724ULL},
    {0x3ff8119a10669d89ULL, 0x3c8cf24f7c3fca39ULL}, {0x3ff81d33b2d94661ULL, 0x3c9c8aefb984164dULL},
    {0x3ff828c99e1ebe84ULL, 0x3c8d6c85882fccf6ULL}, {0x3ff8345bd65e04d9ULL, 0x3c9f2ccfcc7a5eedULL},
    {0x3ff83fea5fb62a1cULL, 0x3c8abfc222fe8593ULL}, {0x3ff84b753e3e663eULL, 0x3c97f54f3391e7b4ULL},
    {0x3ff856fc76062d82ULL, 0x3c9afc9c01d8c341ULL}, {0x3ff862800b15454cULL, 0xbc9e621d5e4469fdULL},
    {0x3ff86e00016bd8a6ULL, 0xbc7c48fc96fe5dd8ULL}, {0x3ff8797c5d028c88ULL, 0x3c900bda73fa537aULL},
    {0x3ff884f521ca93d0ULL, 0xbc8f963ef632cb91ULL}, {0x3ff8906a53adc2f7ULL, 0x3c95fce19a27d717ULL},
    {0x3ff89bdbf68ea38cULL, 0xbc890a45cea5d1c1ULL}, {0x3ff8a74a0e48875eULL, 0xbc9e35126f1e0e21ULL},
    {0x3ff8b2b49eaf9b71ULL, 0x3c7bc29967dae981ULL}, {0x3ff8be1bab90fab0ULL, 0xbc886175635e0700ULL},
    {0x3ff8c97f38b2c059ULL, 0xbc6af8bf15d4bf92ULL}, {0x3ff8d4df49d41a35ULL, 0x3c8a21b9cb695e1aULL},
    {0x3ff8e03be2ad5a8dULL, 0xbc80418ec7cdbb6aULL}, {0x3ff8eb9506f009e2ULL, 0x3c479dab034eea27ULL},
    {0x3ff8f6eaba46f86fULL, 0x3c9ddf7a8b158e39ULL}, {0x3ff9023d00564f6eULL, 0xbc925e29f07113faULL},
    {0x3ff90d8bdcbba21eULL, 0x3c9b652ce9140ef6ULL}, {0x3ff918d7530dfea0ULL, 0xbc9238937a707380ULL},
    {0x3ff9241f66ddfe88ULL, 0xbc81a1fcd4fae64aULL}, {0x3ff92f641bb5d74bULL, 0xbc9f65468fbefb0dULL},
    {0x3ff93aa575196a68ULL, 0x3c7668434d7dcc5cULL}, {0x3ff945e376865568ULL, 0x3c974d5206d4471fULL},
    {0x3ff9511e237401a1ULL, 0xbc72c9ba45d8da0fULL}, {0x3ff95c557f53b3c8ULL, 0x3c9a62b7b209c78eULL},
    {0x3ff967898d909b57ULL, 0x3c91f93a2f15d0eeULL}, {0x3ff972ba518fe1b7ULL, 0xbc7698ed9dd472f2ULL},
    {0x3ff97de7ceb0b940ULL, 0xbc8a8a6cf49a7c0bULL}, {0x3ff98912084c6c08ULL, 0xbc9ca16bc00d6b72ULL},
    {0x3ff9943901b66a80ULL, 0xbc9af011ed0b701eULL}, {0x3ff99f5cbe3c59e5ULL, 0xbc6c6345337f3055ULL},
    {0x3ff9aa7d41262282ULL, 0x3c96cd9bd3971973ULL}, {0x3ff9b59a8db5fdc5ULL, 0xbc85f262c73257beULL},
    {0x3ff9c0b4a7288424ULL, 0xbc8e1f3d8b3ff4c5ULL}, {0x3ff9cbcb90b4baddULL, 0x3c7fe5e11860a77eULL},
    {0x3ff9d6df4d8c2186ULL, 0x3c95c4bd58d804b5ULL}, {0x3ff9e1efe0dabf73ULL, 0xbc97b5dfc2dca7f2ULL},
    {0x3ff9ecfd4dc730efULL, 0x3c967328598f1a39ULL}, {0x3ff9f8079772b457ULL, 0x3c5664b38e5db0d1ULL},
    {0x3ffa030ec0f936fcULL, 0xbc9800613c85b73aULL}, {0x3ffa0e12cd7161e9ULL, 0xbc897a52b1c167e3ULL},
    {0x3ffa1913bfeca67fULL, 0xbc9e1c496aaaa4a4ULL}, {0x3ffa24119b774ae5ULL, 0xbc7ea45bf5aa3cacULL},
    {0x3ffa2f0c63187659ULL, 0x3c9a356713d2bd07ULL}, {0x3ffa3a0419d23d57ULL, 0xbc8dcf83d2769cf1ULL},
    {0x3ffa44f8c2a1ad97ULL, 0x3c71c5b5c6d432f1ULL}, {0x3ffa4fea607ed9f2ULL, 0xbc9ab73de2f387bfULL},
    {0x3ffa5ad8f65ce614ULL, 0x3c9028e7a5e64b06ULL}, {0x3ffa65c4872a121aULL, 0xbc990eafe623bb05ULL},
    {0x3ffa70ad15cfc5fcULL, 0xbc9c52fdcc1096c2ULL}, {0x3ffa7b92a5329ce4ULL, 0xbc9b0341b8c3c5baULL},
    {0x3ffa867538327059ULL, 0xbc87d7a4871eddb0ULL}, {0x3ffa9154d1aa634dULL, 0xbc9c421a09d15ebcULL},
    {0x3ffa9c317470ed06ULL, 0xbc98af220be60970ULL}, {0x3ffaa70b2357e3ebULL, 0xbbf2069d196abce0ULL},
    {0x3ffab1e1e12c882eULL, 0x3c9e449e3463f2a4ULL}, {0x3ffabcb5b0b78e57ULL, 0x3c95217d314473a5ULL},
    {0x3ffac78694bd29aeULL, 0xbc71fbc492e434e8ULL}, {0x3ffad2548ffd1688ULL, 0x3c98b0a487893326ULL},
    {0x3ffadd1fa532a479ULL, 0xbc80f7b41e39378dULL}, {0x3ffae7e7d714c05eULL, 0xbc712de63ea0e1e5ULL},
    {0x3ffaf2ad2855fe55ULL, 0x3c9471f093f2a674ULL}, {0x3ffafd6f9ba4a392ULL, 0xbc994bd1256a6febULL},
    {0x3ffb082f33aab013ULL, 0x3c82c633eaeeae3aULL}, {0x3ffb12ebf30de845ULL, 0xbc92fdc122d67fdbULL},
    {0x3ffb1da5dc6fde7cULL, 0x3c803ceaa05e9ea3ULL}, {0x3ffb285cf26dfc60ULL, 0xbc9eae49b8cbf07fULL},
    {0x3ffb331137a18c2fULL, 0x3c8e923c52c62bffULL}, {0x3ffb3dc2ae9fc1f5ULL, 0x3c7b4a73ccaa2324ULL},
    {0x3ffb487159f9c499ULL, 0x3c8d26b86ff734b9ULL}, {0x3ffb531d3c3cb6ddULL, 0xbc905ab2abe27385ULL},
    {0x3ffb5dc657f1c03bULL, 0xbc7819a4448de400ULL}, {0x3ffb686caf9e15b1ULL, 0xbc8a02a4027034bdULL},
    {0x3ffb731045c3026cULL, 0x3c72af07f9007177ULL}, {0x3ffb7db11cddf061ULL, 0x3c65bde237b84088ULL},
    {0x3ffb884f376870c8ULL, 0x3c9b685e3a2bc5c3ULL}, {0x3ffb92ea97d84485ULL, 0x3c821bff89ed2011ULL},
    {0x3ffb9d83409f6472ULL, 0x3c98ea06fec5ba56ULL}, {0x3ffba819342c099aULL, 0x3c9be96154e24fd7ULL},
    {0x3ffbb2ac74e8b556ULL, 0x3c954906657fc106ULL}, {0x3ffbbd3d053c3957ULL, 0xbc745cb00199a181ULL},
    {0x3ffbc7cae789bf97ULL, 0x3c9ac0d98c8b6c0fULL}, {0x3ffbd2561e30d23aULL, 0xbc7d86620347b6d1ULL},
    {0x3ffbdcdeab8d634eULL, 0xbc81fe350848cce6ULL}, {0x3ffbe76491f7d481ULL, 0x3c9da2882c8e5b5dULL},
    {0x3ffbf1e7d3c4febdULL, 0x3c8fdced616e640fULL}, {0x3ffbfc68734639abULL, 0x3c75730045b98ad6ULL},
    {0x3ffc06e672c96328ULL, 0x3c9564a402e963deULL}, {0x3ffc1161d498e6a4ULL, 0xbc9790df6839df05ULL},
    {0x3ffc1bda9afbc466ULL, 0x3c9eee699e582104ULL}, {0x3ffc2650c83598cbULL, 0xbc40a40e08b94203ULL},
    {0x3ffc30c45e86a35eULL, 0xbc6b65d98c863277ULL}, {0x3ffc3b35602bcdeeULL, 0xbc9da3b5e137e494ULL},
    {0x3ffc45a3cf5eb385ULL, 0xbc6c277b2b6c7590ULL}, {0x3ffc500fae55a755ULL, 0x3c6f374edefe9835ULL},
    {0x3ffc5a78ff43bb8bULL, 0xbc9baf972d1f2f42ULL}, {0x3ffc64dfc458c812ULL, 0xbc978147126aa7cfULL},
    {0x3ffc6f43ffc17147ULL, 0x3c9cc82843414faeULL}, {0x3ffc79a5b3a72e9aULL, 0xbc82e05251abacaaULL},
    {0x3ffc8404e2305115ULL, 0x3c8ef116b7249d4cULL}, {0x3ffc8e618d8009e1ULL, 0x3c661dff1a55461eULL},
    {0x3ffc98bbb7b670abULL, 0xbc738fda01d7f17fULL}, {0x3ffca31362f08a01ULL, 0xbc52cf827ce09823ULL},
    {0x3ffcad6891484d9bULL, 0x3c80ca10e3c7b927ULL}, {0x3ffcb7bb44d4ac94ULL, 0xbc7c8221054f9300ULL},
    {0x3ffcc20b7fa99791ULL, 0xbc8cd9d8e3d834beULL}, {0x3ffccc5943d804dbULL, 0xbc9db86da2fa0850ULL},
    {0x3ffcd6a4936df665ULL, 0x3c98f414e3d8aaa1ULL}, {0x3ffce0ed70767fc9ULL, 0x3c9fce36a8e23362ULL},
    {0x3ffceb33dcf9cc2cULL, 0xbc835e29fea3ac10ULL}, {0x3ffcf577dafd2418ULL, 0xbc8ca6fceaab765cULL},
    {0x3ffcffb96c82f349ULL, 0x3c90e22bc1be3857ULL}, {0x3ffd09f8938ace68ULL, 0x3c909f289a6970f7ULL},
    {0x3ffd1435521178b5ULL, 0x3c857c9ee14b4fa0ULL}, {0x3ffd1e6faa10e9a7ULL, 0xbc92d5f32658cbcbULL},
    {0x3ffd28a79d805279ULL, 0x3c93acfe809a7bb6ULL}, {0x3ffd32dd2e5423b0ULL, 0x3c901433566602c9ULL},
    {0x3ffd3d105e7e1289ULL, 0xbc94245893c8324cULL}, {0x3ffd47412fed1e5fULL, 0xbc918c24bc098a49ULL},
    {0x3ffd516fa48d9605ULL, 0xbc89f33c7ec62bbeULL}, {0x3ffd5b9bbe491d0dULL, 0x3c9876eac5f85f36ULL},
    {0x3ffd65c57f06b107ULL, 0x3c9636a7b0812225ULL}, {0x3ffd6fece8aaaeadULL, 0x3c3639b698bf6ab2ULL},
    {0x3ffd7a11fd16d706ULL, 0x3c74c5a4cc6a6203ULL}, {0x3ffd8434be2a547dULL, 0xbc9160c29aabf03bULL},
    {0x3ffd8e552dc1bfe6ULL, 0xbc8dfc57d492c610ULL}, {0x3ffd98734db7257cULL, 0x3c91b1857021cd3fULL},
    {0x3ffda28f1fe209d1ULL, 0xbc914f216d4fe830ULL}, {0x3ffdaca8a6176eacULL, 0xbc8dae7add572ea1ULL},
    {0x3ffdb6bfe229d7e5ULL, 0xbc87c29807ca499eULL}, {0x3ffdc0d4d5e9502dULL, 0xbc974d89ba2086e1ULL},
    {0x3ffdcae783236dccULL, 0x3c50e9f7128abbdbULL}, {0x3ffdd4f7eba35757ULL, 0xbc94e9589d8da660ULL},
    {0x3ffddf061131c853ULL, 0xbc9c437f71c897e5ULL}, {0x3ffde911f59515d4ULL, 0xbc9438351961dab9ULL},
    {0x3ffdf31b9a91330dULL, 0xbc9946c488a9c150ULL}, {0x3ffdfd2301e7b5d4ULL, 0xbc93aa216692e79aULL},
    {0x3ffe07282d57db1dULL, 0x3c954765b4c8a79aULL}, {0x3ffe112b1e9e8b6bULL, 0x3c8641739c52dc78ULL},
    {0x3ffe1b2bd7765f31ULL, 0xbc9c0770a046a393ULL}, {0x3ffe252a5997a32cULL, 0x3c91aeb3f3d068e1ULL},
    {0x3ffe2f26a6b85cb8ULL, 0xbc932bbf82287b91ULL}, {0x3ffe3920c08c4e0cULL, 0xbc9ced3da87eaa7aULL},
    {0x3ffe4318a8c4fa7aULL, 0x3c90d2c5ff729fe6ULL}, {0x3ffe4d0e6111aaa0ULL, 0x3c8b8df05684ffa5ULL},
    {0x3ffe5701eb1f708aULL, 0xbc88336d253ae92eULL}, {0x3ffe60f348992bd0ULL, 0xbc97badb61b8013fULL},
    {0x3ffe6ae27b278da9ULL, 0xbc92dc2988803b86ULL}, {0x3ffe74cf84711cf3ULL, 0x3c71baede5ee7a6bULL},
    {0x3ffe7eba661a3a33ULL, 0xbc962c5992271076ULL}, {0x3ffe88a321c52387ULL, 0xbc9488cc32ecfda9ULL},
    {0x3ffe9289b911f896ULL, 0xbc97c39cc949512cULL}, {0x3ffe9c6e2d9ebe70ULL, 0xbc761ca6e7e9fed9ULL},
    {0x3ffea65081076369ULL, 0x3c95d879a32050ddULL}, {0x3ffeb030b4e5c2e9ULL, 0x3c9f1c209393d8d1ULL},
    {0x3ffeba0ecad1a933ULL, 0x3c711eeb58f8108bULL}, {0x3ffec3eac460d722ULL, 0x3c9bbe46a8049d43ULL},
    {0x3ffecdc4a32705e3ULL, 0x3c90b373d2e53e9aULL}, {0x3ffed79c68b5ea9eULL, 0xbc9cbae8ee648fe3ULL},
    {0x3ffee172169d3a1aULL, 0x3c63c86aca80a11bULL}, {0x3ffeeb45ae6aac5eULL, 0x3c791c0d07c60f04ULL},
    {0x3ffef51731aa003fULL, 0x3c8f8178abb3ab14ULL}, {0x3ffefee6a1e4feeeULL, 0x3c9556ef1a72f42fULL},
    {0x3fff08b400a37f7bULL, 0xbc9edb6c4320f653ULL}, {0x3fff127f4f6b6a4cULL, 0x3c7c5a6c563dfd25ULL},
    {0x3fff1c488fc0bc97ULL, 0x3c98b268d13709ddULL}, {0x3fff260fc3258bc7ULL, 0x3c9c2a1ca861e212ULL},
    {0x3fff2fd4eb1a08e1ULL, 0x3c88b564b700c17dULL}, {0x3fff3998091c83dfULL, 0xbc98c2baa001a27dULL},
    {0x3fff43591ea96f02ULL, 0x3c9042528b097babULL}, {0x3fff4d182d3b6223ULL, 0x3c87f74ca9ed9e03ULL},
    {0x3fff56d5364b1df1ULL, 0x3c9a67c057d8dd1aULL}, {0x3fff60903b4f8f33ULL, 0xbc85c05984967b1cULL},
    {0x3fff6a493dbdd1f9ULL, 0xbc82cfab74eb5edeULL}, {0x3fff74003f0934cfULL, 0xbc906e5e49a6030cULL},
    {0x3fff7db540a33be1ULL, 0xbc9035fb19b67775ULL}, {0x3fff876843fba41cULL, 0x3c7ba22744be05baULL},
    {0x3fff91194a806648ULL, 0x3c649a340d04373eULL}, {0x3fff9ac8559dba18ULL, 0xbc9175a14441e373ULL},
    {0x3fffa47566be1935ULL, 0x3c9b95c760352b24ULL}, {0x3fffae207f4a4247ULL, 0xbc8bfa504881794aULL},
    {0x3fffb7c9a0a93beaULL, 0x3c945f77ac9e36ccULL}, {0x3fffc170cc4057aeULL, 0x3c97118599389d1eULL},
    {0x3fffcb1603733501ULL, 0x3c915a1eab2b569eULL}, {0x3fffd4b947a3c41bULL, 0x3c888b56dea92407ULL},
    {0x3fffde5a9a3248e1ULL, 0x3c93fb11708d5d18ULL}, {0x3fffe7f9fc7d5dc3ULL, 0xbc9031eb88aa637cULL},
    {0x3ffff1976fe1f68fULL, 0x3c75ab57a130051bULL}, {0x3ffffb32f5bb6347ULL, 0xbc949d883a3b4843ULL},
  },
  {
    {0x3ff847a5ccd213ecULL, 0x3c7608f84ce668fdULL}, {0x3ff8562d059dffdcULL, 0xbc26830998f88876ULL},
    {0x3ff864ae7888ecdbULL, 0x3c823e584fc1388bULL}, {0x3ff8732a2d924d24ULL, 0x3c80a97b29d7bf4dULL},
    {0x3ff881a02ca6a70dULL, 0xbc9dcd2961bf42efULL}, {0x3ff890107d9fd431ULL, 0x3c9746804831c026ULL},
    {0x3ff89e7b28453f94ULL, 0xbc98865151d52cefULL}, {0x3ff8ace0344c22abULL, 0xbc9f11c350129185ULL},
    {0x3ff8bb3fa957c171ULL, 0xbc81a07bdfd9728fULL}, {0x3ff8c9998ef9a573ULL, 0xbc81529c3ddc623dULL},
    {0x3ff8d7edecb1d7e2ULL, 0xbc9a7d201f415805ULL}, {0x3ff8e63cc9ef1ab1ULL, 0x3c8033063c04cf51ULL},
    {0x3ff8f4862e0f20c6ULL, 0x3c9d7136d4a6ac33ULL}, {0x3ff902ca205ec53aULL, 0xbc8de8d7e76d93e0ULL},
    {0x3ff91108a81a41b2ULL, 0xbc5d9eccb4a22174ULL}, {0x3ff91f41cc6d63deULL, 0x3c79253f4a3f2d21ULL},
    {0x3ff92d759473c211ULL, 0xbc71cc33f6bd9d4fULL}, {0x3ff93ba40738ef03ULL, 0x3c9785ebd5cecee6ULL},
    {0x3ff949cd2bb8acc2ULL, 0xbc8d7a88f8d4d88bULL}, {0x3ff957f108df1ec8ULL, 0x3c9e550927f3f3b4ULL},
    {0x3ff9660fa588fb54ULL, 0xbc9b50f3f01a9f03ULL}, {0x3ff974290883bbe6ULL, 0xbc679589b4d80d48ULL},
    {0x3ff9823d388dcd0bULL, 0x3c9fc08ead58c421ULL}, {0x3ff9904c3c56bd5aULL, 0x3c8fdd991df3f966ULL},
    {0x3ff99e561a7f6bb6ULL, 0x3c93cccfb37c803cULL}, {0x3ff9ac5ad99a34dcULL, 0x3c6709d3d9c1fa77ULL},
    {0x3ff9ba5a802b2034ULL, 0x3c8c2d80f687accbULL}, {0x3ff9c85514a80bf6ULL, 0xbc9fc50603c7eff1ULL},
    {0x3ff9d64a9d78d897ULL, 0xbc8efca81d51a53eULL}, {0x3ff9e43b20f79395ULL, 0x3c9bc0216c9f2462ULL},
    {0x3ff9f226a570a193ULL, 0x3c945068d124d5edULL}, {0x3ffa000d3122e7cfULL, 0xbc88300f751bc985ULL},
    {0x3ffa0deeca3ff4f9ULL, 0xbc83b10253389089ULL}, {0x3ffa1bcb76ec296bULL, 0x3c9e4196acaa5913ULL},
    {0x3ffa29a33d3edec4ULL, 0x3c772b318d1042c0ULL}, {0x3ffa377623428ee4ULL, 0x3c8d2c5596600ce2ULL},
    {0x3ffa45442ef4fa5cULL, 0xbc92929d120caba3ULL}, {0x3ffa530d66474e3fULL, 0xbc40c137a0ffbfb4ULL},
    {0x3ffa60d1cf1e496cULL, 0x3c9854bb85086242ULL}, {0x3ffa6e916f526143ULL, 0xbc8a2c1b6de2ebd9ULL},
    {0x3ffa7c4c4cafe5cdULL, 0xbc944ed6c391a545ULL}, {0x3ffa8a026cf72562ULL, 0xbc98df30a4420ed9ULL},
    {0x3ffa97b3d5dc8fc1ULL, 0x3c6e25bd0225446eULL}, {0x3ffaa5608d08d8a9ULL, 0xbc881707ebbefb50ULL},
    {0x3ffab308981919e9ULL, 0x3c97d1e92dfe2aa0ULL}, {0x3ffac0abfc9ef4fbULL, 0xbc93082bdcd9f7ecULL},
    {0x3fface4ac020b414ULL, 0xbc99e9a3bc0e26f1ULL}, {0x3ffadbe4e8196ac6ULL, 0xbc7977c122619800ULL},
    {0x3ffae97a79f91622ULL, 0xbc8891ae89ef77c8ULL}, {0x3ffaf70b7b24bc62ULL, 0x3c94609a016be4e3ULL},
    {0x3ffb0497f0f68c25ULL, 0x3c426bc8c38cbcd2ULL}, {0x3ffb121fe0bdfb2fULL, 0x3c82c1f51b0cc38bULL},
    {0x3ffb1fa34fbfe4c2ULL, 0x3c844fbeda7a9234ULL}, {0x3ffb2d224336a781ULL, 0x3c9bdcdbf825a5d4ULL},
    {0x3ffb3a9cc05242ebULL, 0x3c98edaff4568deaULL}, {0x3ffb4812cc387468ULL, 0xbc954e7632974021ULL},
    {0x3ffb55846c04d3ecULL, 0x3c96e071a5db1538ULL}, {0x3ffb62f1a4c8f03cULL, 0x3c51de3a935b459aULL},
    {0x3ffb705a7b8c6abeULL, 0x3c9244c12a549132ULL}, {0x3ffb7dbef54d12f5ULL, 0xbc865a33c3c2b187ULL},
    {0x3ffb8b1f16ff018eULL, 0x3c9390b60e022b45ULL}, {0x3ffb987ae58cb319ULL, 0x3c7571e9ee6bbd2eULL},
    {0x3ffba5d265d72257ULL, 0x3c8db432ec72feebULL}, {0x3ffbb3259cb5e236ULL, 0xbc9f52dae3e196aeULL},
    {0x3ffbc0748ef73767ULL, 0xbc8255945f144fa9ULL}, {0x3ffbcdbf416031a6ULL, 0xbc70f5aa046a80d0ULL},
    {0x3ffbdb05b8acc49eULL, 0x3c8f865262fe3306ULL}, {0x3ffbe847f98fe07eULL, 0x3c937cf0beefb552ULL},
    {0x3ffbf58608b38a34ULL, 0x3c924c15ef2c7e72ULL}, {0x3ffc02bfeab8f357ULL, 0xbc9879ed21edd738ULL},
    {0x3ffc0ff5a43891baULL, 0xbc804cab0931eeb4ULL}, {0x3ffc1d2739c236b5ULL, 0x3c9643ffbff61c88ULL},
    {0x3ffc2a54afdd2618ULL, 0xbc95a23b84242397ULL}, {0x3ffc377e0b082ccdULL, 0xbc93e802975066c5ULL},
    {0x3ffc44a34fb9b736ULL, 0x3c7d77d8cde2906fULL}, {0x3ffc51c4825fe738ULL, 0xbc7e1a23976efea8ULL},
    {0x3ffc5ee1a760a9faULL, 0xbc8ef23c4229e45fULL}, {0x3ffc6bfac319cd5fULL, 0x3c8f80a4a164315fULL},
    {0x3ffc790fd9e11537ULL, 0x3c5e8fe39b7f8c74ULL}, {0x3ffc8620f0045023ULL, 0x3c7eb28624afb2dbULL},
    {0x3ffc932e09c96c3bULL, 0xbc834ce02a35a889ULL}, {0x3ffca0372b6e8b68ULL, 0xbc84124fb1bb6e52ULL},
    {0x3ffcad3c592a177fULL, 0x3c716a31d9dd64afULL}, {0x3ffcba3d972ad617ULL, 0x3c64745e13af56e6ULL},
    {0x3ffcc73ae997fc1cULL, 0x3c9083e240c24018ULL}, {0x3ffcd43454914125ULL, 0xbc78c8ac1f91e630ULL},
    {0x3ffce129dc2ef285ULL, 0xbc86448447ba4387ULL}, {0x3ffcee1b84820623ULL, 0xbc86004e55eb361bULL},
    {0x3ffcfb0951942d10ULL, 0x3c8c4db405231cdfULL}, {0x3ffd07f34767e5e4ULL, 0xbc97978f35a8d454ULL},
    {0x3ffd14d969f88ed8ULL, 0xbc186f1e375cdd1eULL}, {0x3ffd21bbbd3a77b1ULL, 0xbc9335ad47148e1fULL},
    {0x3ffd2e9a451af364ULL, 0xbc923faf42942efeULL}, {0x3ffd3b750580698bULL, 0xbc91748ecf8c4dcdULL},
    {0x3ffd484c024a679cULL, 0x3c677f40a6076158ULL}, {0x3ffd551f3f51b1ecULL, 0x3c8ad18cbf7ec694ULL},
    {0x3ffd61eec0685479ULL, 0x3c7ff2017ac4938dULL}, {0x3ffd6eba8959b380ULL, 0xbc9b6faca44d210dULL},
    {0x3ffd7b829dea9bdcULL, 0xbc7b771ba3552e6bULL}, {0x3ffd884701d95337ULL, 0xbc94a0f96664456aULL},
    {0x3ffd9507b8dda7feULL, 0x3c8c3a9812a3fe8dULL}, {0x3ffda1c4c6a9012eULL, 0xbc9da291cd5ffbecULL},
    {0x3ffdae7e2ee66de2ULL, 0xbc9373dd3f8acaf4ULL}, {0x3ffdbb33f53ab4beULL, 0x3c8bcbb1e87dc9a3ULL},
    {0x3ffdc7e61d446321ULL, 0x3c90ff8df6348270ULL}, {0x3ffdd494aa9bdc28ULL, 0x3c97a3fa4c5804d5ULL},
    {0x3ffde13fa0d36786ULL, 0x3c9762d30e326023ULL}, {0x3ffdede70377402bULL, 0x3c9162eb1dbaac37ULL},
    {0x3ffdfa8ad60da2bfULL, 0xbc8d81846341c3e5ULL}, {0x3ffe072b1c16dbeeULL, 0xbc606e1d21826cbcULL},
    {0x3ffe13c7d90d568dULL, 0x3c7c4809baea76cdULL}, {0x3ffe20611065a98eULL, 0xbc80397751c91771ULL},
    {0x3ffe2cf6c58ea5cbULL, 0xbc7bc0ec90de14beULL}, {0x3ffe3988fbf163a9ULL, 0x3c822fa4b76eb44eULL},
    {0x3ffe4617b6f15090ULL, 0xbc8a36c4351e0bb5ULL}, {0x3ffe52a2f9ec3c37ULL, 0x3c82663b9e012627ULL},
    {0x3ffe5f2ac83a65cfULL, 0x3c89c9076e88b842ULL}, {0x3ffe6baf252e88ffULL, 0xbc9c65f84fab7d4bULL},
    {0x3ffe78301415eabaULL, 0x3c6aeea10f96ea15ULL}, {0x3ffe84ad983865f6ULL, 0xbc810bb68fcdc09cULL},
    {0x3ffe9127b4d87831ULL, 0xbc9dfde41c02b584ULL}, {0x3ffe9d9e6d334dd8ULL, 0x3c9cf55c02e4248aULL},
    {0x3ffeaa11c480ce8cULL, 0x3c9d5001869b2586ULL}, {0x3ffeb681bdf3a938ULL, 0xbc78ef7abf300746ULL},
    {0x3ffec2ee5cb9600bULL, 0xbc836f4de77a7385ULL}, {0x3ffecf57a3fa544fULL, 0xbc85cf831ff9bb6dULL},
    {0x3ffedbbd96d9d219ULL, 0xbc92c88238f49b92ULL}, {0x3ffee82038761bd8ULL, 0x3c77fcc311e57f42ULL},
    {0x3ffef47f8be875c5ULL, 0xbc8293565593dc11ULL}, {0x3fff00db9445312bULL, 0x3c81647aecb64d1aULL},
    {0x3fff0d34549bb796ULL, 0x3c99fa5ce2957ae5ULL}, {0x3fff1989cff695dcULL, 0xbc60a252976e3ce1ULL},
    {0x3fff25dc095b8705ULL, 0x3c98dbacd90a32c2ULL}, {0x3fff322b03cb7f1bULL, 0x3c933fb8406492c0ULL},
    {0x3fff3e76c242b5d1ULL, 0x3c39dee4c3bf09f1ULL}, {0x3fff4abf47b8b111ULL, 0x3c9461421d0f4277ULL},
    {0x3fff570497204f6dULL, 0x3c70b5616bdaf25fULL}, {0x3fff6346b367d26cULL, 0xbc950c75f858fee5ULL},
    {0x3fff6f859f78e8beULL, 0x3c8cfdd7b418fedbULL}, {0x3fff7bc15e38b855ULL, 0x3c9cd71004cc0730ULL},
    {0x3fff87f9f287e85bULL, 0xbc6ce9cceb2d72a0ULL}, {0x3fff942f5f42ab0eULL, 0x3c7e5e2809ea8325ULL},
    {0x3fffa061a740c785ULL, 0x3c89a365697ef156ULL}, {0x3fffac90cd55a353ULL, 0xbc9573a03d32e91aULL},
    {0x3fffb8bcd4504c0fULL, 0x3c9fccced62830a1ULL}, {0x3fffc4e5befb80cbULL, 0xbc97cc9acd0856d6ULL},
    {0x3fffd10b901dbb5eULL, 0xbc74ebc005577e09ULL}, {0x3fffdd2e4a7939a9ULL, 0x3c610e05fb481a80ULL},
    {0x3fffe94df0cc06b3ULL, 0xbc9b7f5bc7f4276eULL}, {0x3ffff56a85d003b0ULL, 0xbc8d1f8bccba60ffULL},
    {0x400000c2061d787aULL, 0xbcaa802e9b8507b1ULL}, {0x400006cd435f3b61ULL, 0x3c9f9f44f1de9d6cULL},
    {0x40000cd6fc04170aULL, 0x3c83629c9c15c2bcULL}, {0x400012df3160d49aULL, 0x3ca4b740c64ab92aULL},
    {0x400018e5e4c83e2aULL, 0x3c8ae26d11c88aebULL}, {0x40001eeb178b22feULL, 0x3caef3b1030cc5c3ULL},
    {0x400024eecaf85bb9ULL, 0xbc5e320d3d043f8cULL}, {0x40002af1005cce7cULL, 0xbca41f7c457cfb12ULL},
    {0x400030f1b9037302ULL, 0x3c67eef1362c9450ULL}, {0x400036f0f63556aeULL, 0x3caf15d5d2e28fe5ULL},
    {0x40003ceeb939a08dULL, 0x3ca3d0e9de03eef8ULL}, {0x400042eb0355954cULL, 0x3ca5ee78c117b017ULL},
    {0x400048e5d5cc9b28ULL, 0x3c99eacd17b0260cULL}, {0x40004edf31e03dcfULL, 0xbc903973d055abefULL},
    {0x400054d718d03238ULL, 0xbc8feaefa768ca85ULL}, {0x40005acd8bda5a72ULL, 0x3c921974c06cb23dULL},
    {0x400060c28c3ac968ULL, 0xbca13106acabe554ULL}, {0x400066b61b2bc698ULL, 0xbcaf00dd8ef18810ULL},
    {0x40006ca839e5d1c5ULL, 0xbc777986ea417edeULL}, {0x40007298e99fa69eULL, 0x3c894ab5bfedd77eULL},
    {0x400078882b8e4058ULL, 0xbc7e7640e2004c14ULL}, {0x40007e7600e4dd41ULL, 0x3c9ce665f6e7572bULL},
    {0x400084626ad5024cULL, 0xbc91b8b2c1ea0430ULL}, {0x40008a4d6a8e7e8dULL, 0x3c6bf9a9e300a767ULL},
    {0x40009037013f6eb4ULL, 0x3c8c83bdcc1cec94ULL}, {0x4000961f30144079ULL, 0xbcaa7cc1f37281b1ULL},
    {0x40009c05f837b5ffULL, 0xbc8071215f7e05d7ULL}, {0x4000a1eb5ad2e935ULL, 0xbca01e78a0d61f22ULL},
    {0x4000a7cf590d4f24ULL, 0x3c84a4de923b86a4ULL}, {0x4000adb1f40cbb3eULL, 0x3c9ab62857dcfe5fULL},
    {0x4000b3932cf5629eULL, 0xbc917b2b539ef2ccULL}, {0x4000b97304e9df41ULL, 0x3c8067942cf7e250ULL},
    {0x4000bf517d0b333bULL, 0xbca67ff54c0e24e9ULL}, {0x4000c52e9678cbdcULL, 0xbca959e54eab01c6ULL},
    {0x4000cb0a525084d4ULL, 0x3ca32b2922957343ULL}, {0x4000d0e4b1aeab4eULL, 0xbca2029dff332cbfULL},
    {0x4000d6bdb5ae00fbULL, 0xbc9af864dee17f9cULL}, {0x4000dc955f67bf22ULL, 0xbc8710e8370cbd72ULL},
    {0x4000e26baff3999fULL, 0xbc9e42f36ae0c86dULL}, {0x4000e840a867c1ddULL, 0xbcaef32a496260aeULL},
    {0x4000ee1449d8e9c8ULL, 0x3caf68c92d513488ULL}, {0x4000f3e6955a46bdULL, 0x3ca9efedc9e0dd25ULL},
    {0x4000f9b78bfd9467ULL, 0x3ca152defe5b8193ULL}, {0x4000ff872ed317a0ULL, 0x3c6f25823a2e2bd3ULL},
    {0x400105557ee9a145ULL, 0x3c70a9a8b85f1f95ULL}, {0x40010b227d4e9105ULL, 0x3caad690702cda48ULL},
    {0x400110ee2b0dd82aULL, 0xbcaec8c2493da91cULL}, {0x400116b88931fc53ULL, 0x3ca4aa414d301ed1ULL},
    {0x40011c8198c41a38ULL, 0x3c90c139e91297c4ULL}, {0x400122495acbe853ULL, 0x3cac85cd5fefde34ULL},
    {0x4001280fd04fb993ULL, 0x3c991753866cd668ULL}, {0x40012dd4fa547ffdULL, 0x3ca791f83081b73cULL},
    {0x40013398d9ddcf4fULL, 0x3c8f8fde196297b7ULL}, {0x4001395b6feddf95ULL, 0x3cae74583eb8a93eULL},
    {0x40013f1cbd858fc0ULL, 0xbca8d160bcb90844ULL}, {0x400144dcc3a4682bULL, 0xbc8471214da74c12ULL},
    {0x40014a9b83489d29ULL, 0xbc98f2ee98a44e83ULL}, {0x40015058fd6f117eULL, 0x3ca75cbad555a0cfULL},
    {0x40015615331358deULL, 0xbc4223c2de3fc8ffULL}, {0x40015bd0252fba5bULL, 0xbc421a438e176049ULL},
    {0x40016189d4bd32d7ULL, 0x3c9f230af6ae0540ULL}, {0x4001674242b3776bULL, 0x3c568333f2145effULL},
    {0x40016cf97008f7c7ULL, 0xbc5b006817e8d48aULL}, {0x400172af5db2e091ULL, 0xbcab934a4189aa6fULL},
    {0x400178640ca51db9ULL, 0xbcaff5ca5d0a660bULL}, {0x40017e177dd25cccULL, 0xbc8804639c9e5f90ULL},
    {0x400183c9b22c0f40ULL, 0xbc99b84ef27716f6ULL}, {0x4001897aaaa26cb7ULL, 0x3c8e49899dae55f5ULL},
    {0x40018f2a68247543ULL, 0x3ca708ae7f281cc3ULL}, {0x400194d8eb9ff3a0ULL, 0xbc9186818dff3ef7ULL},
    {0x40019a8636017f68ULL, 0xbc97ffeffc543e88ULL}, {0x4001a03248347f47ULL, 0x3c6084ee39b39f5dULL},
    {0x4001a5dd23232b26ULL, 0xbcaeda940563ed7bULL}, {0x4001ab86c7b68e4eULL, 0x3c8a7a2ed9a8fd1aULL},
    {0x4001b12f36d68990ULL, 0xbc9f36477469e0ccULL}, {0x4001b6d67169d55aULL, 0x3c8ef410b1f5ddcbULL},
    {0x4001bc7c785603d5ULL, 0x3c6f466f2d1cf0e2ULL}, {0x4001c2214c7f82f3ULL, 0x3c9356288c2eafeaULL},
    {0x4001c7c4eec99e80ULL, 0xbc99a176332e0e3eULL}, {0x4001cd6760168228ULL, 0xbc54902e1c4bed8dULL},
    {0x4001d308a1473b7fULL, 0xbc9f46485837b3c9ULL}, {0x4001d8a8b33bbbfdULL, 0xbc9888f42b9d5b5aULL},
    {0x4001de4796d2dafcULL, 0xbcab0bd442217450ULL}, {0x4001e3e54cea57acULL, 0xbca419d542c4e5e2ULL},
    {0x4001e981d65edb07ULL, 0xbc86c3390d2f395dULL}, {0x4001ef1d340bf9beULL, 0xbca47d9b8f680d49ULL},
    {0x4001f4b766cc3620ULL, 0x3c92fcdb17d8f217ULL}, {0x4001fa506f790203ULL, 0xbc8612087c191276ULL},
    {0x4001ffe84eeac09fULL, 0x3ca9ffef3988ebc8ULL}, {0x4002057f05f8c870ULL, 0x3c50042a7d5e2600ULL},
    {0x40020b1495796508ULL, 0xbc7bde9121a6333bULL}, {0x400210a8fe41d8e7ULL, 0x3c410f2ac86ad38bULL},
    {0x4002163c41265f49ULL, 0x3c8a8a4def746a26ULL}, {0x40021bce5efa2df2ULL, 0xbc9b3e1a565076a4ULL},
    {0x4002215f588f76f4ULL, 0xbca59a9339ee008dULL}, {0x400226ef2eb76a74ULL, 0xbc944cbf4473b190ULL},
    {0x40022c7de2423869ULL, 0x3caae626094e4b35ULL}, {0x4002320b73ff1259ULL, 0x3c7617e5e41f2a31ULL},
    {0x40023797e4bc2d0dULL, 0xbcaa3312d27dd4edULL}, {0x40023d233546c247ULL, 0x3c7238f90c2f1b55ULL},
    {0x400242ad666b1275ULL, 0xbcaf987bdb46fa0aULL}, {0x4002483678f46657ULL, 0xbca9bbbd78a536baULL},
    {0x40024dbe6dad10adULL, 0xbc6d00d693a72d2bULL}, {0x40025345455e6fdaULL, 0x3ca20a463ab6a1dcULL},
    {0x400258cb00d0ef85ULL, 0x3cae0297e3ca7483ULL}, {0x40025e4fa0cc0a37ULL, 0x3cad41e08e9e4cceULL},
  },
  {
    {0x3ffbe3e77c29e4d3ULL, 0x3c8e8c13b7e84acbULL}, {0x3ffbf497bfc1a511ULL, 0x3c6ce1566f5caed1ULL},
    {0x3ffc054161b64f9bULL, 0xbc92c940827e0070ULL}, {0x3ffc15e46b37ca59ULL, 0x3c993f5cca2aa457ULL},
    {0x3ffc2680e5603f0aULL, 0xbc866877bb9c1e33ULL}, {0x3ffc3716d93463cdULL, 0x3c9f4cb1a745a2bbULL},
    {0x3ffc47a64fa3c284ULL, 0xbc99274de0cbe9a7ULL}, {0x3ffc582f5188fef0ULL, 0x3c827bebf52a2c0cULL},
    {0x3ffc68b1e7aa1bb7ULL, 0x3c8599f0aefb89a0ULL}, {0x3ffc792e1ab8be33ULL, 0xbc95e3ed14a4c439ULL},
    {0x3ffc89a3f3527129ULL, 0xbc91688782df6bf8ULL}, {0x3ffc9a137a00e668ULL, 0x3c7a1d86f4979fe1ULL},
    {0x3ffcaa7cb73a3751ULL, 0xbc9fb29dee96d1bdULL}, {0x3ffcbadfb361244dULL, 0xbc9e102b95953f2eULL},
    {0x3ffccb3c76c55342ULL, 0x3c999d268c095d97ULL}, {0x3ffcdb9309a38d01ULL, 0xbc7985a03e54d120ULL},
    {0x3ffcebe37425f9aeULL, 0xbc95c70a32f666d4ULL}, {0x3ffcfc2dbe645c3aULL, 0xbc878f95b3f4955cULL},
    {0x3ffd0c71f0644ce2ULL, 0xbc45259d2bd4f454ULL}, {0x3ffd1cb0121972beULL, 0x3c9859f64063a98aULL},
    {0x3ffd2ce82b65bc68ULL, 0xbc946a2b45f00f77ULL}, {0x3ffd3d1a441997b5ULL, 0x3c999957b45d04f6ULL},
    {0x3ffd4d4663f4289aULL, 0x3c73eb79e91efcefULL}, {0x3ffd5d6c92a37f22ULL, 0xbc8cae2148c17a00ULL},
    {0x3ffd6d8cd7c4cc97ULL, 0x3c7edcd295e4b420ULL}, {0x3ffd7da73ae497d3ULL, 0x3c75840068ac6919ULL},
    {0x3ffd8dbbc37ef0bcULL, 0xbc9a1a9229106714ULL}, {0x3ffd9dca78ffa2f5ULL, 0xbc6858fa60df7e75ULL},
    {0x3ffdadd362c267caULL, 0x3c44581eb00adf42ULL}, {0x3ffdbdd68813174fULL, 0xbc83a0104b118be7ULL},
    {0x3ffdcdd3f02dd8c2ULL, 0xbc8eed13800a4a5fULL}, {0x3ffdddcba23f522eULL, 0x3c8402259766bd74ULL},
    {0x3ffdedbda564d755ULL, 0xbc6356cc692b283cULL}, {0x3ffdfdaa00ac97deULL, 0xbc4e9016a93beb5aULL},
    {0x3ffe0d90bb15ccd6ULL, 0xbc93ca73b9b734c3ULL}, {0x3ffe1d71db90e57bULL, 0xbc931aebfb8f94a5ULL},
    {0x3ffe2d4d68ffb35eULL, 0x3c926970219b76e1ULL}, {0x3ffe3d236a3595dbULL, 0x3c66e2022f692d1cULL},
    {0x3ffe4cf3e5f7a4e5ULL, 0xbc7fbc267ea94879ULL}, {0x3ffe5cbee2fcdb35ULL, 0x3c95a3a93a1292b8ULL},
    {0x3ffe6c8467ee3fd7ULL, 0x3c956873b2979da8ULL}, {0x3ffe7c447b670f15ULL, 0x3c7572100103b52fULL},
    {0x3ffe8bff23f4e2cbULL, 0x3c8c683842e934b1ULL}, {0x3ffe9bb46817da24ULL, 0xbc849733897d1934ULL},
    {0x3ffeab644e42c0bcULL, 0x3c8868dbc5c7a2e6ULL}, {0x3ffebb0edcdb3538ULL, 0xbc8e35ce364ddfceULL},
    {0x3ffecab41a39cf43ULL, 0x3c94dbf332d7e698ULL}, {0x3ffeda540caa450bULL, 0xbc9eb09c4355e69dULL},
    {0x3ffee9eeba6b9023ULL, 0xbc9e04363fb9f3deULL}, {0x3ffef98429b011ecULL, 0x3c91477737999aedULL},
    {0x3fff0914609db771ULL, 0xbc9f911a16f76ee3ULL}, {0x3fff189f654e1cb8ULL, 0x3c92ca4e5a98bc0aULL},
    {0x3fff28253dceafa4ULL, 0x3c196413f7021e62ULL}, {0x3fff37a5f020d243ULL, 0x3c8d61be47e8e474ULL},
    {0x3fff47218239fcb0ULL, 0xbc8931bc42755075ULL}, {0x3fff5697fa03de6eULL, 0x3c61898b613b2de9ULL},
    {0x3fff66095d5c7f54ULL, 0x3c9786e213008044ULL}, {0x3fff7575b2165ffcULL, 0x3c9fdc0b17795221ULL},
    {0x3fff84dcfdf899c0ULL, 0xbc2dd280c684b691ULL}, {0x3fff943f46befe42ULL, 0x3c9caf892cdd937eULL},
    {0x3fffa39c921a368bULL, 0x3c6c9dacf3481778ULL}, {0x3fffb2f4e5afe1b0ULL, 0xbc97aca15fd876f5ULL},
    {0x3fffc248471ab313ULL, 0xbc8399f3d0f90e23ULL}, {0x3fffd196bbea9038ULL, 0xbc98b7fa0445aa64ULL},
    {0x3fffe0e049a4ae2bULL, 0x3c966dcb5e5e769aULL}, {0x3ffff024f5c3ae89ULL, 0xbc67fd3aa95b9af3ULL},
    {0x3fffff64c5b7bc16ULL, 0x3c86b45ae077fb70ULL}, {0x4000074fdf73537fULL, 0xbcab8feb34aff02fULL},
    {0x40000eeaf3560052ULL, 0xbc99c0a48d9f20c9ULL}, {0x40001683a12c9b91ULL, 0xbc95997192b0f962ULL},
    {0x40001e19eb9ad82dULL, 0xbc9f486fe7bcc9b6ULL}, {0x400025add53f7259ULL, 0xbc9315d50f6df9d9ULL},
    {0x40002d3f60b43cbaULL, 0xbc98db852fcca31bULL}, {0x400034ce908e2d68ULL, 0xbc9f1ecd1077a534ULL},
    {0x40003c5b675d6ac4ULL, 0xbc8d47325f3f4b06ULL}, {0x400043e5e7ad5822ULL, 0x3ca3350f57fbb210ULL},
    {0x40004b6e1404a249ULL, 0xbc8661a0d443c632ULL}, {0x400052f3eee54bc4ULL, 0x3c574331475399f9ULL},
    {0x40005a777accb911ULL, 0x3c9b13d1914be54bULL}, {0x400061f8ba33bca1ULL, 0x3cad2c4dc2bea5deULL},
    {0x40006977af8ea2b3ULL, 0xbca1a269c43be493ULL}, {0x400070f45d4d3d02ULL, 0x3c89ae1228fd9580ULL},
    {0x4000786ec5daee57ULL, 0xbc96a4a1f05ec04cULL}, {0x40007fe6eb9eb5e7ULL, 0xbc772f071e46720aULL},
    {0x4000875cd0fb3a96ULL, 0x3ca10482039fdc78ULL}, {0x40008ed0784ed610ULL, 0xbc7d2ca104102e2dULL},
    {0x40009641e3f39fbcULL, 0xbca30892a6a3eb1dULL}, {0x40009db1163f778fULL, 0xbc8c203197778303ULL},
    {0x4000a51e118410baULL, 0x3c90840186004197ULL}, {0x4000ac88d80efc34ULL, 0x3c833aa125f7b0efULL},
    {0x4000b3f16c29b322ULL, 0xbc96d271cf813be6ULL}, {0x4000bb57d019a11dULL, 0x3caf60944702ca95ULL},
    {0x4000c2bc06202e5cULL, 0xbcadf5b19e6c6eb6ULL}, {0x4000ca1e107ac9afULL, 0x3ca0505cebac8655ULL},
    {0x4000d17df162f26fULL, 0x3c85caa423128f88ULL}, {0x4000d8dbab0e4239ULL, 0x3c7c2cf36570f90bULL},
    {0x4000e0373fae7698ULL, 0x3c54e46165928b3aULL}, {0x4000e790b1717a8aULL, 0x3c57d99ef553a5d2ULL},
    {0x4000eee802816fe8ULL, 0x3ca9e29fa589fda9ULL}, {0x4000f63d3504b8b2ULL, 0x3c5dd23afd003980ULL},
    {0x4000fd904b1e0038ULL, 0xbc82ac176ed9cf4bULL}, {0x400104e146ec442dULL, 0x3ca2a8af867a6bc1ULL},
    {0x40010c302a8add9bULL, 0xbcaa20e2d5abfa31ULL}, {0x4001137cf81189b5ULL, 0xbc986ea88d59a94cULL},
    {0x40011ac7b1947299ULL, 0xbc88fd63d10d7d0eULL}, {0x40012210592437ecULL, 0x3c61b1d68d12631aULL},
    {0x40012956f0cdf761ULL, 0xbc9541e37e4e7638ULL}, {0x4001309b7a9b5522ULL, 0x3cace58a9d8e5698ULL},
    {0x400137ddf8928425ULL, 0x3c9a0635d62daa5eULL}, {0x40013f1e6cb64e5eULL, 0xbc9b2073d381f1dcULL},
    {0x4001465cd9061cdfULL, 0x3c88cd9e28b0e815ULL}, {0x40014d993f7dffdfULL, 0x3c8bbe3bc1061454ULL},
    {0x400154d3a216b6a3ULL, 0x3c9bebc1515a9293ULL}, {0x40015c0c02c5b754ULL, 0x3ca731cc061ede60ULL},
    {0x40016342637d36bbULL, 0x3ca2866003a2b986ULL}, {0x40016a76c62c2fe5ULL, 0x3ca4dd045934b8edULL},
    {0x400171a92cbe6bb2ULL, 0xbc6402846dad5243ULL}, {0x400178d9991c884aULL, 0xbca2059edf093d7cULL},
    {0x400180080d2c007eULL, 0x3c9eba2ca1bb02eaULL}, {0x400187348acf3315ULL, 0xbcaa9c163d970af9ULL},
    {0x40018e5f13e569f9ULL, 0x3ca8259433fe5bfeULL}, {0x40019587aa4ae160ULL, 0xbcad67694d8e8541ULL},
    {0x40019cae4fd8cecaULL, 0xbc9e38105582c100ULL}, {0x4001a3d3066567ffULL, 0x3c78e3be2f7d37ceULL},
    {0x4001aaf5cfc3e9ebULL, 0xbca884a6f817b911ULL}, {0x4001b216adc49f67ULL, 0x3caec9de67e31fdaULL},
    {0x4001b935a234e7f8ULL, 0xbc749e41327ccd03ULL}, {0x4001c052aedf3e69ULL, 0x3cab27bf68bb8c00ULL},
    {0x4001c76dd58b3f65ULL, 0xbcac8cebfa093b71ULL}, {0x4001ce8717fdafeaULL, 0x3ca7d2c96c01e6d3ULL},
    {0x4001d59e77f883beULL, 0x3ca57b023db6b8aaULL}, {0x4001dcb3f73ae3beULL, 0xbca0daac2baca63bULL},
    {0x4001e3c797813425ULL, 0xbca43d3dfbe6ba43ULL}, {0x4001ead95a851ac1ULL, 0xbc86524d0f96acb8ULL},
    {0x4001f1e941fd8513ULL, 0xbca45755b4a1be39ULL}, {0x4001f8f74f9eae5cULL, 0xbc1a9027bb387d09ULL},
    {0x40020003851a259eULL, 0x3caaf8dfd45e6346ULL}, {0x4002070de41ed388ULL, 0xbca4f6168c7df0d8ULL},
    {0x40020e166e59004dULL, 0x3ca3b2d6e5d217f3ULL}, {0x4002151d25725978ULL, 0xbca594acab3b2d41ULL},
    {0x40021c220b11f79cULL, 0x3ca3e9c278a83bb8ULL}, {0x4002232520dc6408ULL, 0x3ca07c936183ff15ULL},
    {0x40022a2668739e5aULL, 0x3c862d27834ecffaULL}, {0x40023125e377220cULL, 0x3ca2279c560632b5ULL},
    {0x400238239383ebf0ULL, 0xbc7d0ff5620c3590ULL}, {0x40023f1f7a347f98ULL, 0x3c82f44f38d8c8a7ULL},
    {0x400246199920ecb6ULL, 0xbca2abb85efe778fULL}, {0x40024d11f1ded465ULL, 0x3c6347dbaa573e06ULL},
    {0x4002540886016e6cULL, 0xbca6b7e641652764ULL}, {0x40025afd57198e68ULL, 0x3cab244532179fa4ULL},
    {0x400261f066b5a8f5ULL, 0xbca1bdf6d3f09acfULL}, {0x400268e1b661d8b8ULL, 0xbcac242dfd920a82ULL},
    {0x40026fd147a7e36bULL, 0xbca2853c57b6e3f9ULL}, {0x400276bf1c0f3ed2ULL, 0xbc6f10365ccbe17aULL},
    {0x40027dab351d15a5ULL, 0xbc9d8308bad9d7b8ULL}, {0x4002849594544c6aULL, 0x3ca467cddeedfc4fULL},
    {0x40028b7e3b358648ULL, 0x3caca7f1ca1c94e3ULL}, {0x400292652b3f29c5ULL, 0x3ca505f54a1f1b66ULL},
    {0x4002994a65ed657cULL, 0x3c9f75772f9e4c89ULL}, {0x4002a02decba34c6ULL, 0xbcaa9ff7df371160ULL},
    {0x4002a70fc11d6452ULL, 0x3c994ec25d05701dULL}, {0x4002adefe48c96baULL, 0x3ca50f942e0fb107ULL},
    {0x4002b4ce587b4900ULL, 0x3c9dcd340da942b5ULL}, {0x4002bbab1e5ad707ULL, 0xbca542b7c9ce264cULL},
    {0x4002c286379a7ffbULL, 0x3caa4a9fab55abd6ULL}, {0x4002c95fa5a76ab6ULL, 0xbc7b52f8098c3aaaULL},
    {0x4002d03769ecaa0aULL, 0x3caf16530f88bb0fULL}, {0x4002d70d85d34111ULL, 0x3cad5919d163d8c9ULL},
    {0x4002dde1fac22764ULL, 0xbca7756c351de7b0ULL}, {0x4002e4b4ca1e4d4bULL, 0x3c36f906af0b11e2ULL},
    {0x4002eb85f54a9fe9ULL, 0xbcaae3e2e1e5ac49ULL}, {0x4002f2557da80d4fULL, 0x3c9f8dec426eb956ULL},
    {0x4002f92364958894ULL, 0xbc9accc8f26943a0ULL}, {0x4002ffefab700dd2ULL, 0x3ca12cc874143c88ULL},
    {0x400306ba5392a629ULL, 0xbc9635a9a3ae17ecULL}, {0x40030d835e566ba8ULL, 0x3c8dc39801858513ULL},
    {0x4003144acd128d39ULL, 0x3cab79549ed23266ULL}, {0x40031b10a11c527bULL, 0xbca4415ceb8b595eULL},
    {0x400321d4dbc71f90ULL, 0x3ca8b3c02c0dc2b2ULL}, {0x400328977e6478eeULL, 0xbca36d46b718e6ccULL},
    {0x40032f588a440713ULL, 0xbca23c69ca1e17d3ULL}, {0x4003361800b39a41ULL, 0x3c8d495806b6060eULL},
    {0x40033cd5e2ff2e27ULL, 0x3c9e27701e92fe5bULL}, {0x400343923270ed82ULL, 0xbc9e07f8bcff97c6ULL},
    {0x40034a4cf05135b4ULL, 0x3c8c3c07cc3e76a8ULL}, {0x400351061de69a58ULL, 0xbcaacb26f2cbfdcdULL},
    {0x400357bdbc75e8c2ULL, 0xbcafdb9a469e505bULL}, {0x40035e73cd422b80ULL, 0x3ca67916e3cdae2fULL},
    {0x40036528518cadd0ULL, 0x3c778112cd824d8fULL}, {0x40036bdb4a94ff05ULL, 0x3caeaf2fda8db90aULL},
    {0x4003728cb998f5f1ULL, 0x3caa5d49dd7cc93aULL}, {0x4003793c9fd4b43bULL, 0xbc9683fdb8434ceaULL},
    {0x40037feafe82a9b1ULL, 0xbc9533919254dc7eULL}, {0x40038697d6db9794ULL, 0x3ca209f2436f3e57ULL},
    {0x40038d432a1693d9ULL, 0x3c832bc212c8ce80ULL}, {0x400393ecf9690c5fULL, 0x3ca9d868a7049335ULL},
    {0x40039a954606ca25ULL, 0xbc859a0a312b44bbULL}, {0x4003a13c1121f46eULL, 0xbc7bd4e18e9010d2ULL},
    {0x4003a7e15beb13e7ULL, 0xbc8927bc9f97f570ULL}, {0x4003ae85279115beULL, 0xbc8b4e1b3902183dULL},
    {0x4003b52775414eb5ULL, 0xbca35807f3ba95aeULL}, {0x4003bbc846277e2bULL, 0x3c93bab6f3afebb5ULL},
    {0x4003c2679b6dd122ULL, 0x3c831545c6ac9bc9ULL}, {0x4003c905763ce537ULL, 0xbc9eb4f67b5a33f8ULL},
    {0x4003cfa1d7bbcb97ULL, 0x3c9ac74235842701ULL}, {0x4003d63cc1100befULL, 0x3c8a76bf82ab3f81ULL},
    {0x4003dcd6335da74eULL, 0xbca61034c6e94561ULL}, {0x4003e36e2fc71b04ULL, 0x3ca9bbfffcd8d172ULL},
    {0x4003ea04b76d637fULL, 0x3c6b660dc91a7129ULL}, {0x4003f099cb6fff14ULL, 0x3ca264c34d78c3adULL},
    {0x4003f72d6cecf0d0ULL, 0x3c915ec12cc04303ULL}, {0x4003fdbf9d00c337ULL, 0x3c8a36847fe91b44ULL},
    {0x400404505cc68b03ULL, 0x3c6c8acafd5a722bULL}, {0x40040adfad57e9d9ULL, 0x3c9b77ec4a340333ULL},
    {0x4004116d8fcd10faULL, 0x3c83ab6d87943390ULL}, {0x400417fa053cc3eaULL, 0x3ca7319903b93926ULL},
    {0x40041e850ebc5b16ULL, 0x3c6473c2ebcb81e7ULL}, {0x4004250ead5fc66dULL, 0xbc9b942c728f96fbULL},
    {0x40042b96e2398ff9ULL, 0xbcaca13f2fd8c03fULL}, {0x4004321dae5ade6eULL, 0xbca87133cc7a789cULL},
    {0x400438a312d377b5ULL, 0xbc94ca34c91f3ea8ULL}, {0x40043f2710b1c370ULL, 0xbc9a2dd2f1eee0e3ULL},
    {0x400445a9a902cd77ULL, 0x3c71f766b5423298ULL}, {0x40044c2adcd24852ULL, 0x3cab1d5c006184b2ULL},
    {0x400452aaad2a8facULL, 0xbca21bdd4ff06a83ULL}, {0x400459291b14aabbULL, 0x3ca8e844d58e3491ULL},
    {0x40045fa627984eb0ULL, 0xbc9aca09ed07c0b0ULL}, {0x40046621d3bbe10fULL, 0xbca32f7f3e95133aULL},
    {0x40046c9c20847a11ULL, 0x3ca5286a100807d0ULL}, {0x400473150ef5e6fbULL, 0xbc92e8c29c1728deULL},
    {0x4004798ca012ac69ULL, 0x3cafa6c1feae240bULL}, {0x40048002d4dc08a2ULL, 0x3ca23aad14bcb114ULL},
    {0x40048677ae51f5d7ULL, 0x3caf0fb15c5c55d8ULL}, {0x40048ceb2d732c6aULL, 0xbc9b68c738a09486ULL},
    {0x4004935d533d2524ULL, 0x3ca3ddea46dd6577ULL}, {0x400499ce20ac1b73ULL, 0x3cafa938757aa7d3ULL},
    {0x4004a03d96bb0f97ULL, 0xbc8bec847a5d51b4ULL}, {0x4004a6abb663c8ceULL, 0xbc76d33aaf9eaaa0ULL},
    {0x4004ad18809ed780ULL, 0xbc901f53449a17fbULL}, {0x4004b383f663975eULL, 0x3caeaeb22a19e670ULL},
    {0x4004b9ee18a83184ULL, 0x3ca41109082d2656ULL}, {0x4004c056e8619e8eULL, 0xbc8c8436a8a33223ULL},
    {0x4004c6be6683a8aeULL, 0x3c9957615c5fb3c7ULL}, {0x4004cd249400edbfULL, 0xbcae26bd94a9392bULL},
    {0x4004d38971cae14aULL, 0xbca7d612a00803ceULL}, {0x4004d9ed00d1ce92ULL, 0x3ca1157f4e854196ULL},
    {0x4004e04f4204da95ULL, 0x3ca10d02c2915cc4ULL}, {0x4004e6b036520607ULL, 0x3c59aab1360ec472ULL},
    {0x4004ed0fdea62f4dULL, 0xbcae291d8bbeb806ULL}, {0x4004f36e3bed1470ULL, 0x3c922d753c49be15ULL},
    {0x4004f9cb4f115512ULL, 0xbc9a792abd4ba14bULL}, {0x4005002718fc7453ULL, 0x3c7331690aef34a8ULL},
    {0x400506819a96dabfULL, 0xbc9c00f50c919be3ULL}, {0x40050cdad4c7d82dULL, 0xbc99a64b2a765c44ULL},
    {0x40051332c875a5a1ULL, 0x3c84ad633c1267adULL}, {0x4005198976856727ULL, 0x3c7459c8e690b68cULL},
  },
};
static const uint64_t POLY[6] = {0x3fe3333333333333ULL, 0xbfbeb851eb851eb8ULL, 0x3facac083126e979ULL, 0xbfa13404ea4a8c15ULL, 0x3f976577531db446ULL, 0xbf9128467026d989ULL};
static const uint64_t DELTA = 0x3c7999999999999aULL;   /* 3/5 - 0.6(double) */
static const uint64_t LN2 = 0x3fe62e42fefa39efULL;

/* x positive, normal, finite */
static inline double pow06(double x)
{
    uint64_t ix = asuint64(x);
    int e = (int)(ix >> 52) - 1023;
    uint64_t mb = ix & 0x000fffffffffffffULL;
    int i = (int)(mb >> 44);                                   /* top 8 mantissa bits -> 256 intervals */
    double m = asdouble(mb | 0x3ff0000000000000ULL);           /* m in [1,2) */
    double c = 1.0 + (double)(2 * i + 1) * 0.001953125;        /* centre of the interval, exact */
    double r = (m - c) * asdouble(INVC[i]);                    /* m - c is exact */
    int t = 3 * e;
    int k = (t >= 0) ? t / 5 : -((-t + 4) / 5);                /* floor(3e/5) */
    int j = t - 5 * k;                                         /* 0..4 */
    double A1 = asdouble(POLY[0]), A2 = asdouble(POLY[1]), A3 = asdouble(POLY[2]);
    double A4 = asdouble(POLY[3]), A5 = asdouble(POLY[4]), A6 = asdouble(POLY[5]);
    double p = r * (A1 + r * (A2 + r * (A3 + r * (A4 + r * (A5 + r * A6)))));
    double corr = -asdouble(DELTA) * ((double)e * asdouble(LN2) + asdouble(LNC[i]) + r);
    double pt = p + (corr + corr * p);
    double H = asdouble(HT[j][i][0]), Lo = asdouble(HT[j][i][1]);
    double y = H + (Lo + H * pt);
    return y * asdouble((uint64_t)(k + 1023) << 52);           /* exact scaling by 2^k */
}
}  /* namespace pow06lib */

/* Special values for beta = 0.6 are returned directly, with the same values as pow():
     x^0.6    : 0 -> 0,    x < 0 -> nan,  nan -> nan
     x^(-0.4) : 0 -> +inf, x < 0 -> nan,  nan -> nan
   IterateToQnew relies on them: a nan (first guess or Newton step below 0, or 0^(-0.4) = inf
   in the first guess) is caught by mmax, which restarts Newton at 1e-30 or returns 0. */
static const uint64_t BETA06 = 0x3fe3333333333333ULL;   /* the double 0.6 */

/* x^beta: fast path for beta = 0.6 and x positive, normal, finite; otherwise the general ownpow() */
static inline double powbeta(double x, double beta)
{
    uint64_t ix = ownpowlib::asuint64(x);
    if (ownpowlib::asuint64(beta) == BETA06) {
        if (ix - 0x0010000000000000ULL < 0x7fe0000000000000ULL)   /* x positive, normal, finite */
            return pow06lib::pow06(x);
        if (x == 0.0)
            return 0.0;                                          /* also -0: pow(-0, 0.6) = +0 */
        if (x < 0.0)
            return ownpowlib::math_invalid(x);                   /* nan */
        if (x != x)
            return x + beta;                                     /* nan */
    }
    return ownpow(x, beta);                                      /* other beta, subnormal, inf */
}

/* x^(beta-1) for x that is not positive and finite */
static inline double powbeta1special(double x, double beta)
{
    if (ownpowlib::asuint64(beta) == BETA06) {
        if (x == 0.0)
            return ownpowlib::asdouble(0x7ff0000000000000ULL);   /* +inf, also for -0 */
        if (x < 0.0)
            return ownpowlib::math_invalid(x);                   /* nan */
        if (x != x)
            return x + (beta - 1);                               /* nan */
    }
    return ownpow(x, beta - 1);                                  /* other beta, inf */
}

/* x positive and finite (subnormal included) */
static inline int posfinite(double x)
{
    return ownpowlib::asuint64(x) - 1 < 0x7ff0000000000000ULL - 1;
}

/* x^(beta-1) = x^beta / x for x positive and finite */
static inline double powbeta1(double x, double beta)
{
    if (posfinite(x))
        return powbeta(x, beta) / x;
    return powbeta1special(x, beta);
}
/* ====================== end of special x^0.6 ============================ */


/* Q^beta and Q^(beta-1) with one pow(): for Q positive and finite, Q^(beta-1) = Q^beta / Q
   (mathematically identical, a division is exact the same way on every processor).
   For Q <= 0 and nan the same values as pow() (see above). */
static inline void powpair(double Q, double beta, double *pb, double *pb1)
{
    *pb = powbeta(Q, beta);
    if (posfinite(Q))
        *pb1 = *pb / Q;
    else
        *pb1 = powbeta1special(Q, beta);
}


static double IterateToQnew(double Qin, double Qold, double q, double alpha, double beta,double deltaT, double deltaX)
{
    /* Q at loop k+1 for i+1, j+1 */
    double ab_pQ, deltaTX, C;
    int   count;

    double Qkx;
    double fQkx;
    double dfQkx;
    double pQkx, pQkx1;
    double epsilon;
    int MAX_ITERS;

    MAX_ITERS = 10;
    epsilon =  0.0001;
    /* if no input then output = 0 */
    if ((Qin+Qold+q) == 0)
        return(0);

    /* common terms */
    ab_pQ = alpha*beta*powbeta1(((Qold+Qin)/2), beta);
    deltaTX = deltaT/deltaX;
    C = deltaTX*Qin + alpha*powbeta(Qold,beta) + deltaT*q;

    /*  1. Initial guess Qk1.             */
    /*  2. Evaluate function f at Qkx.    */
    /*  3. Evaluate derivative df at Qkx. */
    /*  4. Check convergence.             */

    /*
     * There's a problem with the first guess of Qkx. fQkx is only defined
     * for Qkx's > 0. Sometimes the first guess results in a Qkx+1 which is
     * negative or 0. In that case we change Qkx+1 to 1e-30. This keeps the
     * convergence loop healthy.
     */
    Qkx   = (deltaTX * Qin + Qold * ab_pQ + deltaT * q) / (deltaTX + ab_pQ);
    powpair(Qkx, beta, &pQkx, &pQkx1);                 /* Q^beta and Q^(beta-1) */
    fQkx  = deltaTX * Qkx + alpha * pQkx - C;           /* Current k */
    dfQkx = deltaTX + alpha * beta * pQkx1;             /* Current k */
    Qkx   -= fQkx / dfQkx;                                  /* Next k */
    Qkx   = mmax(Qkx, 1e-30);
    count = 0;

    do
    {
      powpair(Qkx, beta, &pQkx, &pQkx1);                 /* Q^beta and Q^(beta-1) */
      fQkx  = deltaTX * Qkx + alpha * pQkx - C;           /* Current k */
      dfQkx = deltaTX + alpha * beta * pQkx1;             /* Current k */
      Qkx   -= fQkx / dfQkx;                                /* Next k */
      count++;
    } while(fabs(fQkx) > epsilon && count < MAX_ITERS);

    return(mmax(Qkx,0.0));
}


void kinematic(double * Qold,double * q,long long* dirDown,long long* dirUpLen,long long* dirUpID,double * Qnew, double * alpha, double beta, double deltaT, double * deltaX, int size){

    int i,j;
    long long minID,maxID,down;
    double Qin;

    for(i=0;i<size;i++){

        Qin = 0.0;
        down = dirDown[i];

        minID = dirUpLen[down];
        maxID = dirUpLen[down+1];
        for(j=minID;j<maxID;j++)
            Qin += Qnew[dirUpID[j]];

        Qnew[down] = IterateToQnew(Qin,Qold[down],q[down],alpha[down],beta,deltaT,deltaX[down]);
    }
}


void runoffConc(double * conc, double * peak, double * fraction, double * flow, int maxlag, int size){

    int i,k,lag;
    double lag1, lag2;
    double * lag1alt = new double[size];
    double * div = new double[size];
    double * areaFractionOld = new double[size];
    double * area = new double[size];
    double * areaAlt = new double[size];
    double * areaFraction = new double[size];
    double * areaFractionSum = new double[size];

    for(i=0;i<size;i++){
        div[i] = 2 * (peak[i] * peak[i]);          /* x^2 as x*x: exact, same on every platform */
        areaFractionOld[i] = 0.0;
    }

    for(lag=0;lag<maxlag;lag++){
        double lag1 = lag + 1;
        lag2 = lag1 * lag1;

        for(i=0;i<size;i++){

            lag1alt[i] = 2 * peak[i] - lag1;
            area[i] = lag2 / div[i];
            areaAlt[i] = 1 - (lag1alt[i] * lag1alt[i]) / div[i];

            if (lag1 > peak[i]) areaFractionSum[i] = areaAlt[i];
            else    areaFractionSum[i] = area[i];
            if (lag1alt[i] < 1) areaFractionSum[i] = 1.0;

            areaFraction[i] = areaFractionSum[i] - areaFractionOld[i];
            areaFractionOld[i] = areaFractionSum[i];

            k = lag * size + i;
            conc[k] = conc[k] + fraction[i] * flow[i] * areaFraction[i];

        }
    }

        delete [] div;
        delete [] lag1alt;
        delete [] areaFractionOld;
        delete [] area;
        delete [] areaAlt;
        delete [] areaFraction;
        delete [] areaFractionSum;
}


/* =========================================================================
   new: level-parallel kinematic wave
   ========================================================================= */

int kinematicParVersion(void){ return 4; }   /* 4: own pow() + one pow() per Newton step + special x^0.6 */

double ownPow(double x, double y){ return ownpow(x, y); }
double ownPow06(double x){ return powbeta(x, 0.6); }

int kinematicParMaxThreads(void){
    unsigned int n = std::thread::hardware_concurrency();
    return (n == 0) ? 1 : (int) n;
}


/* Compute the level of every cell.
   dirDown    : cells in routing order (every cell after all its upstream cells), length size
   dirUpLen   : CSR start index of the upstream cells of each cell, length ncells+1
   dirUpID    : upstream cell ids
   size       : length of dirDown (number of cells routed)
   ncells     : number of cells (length of Qold, Qnew, ...)
   levelOrder : out, length size: the cells sorted by level (stable: dirDown order inside a level)
   levelStart : out, length >= size+1: levelStart[l] .. levelStart[l+1]-1 are the cells of level l
   returns    : number of levels (0 if size == 0)                                                 */
int kinematicLevels(long long* dirDown, long long* dirUpLen, long long* dirUpID, int size, int ncells,
                    long long* levelOrder, long long* levelStart){

    if (size <= 0) { levelStart[0] = 0; return 0; }

    std::vector<long long> level(ncells, 0);
    long long maxlev = 0;
    for(int i=0;i<size;i++){
        long long down = dirDown[i];
        long long lev = 0;
        for(long long j=dirUpLen[down]; j<dirUpLen[down+1]; j++){
            long long l = level[dirUpID[j]] + 1;
            if (l > lev) lev = l;
        }
        level[down] = lev;
        if (lev > maxlev) maxlev = lev;
    }
    int nlevels = (int)(maxlev + 1);

    /* counting sort by level, stable (keeps the dirDown order inside a level) */
    std::vector<long long> count(nlevels + 1, 0);
    for(int i=0;i<size;i++) count[level[dirDown[i]] + 1]++;
    for(int l=0;l<nlevels;l++) count[l+1] += count[l];
    for(int l=0;l<=nlevels;l++) levelStart[l] = count[l];
    for(int i=0;i<size;i++){
        long long down = dirDown[i];
        levelOrder[count[level[down]]++] = down;
    }
    return nlevels;
}


/* one cell: identical arithmetic to kinematic() */
static inline void cellQ(long long down, const double* Qold, const double* q,
                         const long long* dirUpLen, const long long* dirUpID, double* Qnew,
                         const double* alpha, double beta, double deltaT, const double* deltaX){
    double Qin = 0.0;
    long long minID = dirUpLen[down];
    long long maxID = dirUpLen[down+1];
    for(long long j=minID;j<maxID;j++)
        Qin += Qnew[dirUpID[j]];
    Qnew[down] = IterateToQnew(Qin,Qold[down],q[down],alpha[down],beta,deltaT,deltaX[down]);
}


struct KinJob {
    const double* Qold; const double* q;
    const long long* levelOrder; const long long* levelStart;
    int lastPar;                 /* last level computed in parallel (levels after it: serial by the master) */
    const long long* dirUpLen; const long long* dirUpID;
    double* Qnew; const double* alpha; double beta; double deltaT; const double* deltaX;
};


/* Persistent pool: nthreads-1 worker threads + the calling (master) thread.
   Between calls the workers sleep on a condition variable; inside a call the
   threads synchronise with a spinning barrier after every level.            */
class KinPool {
public:
    KinPool() : nthreads(1), stop(false), epoch(0), arrived(0), generation(0) {}
    ~KinPool() { shutdown(); }

    void resize(int n){
        if (n == nthreads) return;
        shutdown();
        nthreads = n;
        stop = false;
        arrived.store(0); generation.store(0);
        /* new workers start with the current epoch, so they wait for the next run()
           instead of starting a pass on the stale job */
        long seen0 = epoch.load(std::memory_order_acquire);
        for(int t=1;t<nthreads;t++)
            workers.push_back(std::thread(&KinPool::worker, this, t, seen0));
    }

    void run(const KinJob& j){
        {
            std::lock_guard<std::mutex> lk(mu);
            job = j;
            epoch.fetch_add(1, std::memory_order_release);
        }
        cv.notify_all();
        work(0);
    }

private:
    int nthreads;
    bool stop;
    std::vector<std::thread> workers;
    std::mutex mu;
    std::condition_variable cv;
    std::atomic<long> epoch;
    std::atomic<int>  arrived;
    std::atomic<long> generation;
    KinJob job;

    void shutdown(){
        if (workers.empty()) return;
        {
            std::lock_guard<std::mutex> lk(mu);
            stop = true;
        }
        cv.notify_all();
        for(size_t t=0;t<workers.size();t++) workers[t].join();
        workers.clear();
    }

    void worker(int tid, long seen){
        for(;;){
            {
                std::unique_lock<std::mutex> lk(mu);
                cv.wait(lk, [&]{ return stop || epoch.load(std::memory_order_acquire) != seen; });
                if (stop) return;
                seen = epoch.load(std::memory_order_acquire);
            }
            work(tid);
        }
    }

    /* sense-reversing spin barrier */
    void barrier(){
        long gen = generation.load(std::memory_order_acquire);
        if (arrived.fetch_add(1, std::memory_order_acq_rel) + 1 == nthreads){
            arrived.store(0, std::memory_order_relaxed);
            generation.store(gen + 1, std::memory_order_release);
        } else {
            int spins = 0;
            while (generation.load(std::memory_order_acquire) == gen){
                if (++spins > 4000) { std::this_thread::yield(); spins = 0; }
            }
        }
    }

    void work(int tid){
        const KinJob& j = job;
        for(int lev=0; lev<=j.lastPar; lev++){
            long long s = j.levelStart[lev], e = j.levelStart[lev+1];
            long long n = e - s;
            long long chunk = (n + nthreads - 1) / nthreads;
            long long a = s + tid * chunk;
            long long b = a + chunk; if (b > e) b = e;
            for(long long i=a;i<b;i++)
                cellQ(j.levelOrder[i], j.Qold, j.q, j.dirUpLen, j.dirUpID, j.Qnew, j.alpha, j.beta, j.deltaT, j.deltaX);
            barrier();
        }
    }
};

static KinPool pool;
static std::mutex poolMutex;   /* kinematicPar is not re-entrant: one call at a time */


void kinematicPar(double * Qold, double * q, long long* levelOrder, long long* levelStart, int nlevels,
                  long long* dirUpLen, long long* dirUpID, double * Qnew, double * alpha, double beta,
                  double deltaT, double * deltaX, int nthreads){

    if (nlevels <= 0) return;
    int maxt = kinematicParMaxThreads();
    if (nthreads > maxt) nthreads = maxt;
    if (nthreads > 64) nthreads = 64;

    /* levels with fewer cells than this are not worth a barrier */
    long long minPar = 4LL * nthreads;
    int lastPar = -1;
    if (nthreads > 1){
        for(int lev=nlevels-1; lev>=0; lev--){
            if (levelStart[lev+1] - levelStart[lev] >= minPar) { lastPar = lev; break; }
        }
    }

    if (lastPar >= 0){
        std::lock_guard<std::mutex> lk(poolMutex);
        pool.resize(nthreads);
        KinJob j;
        j.Qold = Qold; j.q = q; j.levelOrder = levelOrder; j.levelStart = levelStart; j.lastPar = lastPar;
        j.dirUpLen = dirUpLen; j.dirUpID = dirUpID; j.Qnew = Qnew; j.alpha = alpha; j.beta = beta;
        j.deltaT = deltaT; j.deltaX = deltaX;
        pool.run(j);
    }

    /* remaining (small) levels, or everything if nthreads <= 1: serial in level order */
    for(long long i=levelStart[lastPar+1]; i<levelStart[nlevels]; i++)
        cellQ(levelOrder[i], Qold, q, dirUpLen, dirUpID, Qnew, alpha, beta, deltaT, deltaX);
}
