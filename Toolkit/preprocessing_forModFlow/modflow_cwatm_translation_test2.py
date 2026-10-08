import numpy as np
import matplotlib.pyplot as plt

res_ModFlow = 500.
nrow, ncol = 566, 586
indexes = {}

indexes['CWATMindex'] = np.loadtxt("ModFlow_input/newModFlow_inputs500m_Bhima/CWATMindex.txt").astype(int)
# Contains CWATM index corresponding to each ModFlow cell
indexes['Weight'] = np.loadtxt("ModFlow_input/newModFlow_inputs500m_Bhima/Weight.txt")  # Importing weight for projection

pump = np.full(118400, 0.1)
# # CWatM 2D groundwater pumping array is converted into Modflow 2D array
pumping = indexes['Weight'] * pump[indexes['CWATMindex']]
pumping = pumping.reshape(nrow, ncol)

plt.imshow(pumping)
plt.show()

plt.figure()
plt.imshow(np.reshape(indexes['CWATMindex'],(nrow, ncol)))
plt.show()

plt.figure()
plt.imshow(np.reshape(indexes['Weight'],(nrow, ncol)))
plt.colorbar()
plt.show()

print(np.max(indexes['Weight']))
