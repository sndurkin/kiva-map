This project holds code used to generate world map visualizations using data from Kiva. It has the code to generate the main Kiva map using the data from their snapshot, as well as custom maps for a given lender or lending team.

#### Installation steps for Ubuntu 11.10

1. Download this repo https://github.com/sndurkin/kiva-map.git
2. Install R: `sudo apt-get install r-base`
3. Install libxt: `sudo apt-get install libxt-dev`
4. Install Cairo graphics library: `sudo apt-get install libcairo2-dev`
5. Install R packages:
   * `R`
   * (within R) `install.packages("maps,mapproj,geosphere,Cairo,png,bigmemory,rjson")`

#### Generating the Kiva world map

1. Download a Kiva data snapshot from http://build.kiva.org in JSON format: http://s3.kiva.org/snapshots/kiva_ds_json.zip
2. Unzip it in the `kiva-map` directory
3. `python process_loans.py #`, where `#` is the number of loan files you wish to process; this will generate 3 csv files
4. Create a `data` folder and copy the csv files to it
5. Execute the R script to generate the image: `Rscript kiva.R ~/kiva-map` (You can pass the first argument to the script as the filepath, otherwise it will use the current directory)
6. This will generate `images/kiva.png`

#### Generating an image for your team's last 20 loans

1. `wget -O loans/2.json http://api.kivaws.org/v1/teams/#/loans.json` (where `#` is your tean's number, e.g. Reddit is `2498`)
2. `python process_loans.py 1` (Wait for output, it will take a while...)
3. `R --file=kiva.R`
4. This produces a new `images/kiva.png` with your team's loans visualized

#### Generating an image for a lender or lending team

1. `python generate_custom_map <L|T> <lender id|team shortname>`