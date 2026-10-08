library(sf)
library(terra)
library(ggplot2)

swl_sim <- rast("p:/watmodel/cwatm/model/cwatm_modflow_layers/Toolkit/Calibration_modflow/runs_calibration_old/run_165/165/swl_out.tif")
plot(swl_sim)

swl_obs <- sf::read_sf("p:/watmodel/cwatm/model/cwatm_modflow_layers/Toolkit/Calibration_modflow/observed_data/boreholes_harmonized_clean.shp")


if (st_crs(swl_obs) != st_crs(swl_sim)) {
  print("CRS mismatch detected! Reprojecting points to match raster...")
  swl_obs <- st_transform(swl_obs, st_crs(swl_sim))
}

# 3. Extract the raster values
# terra::extract accepts sf objects natively
extracted_values <- extract(swl_sim, swl_obs)

# 4. Bind the results back into your original sf object dataframe
# extracted_values returns a dataframe where the first column is 'ID' 
# and subsequent columns are the raster band names.
my_points_with_data <- cbind(swl_obs, extracted_values)

# Inspect your new dataset
print(head(my_points_with_data))

my_points_with_data$error <- my_points_with_data$swl_out - my_points_with_data$SWL
my_points_with_data$errorPrcnt <- (my_points_with_data$swl_out - my_points_with_data$SWL)/my_points_with_data$SWL
summary(my_points_with_data$error)
summary(my_points_with_data$errorPrcnt)
my_points_with_data$errorPrcnt_cap <- ifelse(my_points_with_data$errorPrcnt > 10, 10, my_points_with_data$errorPrcnt)
hist(my_points_with_data$error)
ggplot(my_points_with_data, aes(x = error, y = ..count..)) + geom_histogram()
ggplot(my_points_with_data) + geom_sf(aes(color = error)) + scale_color_viridis_c()
ggplot(my_points_with_data) + geom_sf(aes(color = errorPrcnt_cap)) + scale_color_viridis_c()
