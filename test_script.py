import pandas as pd
import numpy as np
xl_settings_file_path = 'cwatm_settings.xlsx.'
df = pd.read_excel(xl_settings_file_path, sheet_name='Reservoirs_downstream')
min_ID = min([int(float(i)) for i in list(df)[2:]])
max_ID = max([int(float(i)) for i in list(df)[2:]])
waterBodyID_C = range(min_ID, max_ID+1)
waterBodyID_C = [int(i) for i in waterBodyID_C]

reservoir_release = [[-1 for i in waterBodyID_C] for i in range(366)]

for res in list(df)[2:]:
    #res_index = waterBodyID_C.index(int(float(res)))
    res_index = np.where(waterBodyID_C == int(float(res)))[0][0]
    print(res_index)

    #for day in range(366):
    #    reservoir_release[day][res_index] = df[res][day]
