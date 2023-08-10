/* common terms */
#include <math.h>
#include <stdio.h>
#include <vector>
#include <algorithm>
#define mmax(x, y) ((x > y) ? (x) : (y))

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

/* https://bumbershootsoft.wordpress.com/2019/04/07/working-with-dlls-on-windows-mac-and-linux/ */

DLLEXPORT void ups(long long* in_array,long long* dirshort, double * out_array, int size);
DLLEXPORT void dirID(long long* lddorder, long long* ldd, long long* out_array, int sizei, int sizej);
DLLEXPORT void repairLdd1(long long * ldd, int sizei, int sizej);
DLLEXPORT void repairLdd2(long long* ldd, long long* dir,long long* check, int sizei);
DLLEXPORT void kinematic(double * Qold, double * q,long long* dirDown,long long* dirUpLen, long long* dirUpID, double * Qnew,double * alpha, double beta, double deltaT, double * deltaX, int size);

DLLEXPORT void runoffConc(double * conc, double * peak, double * fraction, double * flow, int maxlag, int size);



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

    /*for(i=0;i<sizei;i++){
        for(j=0;j<sizej;j++){
           printf("%d %d %d ", i,j,ldd[i*sizej+j]);
        }  
    }*/

    
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
            // std::cout << someVector[kk];
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

	
			
// dir3 = np.array([[ (lddOrder[y+dirY[lddnp[y][x]],x+dirX[lddnp[y][x]]])   for x in xrange(xi)] for y in xrange(yi)])
/*
for y in xrange(yi):
   for x in xrange(xi):
      value = lddnp[y][x]
      if (value!=0) and (value <> 5):
         dir[y,x]=lddOrder[y+dirY[value],x+dirX[value]]  */

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


           //printf ("i %d j %d k %d  %d %d %d %d\n", i,j,k,lddvalue,x,y,k1);
           //printf ("in %e \n", in_array[i * sizej + j]);
           //out_array[i * sizej + j] = cos(in_array[i * sizej + j]);

        }
    }
}









static double IterateToQnew(double Qin, double Qold, double q, double alpha, double beta,double deltaT, double deltaX)
{
    /* Q at loop k+1 for i+1, j+1 */
    double ab_pQ, deltaTX, C;
    int   count;

    double Qkx;
    double fQkx;
    double dfQkx;
    double epsilon;
    int MAX_ITERS;

    MAX_ITERS = 10;
    epsilon =  0.0001;
    /* if no input then output = 0 */
    if ((Qin+Qold+q) == 0)
        return(0);

    /* common terms */
    ab_pQ = alpha*beta*pow(((Qold+Qin)/2),beta-1);
    deltaTX = deltaT/deltaX;
    C = deltaTX*Qin + alpha*pow(Qold,beta) + deltaT*q;

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
    fQkx  = deltaTX * Qkx + alpha * pow(Qkx, beta) - C;   /* Current k */
    dfQkx = deltaTX + alpha * beta * pow(Qkx, beta - 1);  /* Current k */
    Qkx   -= fQkx / dfQkx;                                /* Next k */
    /*Qkx   = MAX(Qkx, 1e-30);*/
    Qkx   = mmax(Qkx, 1e-30);
    count = 0;

    do
    {
      fQkx  = deltaTX * Qkx + alpha * pow(Qkx, beta) - C;   /* Current k */
      dfQkx = deltaTX + alpha * beta * pow(Qkx, beta - 1);  /* Current k */
      Qkx   -= fQkx / dfQkx;                                /* Next k */
      count++;
    } while(fabs(fQkx) > epsilon && count < MAX_ITERS);

    /*Qk1 = Qkx;*/
    /*Qk1 = max(Qk1,0.0);*/

    return(mmax(Qkx,0.0));
}

void kinematic(double * Qold,double * q,long long* dirDown,long long* dirUpLen,long long* dirUpID,double * Qnew, double * alpha, double beta, double deltaT, double * deltaX, int size){

    int i,j;
    long long minID,maxID,down;
    double Qin;

	
    for(i=0;i<size;i++){

        Qin = 0.0;
        down = dirDown[i];
        /*printf("------------- %u %u\n", i,down); */

        minID = dirUpLen[down];
        maxID = dirUpLen[down+1];
        for(j=minID;j<maxID;j++)
            Qin += Qnew[dirUpID[j]];
            /*printf("  -> ID %u %u %u %u  \n", minID,maxID,j,id);
            printf("Qnew_id  %g \n", Qnew[id]);
        printf("Qin %g \n", Qin);
        printf("Qold %g \n", Qold[down]);  */

        Qnew[down] = IterateToQnew(Qin,Qold[down],q[down],alpha[down],beta,deltaT,deltaX[down]);
        //Qnew[down] = Qin;
        //printf("Qnew_down %u %g \n",down, Qnew[down]);
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
		div[i] = 2 * pow(peak[i], 2);
		areaFractionOld[i] = 0.0;
	}

	for(lag=0;lag<maxlag;lag++){
		double lag1 = lag + 1;
		lag2 = pow(lag1, 2);
		
		for(i=0;i<size;i++){

			lag1alt[i] = 2 * peak[i] - lag1;
			area[i] = lag2 / div[i];
            areaAlt[i] = 1 - pow(lag1alt[i], 2) / div[i];
			
			if (lag1 > peak[i]) areaFractionSum[i] = areaAlt[i];
			else 	areaFractionSum[i] = area[i];
			if (lag1alt[i] < 1)	areaFractionSum[i] = 1.0;
			
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

	// source http://stackoverflow.com/questions/24040984/transformation-using-triangular-weighting-function-in-python
	
}
		
