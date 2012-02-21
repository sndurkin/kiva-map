library(maps)
library(mapproj)
library(geosphere)
library(Cairo)
library(png)
library(rjson)

# Read the command-line args.
args <- commandArgs(trailingOnly = TRUE)

cfg <- fromJSON(paste(readLines("custom_cfg.json"), collapse=""))

# Initialize global vars.
DISTANCE_RANGE_NUM <- 10
ID <- args[2]

# Open the image for writing.
CairoPNG(sprintf("images/%s.png", ID), width=cfg$imgWidth, height=cfg$imgHeight, bg=cfg$backgroundColor)

# Draw the world.
map("world", col=cfg$continentsColor, fill=TRUE, bg=cfg$backgroundColor, lwd=0.05, mar=c(0,0,0,0), border=0, xlim=c(-180, 180), ylim=c(-90, 90))


# Read in and sort the lenders and loans.
lenderLocations <- read.csv(sprintf("data/%s_lenders.csv", ID), header=TRUE, sep=";", as.is=TRUE)
maxLenderCount <- max(lenderLocations$count)
order(lenderLocations$count, decreasing=FALSE)

loanLocations <- read.csv(sprintf("data/%s_loans.csv", ID), header=TRUE, sep=";", as.is=TRUE)
maxLoanCount <- max(loanLocations$count)
order(loanLocations$count, decreasing=FALSE)

# Read in the lender-loan data.
lenderLoanData <- read.csv(sprintf("data/%s_lender_loans.csv", ID), header=TRUE, sep=";", as.is=TRUE)
maxDistance <- max(lenderLoanData$distance)
maxLenderLoanCount <- max(lenderLoanData$count)

# Sort by a function on distance and lender-loan count.
len <- length(lenderLoanData[,1])
maxDistance <- max(lenderLoanData$distance)
maxLenderLoanCount <- max(lenderLoanData$count)
rangeLen <- maxDistance / DISTANCE_RANGE_NUM
lenderLoanData$sortValue <- (floor((maxDistance - lenderLoanData$distance) / rangeLen) * maxLenderLoanCount) + lenderLoanData$count
maxSortValue <- max(lenderLoanData$sortValue)
order(lenderLoanData$sortValue, decreasing=FALSE)


# Draw the lender-loan data.
linePal <- colorRampPalette(c(cfg$lenderLoanLines$darkestColor, cfg$lenderLoanLines$lightestColor))
lineColors <- linePal(100)
for(i in 1:length(lenderLoanData[,1])) {
    pair <- lenderLoanData[i,]
    
    colorIdx <- ceiling((pair$sortValue / maxSortValue) * length(lineColors))
    color <- lineColors[colorIdx]
    
    inter <- gcIntermediate(c(pair$lender_lon, pair$lender_lat), c(pair$loan_lon, pair$loan_lat), n=300, breakAtDateLine=TRUE, addStartEnd=TRUE)
    if(typeof(inter) == "list") {
        lines(inter[[1]], col=color, lwd=cfg$lenderLoanLines$size)
        lines(inter[[2]], col=color, lwd=cfg$lenderLoanLines$size)
    }
    else {
        lines(inter, col=color, lwd=cfg$lenderLoanLines$size)
    }
}

# Draw the lenders.
lenderColorPal <- colorRampPalette(c(cfg$lenderPoints$darkestColor, cfg$lenderPoints$lightestColor))
lenderColors <- lenderColorPal(100)
for(i in 1:length(lenderLocations[,1])) {
    lenderLoc <- lenderLocations[i,]
    
    colorIdx <- ceiling((lenderLoc$count / maxLenderCount)^(1/4) * length(lenderColors))
    points(lenderLoc$lon, lenderLoc$lat, pch=20, col=lenderColors[colorIdx], cex=cfg$lenderPoints$size)
}

# Draw the loans.
loanColorPal <- colorRampPalette(c(cfg$loanPoints$darkestColor, cfg$loanPoints$lightestColor))
loanColors <- loanColorPal(100)
for(i in 1:length(loanLocations[,1])) {
    loanLoc <- loanLocations[i,]
    colorIdx <- ceiling((loanLoc$count / maxLoanCount)^(1/4) * length(loanColors))
    points(loanLoc$lon, loanLoc$lat, pch=20, col=loanColors[colorIdx], cex=cfg$loanPoints$size)
}

# Write everything to the image.
dev.off()
