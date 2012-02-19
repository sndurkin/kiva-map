library(maps)
library(mapproj)
library(geosphere)
library(Cairo)
library(bigmemory)

# Initialize global variables.
ABSOLUTE_DATA_PATH <- "C:/Projects/kiva-map/data/"
FILE_PATH <- "C:/Projects/kiva-map/images/kiva_points.png"
LENDER_LOCATIONS_FILE_NAME <- "lender_locations"
LOAN_LOCATIONS_FILE_NAME <- "loan_locations"
WIDTH <- 4096
HEIGHT <- 2048


# Open the image for writing.
CairoPNG(FILE_PATH, width=WIDTH, height=HEIGHT, bg="black")

# Draw the world.
map("world", col="#191919", fill=TRUE, bg="black", lwd=0.05, mar=c(0,0,0,0), border=0, xlim=c(-180, 180), ylim=c(-90, 90))

# Read in and sort the lender data.
lenderLocations <- try(attach.big.matrix(sprintf("%s%s_points.desc", ABSOLUTE_DATA_PATH, LENDER_LOCATIONS_FILE_NAME)), silent=TRUE)
if(is.big.matrix(lenderLocations) == FALSE) {
    lenderLocations <- read.big.matrix(sprintf("%s%s.csv", ABSOLUTE_DATA_PATH, LENDER_LOCATIONS_FILE_NAME),
                                       type="double", header=TRUE, sep=";",
                                       backingpath=ABSOLUTE_DATA_PATH,
                                       backingfile=sprintf("%s_points.bin", LENDER_LOCATIONS_FILE_NAME),
                                       descriptorfile=sprintf("%s_points.desc", LENDER_LOCATIONS_FILE_NAME))
    
    # Sort by the lender count.
    mpermute(lenderLocations, order=morder(lenderLocations, 4))
}
maxLenderCount <- max(lenderLocations[,4])

# Draw the lender points.
lenderColorPal <- colorRampPalette(c("#1140fa", "#ffffff"))
lenderColors <- lenderColorPal(100)
for (j in 1:length(lenderLocations[,1])) {
    colIndex <- ceiling((lenderLocations[j,4] / maxLenderCount)^(1/4) * length(lenderColors))
    points(lenderLocations[j,3], lenderLocations[j,2], pch=20, col=lenderColors[colIndex], cex=0.4)
}

# Read in and sort the loan data.
loanLocations <- try(attach.big.matrix(sprintf("%s%s_points.desc", ABSOLUTE_DATA_PATH, LOAN_LOCATIONS_FILE_NAME)), silent=TRUE)
if(is.big.matrix(loanLocations) == FALSE) {
    loanLocations <- read.big.matrix(sprintf("%s%s.csv", ABSOLUTE_DATA_PATH, LOAN_LOCATIONS_FILE_NAME),
                                     type="double", header=TRUE, sep=";",
                                     backingpath=ABSOLUTE_DATA_PATH,
                                     backingfile=sprintf("%s_points.bin", LOAN_LOCATIONS_FILE_NAME),
                                     descriptorfile=sprintf("%s_points.desc", LOAN_LOCATIONS_FILE_NAME))
    
    # Sort by the loan count.
    mpermute(loanLocations, order=morder(loanLocations, 4))
}
maxLoanCount <- max(loanLocations[,4])

# Draw the loan points.
loanColorPal <- colorRampPalette(c("#8e8a22", "#d5d052"))
loanColors <- loanColorPal(100)
for (k in 1:length(loanLocations[,1])) {
    colIndex <- ceiling((loanLocations[k,4] / maxLoanCount)^(1/4) * length(loanColors))
    points(loanLocations[k,3], loanLocations[k,2], pch=20, col=loanColors[colIndex], cex=0.5)
}

# Write the points to the image.
dev.off()