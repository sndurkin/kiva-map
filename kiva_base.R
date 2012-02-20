library(maps)
library(mapproj)
library(geosphere)
library(Cairo)
library(png)
library(bigmemory)

# Initialize global variables.
ABSOLUTE_DATA_PATH <- "C:/Projects/kiva-map/data/"
FILE_PATH <- "C:/Projects/kiva-map/images/kiva_base.png"
LENDER_LOCATIONS_FILE_NAME <- "lender_locations"
LOAN_LOCATIONS_FILE_NAME <- "loan_locations"
LENDER_LOANS_FILE_NAME <- "lender_loans"
DISTANCE_RANGE_NUM <- 10
WIDTH <- 4096
HEIGHT <- 2048
MAX_LINES_TO_DRAW <- 100000


# Read in and sort the lender-loan data.
lenderLoanData <- try(attach.big.matrix(sprintf("%s%s.desc", ABSOLUTE_DATA_PATH, LENDER_LOANS_FILE_NAME)), silent=TRUE)
if(is.big.matrix(lenderLoanData) == FALSE) {
    lenderLoanData <- read.big.matrix(sprintf("%s%s.csv", ABSOLUTE_DATA_PATH, LENDER_LOANS_FILE_NAME),
                                      type="double", header=TRUE, sep=";",
                                      extraCols="sortValue",
                                      backingpath=ABSOLUTE_DATA_PATH,
                                      backingfile=sprintf("%s.bin", LENDER_LOANS_FILE_NAME),
                                      descriptorfile=sprintf("%s.desc", LENDER_LOANS_FILE_NAME))
    
    # Sort by a function on distance and lender-loan count.
    len <- length(lenderLoanData[,1])
    maxDistance <- max(lenderLoanData[,4])
    maxLenderLoanCount <- max(lenderLoanData[,3])
    rangeLen <- maxDistance / DISTANCE_RANGE_NUM
    for(i in 1:len) {
        lenderLoanData[i,9] <- (floor((maxDistance - lenderLoanData[i,4]) / rangeLen) * maxLenderLoanCount) + lenderLoanData[i,3]
    }
    mpermute(lenderLoanData, order=morder(lenderLoanData, 9, decreasing=FALSE))
}
maxSortValue <- max(lenderLoanData[,9])

# Draw the lender-loan data.
linePal <- colorRampPalette(c("#030a02", "#0f3708"))
lineColors <- linePal(100)
len <- length(lenderLoanData[,1])
for(i in 1:len) {
    if(i %% 1000 == 1) {
        print(sprintf("i: %d", i))
        flush.console()
    }
    
    # On every [MAX_LINES_TO_DRAW]th iteration, stop calculation and write to the image.
    if(i %% MAX_LINES_TO_DRAW == 1) {
        if(i > 1) {
            dev.off()
            gc()
            
            print("created PNG, collected garbage")
            flush.console()
        }
        
        # Read in the current image on file.
        baseImg <- try(readPNG(FILE_PATH, native=TRUE), silent=TRUE)
        
        # Open the image for writing.
        CairoPNG(FILE_PATH, width=WIDTH, height=HEIGHT, bg="black")
        
        # Draw the world.
        map("world", col="black", fill=TRUE, bg="black", lwd=0.05, mar=c(0,0,0,0), border=0, xlim=c(-180, 180), ylim=c(-90, 90))
        
        # Draw the image base (if there is one).
        if(class(baseImg) != "try-error") {
            lim <- par()
            rasterImage(baseImg, lim$usr[1], lim$usr[3], lim$usr[2], lim$usr[4])
            
            print("read in and drew image")
            flush.console()
        }
        else {
            print("couldn't find image")
            flush.console()
        }
    }
    
    pair <- lenderLoanData[i,]
    
    colIndex <- ceiling((pair[9] / maxSortValue) * length(lineColors))
    color <- lineColors[colIndex]
    
    inter <- gcIntermediate(c(pair[6], pair[5]), c(pair[8], pair[7]), n=300, breakAtDateLine=TRUE, addStartEnd=TRUE)
    if(typeof(inter) == "list") {
        lines(inter[[1]], col=color, lwd=0.2)
        lines(inter[[2]], col=color, lwd=0.2)
    }
    else {
        lines(inter, col=color, lwd=0.2)
    }
}

# Read in and sort the lender data.
lenderLocations <- try(attach.big.matrix(sprintf("%s%s.desc", ABSOLUTE_DATA_PATH, LENDER_LOCATIONS_FILE_NAME)), silent=TRUE)
if(is.big.matrix(lenderLocations) == FALSE) {
    lenderLocations <- read.big.matrix(sprintf("%s%s.csv", ABSOLUTE_DATA_PATH, LENDER_LOCATIONS_FILE_NAME),
                                       type="double", header=TRUE, sep=";",
                                       backingpath=ABSOLUTE_DATA_PATH,
                                       backingfile=sprintf("%s.bin", LENDER_LOCATIONS_FILE_NAME),
                                       descriptorfile=sprintf("%s.desc", LENDER_LOCATIONS_FILE_NAME))
    
    # Sort by the lender count.
    mpermute(lenderLocations, order=morder(lenderLocations, 4))
}
maxLenderCount <- max(lenderLocations[,4])

# Draw the lender points.
for (j in 1:length(lenderLocations[,1])) {
    points(lenderLocations[j,3], lenderLocations[j,2], pch=20, col="#021870", cex=0.4)
}

# Read in and sort the loan data.
destPairs <- try(attach.big.matrix(sprintf("%s%s.desc", ABSOLUTE_DATA_PATH, LOAN_LOCATIONS_FILE_NAME)), silent=TRUE)
if(is.big.matrix(destPairs) == FALSE) {
    destPairs <- read.big.matrix(sprintf("%s%s.csv", ABSOLUTE_DATA_PATH, LOAN_LOCATIONS_FILE_NAME),
                                 type="double", header=TRUE, sep=";",
                                 backingpath=ABSOLUTE_DATA_PATH,
                                 backingfile=sprintf("%s.bin", LOAN_LOCATIONS_FILE_NAME),
                                 descriptorfile=sprintf("%s.desc", LOAN_LOCATIONS_FILE_NAME))
    
    # Sort by the loan count.
    mpermute(destPairs, order=morder(destPairs, 4))
}
maxLoanCount <- max(destPairs[,4])

# Draw the loan points.
for (k in 1:length(destPairs[,1])) {
    points(destPairs[k,3], destPairs[k,2], pch=20, col="#656218", cex=0.5)
}

# Write the last of the lines and all the points to the image.
dev.off()