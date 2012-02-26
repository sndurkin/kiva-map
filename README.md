This project holds code used to generate world map visualizations using data from Kiva. It has the code for:

* generating the Kiva world map using the data from their snapshot
* generating a custom map for a given lender or lending team

#### Kiva world map (generated with `process_loans.py` and `kiva.R`)
![kiva world map](https://github.com/sndurkin/kiva-map/raw/master/images/kiva-small.png)

#### Installation steps for Ubuntu 11.10

1. Download this repo https://github.com/sndurkin/kiva-map.git
2. Install R: `sudo apt-get install r-base`
3. Install libxt: `sudo apt-get install libxt-dev`
4. Install Cairo graphics library: `sudo apt-get install libcairo2-dev`
5. Install R packages:
   * `R`
   * (within R) `install.packages("maps,mapproj,geosphere,Cairo,png,bigmemory,rjson")`

#### Generating a map for a specific lender or lending team

1. `python generate_custom_map.py <L|T> <lender id|team shortname>`
  * Example: `python generate_custom_map.py T buildkiva`
  * After all data has been processed, this will execute `draw_custom_map.R` to generate an image in the `images/` directory.
  * If the script exits with a message saying "Too many errors encountered, exiting the script", they are most likely due to connection issues. You can keep re-executing the script and it will work off of existing data (stored in the `data/` directory) until it has all been processed.

#### Generating the Kiva world map (for all lenders and loans)

1. Download a Kiva data snapshot from http://build.kiva.org in JSON format: http://s3.kiva.org/snapshots/kiva_ds_json.zip
2. Unzip it in the `kiva-map` directory
3. `python process_loans.py #`, where `#` is the number of loan files you wish to process
  * This will generate 3 `csv` files (as well as a couple other metadata files).
4. Create a `data` folder and copy the csv files to it
5. Execute the R script to generate the image: `Rscript kiva.R ~/kiva-map`
  * You can pass the first argument to the script as the filepath, otherwise it will use the current directory.
6. This will generate `images/kiva.png`