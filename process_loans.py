import  sys, traceback, urllib, json, csv, time
from    math import *

###############################################################################################
#  
#  This script iterates the loans found in the Kiva data snapshot (which should be located
#  in /loans with respect to this script), and for each one finds the lenders (using the
#  Kiva API) and their locations (using the Google Maps API). It compiles this data into
#  3 files:
#   - lender_locations.csv
#   - loan_locations.csv
#   - lender_loans.csv
#  
#  To execute: python process_loans.py <number of loan files>
#  
###############################################################################################
#  
#  Implementation Details
#  
#  Because there are so many loans to process, this script was written to be run several
#  times, working through them one file at a time. It stores metadata regarding its progress
#  in 2 files:
#   - locations.json
#   - loan_ids.json
#
#  The in-memory representation of the data isn't very intuitive; I was worried about the
#  memory usage because it grows on every execution. It is explained below:
#  
#  loan_ids: This is a map which holds 2 things:
#    1) every loan id that is processed, so we can ignore duplicates
#    2) the next loan file to process (key is 'file_num')
#  
#  locations: This is a map from location_string to location:
#    - location_string: The 'whereabouts' and 'country_code' of a Kiva lender
#    - location: format is '<lat> <lon>'
#  
#  loan_locations: This is a map from location to loan_info:
#    - location: format is '<lat> <lon>'
#    - loan_info: contains loan count, idx into idx_to_loan_map, lat, and lon
#  
#  idx_to_loan_map: This is a map from idx to loan_info. Indices are used to uniquely 
#    identify loans and lenders, so they can be persisted in files and then read back
#    into memory on the subsequent executions of this script.
#  
#  lender_locations: This is a map from location to lender_info:
#    - location: format is '<lat> <lon>'
#    - lender_info: contains lender count, idx into idx_to_lender_map, and a map which has
#        structure as loan_locations; it contains lender-loan count, distance between lender
#        and loan, and idx into idx_to_loan_map. This is done so that we can access the
#        correct loan when reading the data back into memory from lender_loans.csv.
#  
#  idx_to_lender_map: This is a map from idx to lender_info (same structure as loan_info).
#  
###############################################################################################


# Initialize global variables.
loan_ids = { 'file_num': 1 }
locations = {}
idx_to_lender_map = {}
lender_locations = {}
idx_to_loan_map = {}
loan_locations = {}

SECONDS_BETWEEN_KIVA_QUERIES = 1
SECONDS_BETWEEN_GMAPS_QUERIES = 1
MAX_EXCEPTIONS_TOLERATED = 30


def log_exception(data_str, data = ''):
    log_exception.num_errors_logged += 1
    
    log_exception.log_file.write('-----------------------------------------------------------\n')
    log_exception.log_file.write('Unexpected error processing {0}:\n{1}\n'.format(data_str, data))
    log_exception.log_file.write('-----------------------------------------------------------\n')
    traceback.print_exc(None, log_exception.log_file)
    log_exception.log_file.write('-----------------------------------------------------------\n\n')
    
    if(log_exception.num_errors_logged > MAX_EXCEPTIONS_TOLERATED):
        # Abort the program if the number of errors is too high.
        print 'Too many errors have been found; exiting the script.'
        sys.exit()


def log_warning(warning, data = ''):
    log_warning.num_warnings_logged += 1
    
    log_exception.log_file.write('-----------------------------------------------------------\n')
    try:
        log_exception.log_file.write(u'Warning: {0}\n{1}\n'.format(warning, data))
    except UnicodeEncodeError:
        log_exception.log_file.write(u'Exception when trying to display warning: {0}\n'.format(data))
    log_exception.log_file.write('-----------------------------------------------------------\n\n')


def add_lender_location(loc_str, lat, lon):
    lender_loc = '{0} {1}'.format(lat, lon)
    if lender_loc not in lender_locations:
        lender_idx = len(idx_to_lender_map)
        lender_locations[lender_loc] = {
            'idx': lender_idx,
            'count': 1,
            'lat': lat,
            'lon': lon,
            'loan_locations': {}
        }
        idx_to_lender_map[lender_idx] = lender_locations[lender_loc]
    locations[loc_str] = lender_locations[lender_loc]['idx']


def add_loan_location(lat, lon):
    loan_loc = '{0} {1}'.format(lat, lon)
    if loan_loc not in loan_locations:
        loan_idx = len(idx_to_loan_map)
        loan_locations[loan_loc] = {
            'idx': loan_idx,
            'count': 1,
            'lat': lat,
            'lon': lon
        }
        idx_to_loan_map[loan_idx] = loan_locations[loan_loc]
    else:
        loan_locations[loan_loc]['count'] += 1


# This function was taken from: http://stackoverflow.com/a/4913653 (thanks to Michael Dunn)
def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    return km


def add_lender_loan(lender_idx, loan_loc):
    lender_info = idx_to_lender_map[lender_idx]
    lender_info['count'] += 1
    loan_locs_from_lender = lender_info['loan_locations']
    
    loan_info = loan_locations[loan_loc]
    distance = haversine(lender_info['lat'], lender_info['lon'], loan_info['lat'], loan_info['lon'])
    
    if loan_loc not in loan_locs_from_lender:
        loan_locs_from_lender[loan_loc] = {
            'idx': loan_locations[loan_loc]['idx'],
            'lender_loan_count': 1,
            'distance': distance,
            'lat': loan_info['lat'],
            'lon': loan_info['lon']
        }
    else:
        loan_locs_from_lender[loan_loc]['lender_loan_count'] += 1


def add_lender_location_from_file(idx, lat, lon, count):
    lender_loc = '{0} {1}'.format(lat, lon)
    if lender_loc not in lender_locations:
        lender_locations[lender_loc] = {
            'idx': idx,
            'count': count,
            'lat': lat,
            'lon': lon,
            'loan_locations': {}
        }
        idx_to_lender_map[idx] = lender_locations[lender_loc]


def add_loan_location_from_file(idx, lat, lon, count):
    loan_loc = '{0} {1}'.format(lat, lon)
    if loan_loc not in loan_locations:
        loan_locations[loan_loc] = {
            'idx': idx,
            'count': count,
            'lat': lat,
            'lon': lon
        }
        idx_to_loan_map[idx] = loan_locations[loan_loc]


def add_lender_loan_from_file(lender_idx, loan_idx, lender_loan_count, distance):
    lender_info = idx_to_lender_map[lender_idx]
    loan_locs_from_lender = lender_info['loan_locations']
    
    loan_info = idx_to_loan_map[loan_idx]
    loan_loc = '{0} {1}'.format(loan_info['lat'], loan_info['lon'])
    
    if loan_loc not in loan_locs_from_lender:
        loan_locs_from_lender[loan_loc] = {
            'idx': loan_idx,
            'lender_loan_count': lender_loan_count,
            'distance': distance,
            'lat': loan_info['lat'],
            'lon': loan_info['lon']
        }


def unicode_csv_reader(utf8_data, delimiter=','):
    csv_reader = csv.reader(utf8_data, delimiter=delimiter)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]


def read_existing_data():
    # lender locations
    try:
        file = open('lender_locations.csv', 'r')
        reader = unicode_csv_reader(file, delimiter=';')
        reader.next()
        for row in reader:
            add_lender_location_from_file(int(row[0]), row[1], row[2], int(row[3]))
        file.close()
    except IOError:
        # It had trouble opening the file, so it may not exist.
        pass
    except:
        log_exception('lender_locations.csv')
    
    # loan locations
    try:
        file = open('loan_locations.csv', 'r')
        reader = unicode_csv_reader(file, delimiter=';')
        reader.next()
        for row in reader:
            add_loan_location_from_file(int(row[0]), row[1], row[2], int(row[3]))
        file.close()
    except IOError:
        pass
    except:
        log_exception('loan_locations.csv')
    
    # lender-loans
    try:
        file = open('lender_loans.csv', 'r')
        reader = unicode_csv_reader(file, delimiter=';')
        reader.next()
        for row in reader:
            add_lender_loan_from_file(int(row[0]), int(row[1]), int(row[2]), row[3])
        file.close()
    except IOError:
        pass
    except:
        log_exception('lender_loans.csv')
    
    # locations
    try:
        file = open('locations.json', 'r')
        global locations
        locations = json.loads(file.read())
        file.close()
    except IOError:
        pass
    except:
        log_exception('locations.json')
    
    # loan ids
    try:
        file = open('loan_ids.json')
        global loan_ids
        loan_ids = json.loads(file.read())
        file.close()
    except IOError:
        pass
    except:
        log_exception('load_ids.json')


def read_loan_data(file_path):
    try:
        file = open(file_path, 'r')
        data = json.loads(file.read())
        file.close()
        return data
    except:
        log_exception(file_path)
        return None


def write_existing_data():
    # lender locations
    file = open('lender_locations.csv', 'wb')
    writer = csv.writer(file, delimiter=';')
    writer.writerow(['idx', 'lat', 'lon', 'count'])
    for loc, info in lender_locations.iteritems():
        loc_split = loc.partition(' ')
        writer.writerow([
            info['idx'],
            loc_split[0],
            loc_split[2],
            info['count']
        ])
    file.close()
    
    # loan locations
    file = open('loan_locations.csv', 'wb')
    writer = csv.writer(file, delimiter=';')
    writer.writerow(['idx', 'lat', 'lon', 'count'])
    for loc, info in loan_locations.iteritems():
        loc_split = loc.partition(' ')
        writer.writerow([
            info['idx'],
            loc_split[0],
            loc_split[2],
            info['count']
        ])
    file.close()
    
    # lender-loans
    file = open('lender_loans.csv', 'wb')
    writer = csv.writer(file, delimiter=';')
    writer.writerow(['lender_idx', 'loan_idx', 'count', 'distance', 'lender_lat', 'lender_lon', 'loan_lat', 'loan_lon'])
    for lender_loc, lender_info in lender_locations.iteritems():
        lender_loc_split = lender_loc.partition(' ')
        for loan_loc, loan_info in lender_info['loan_locations'].iteritems():
            loan_loc_split = loan_loc.partition(' ')
            writer.writerow([
                lender_info['idx'],
                loan_info['idx'],
                loan_info['lender_loan_count'],
                loan_info['distance'],
                lender_loc_split[0],
                lender_loc_split[2],
                loan_loc_split[0],
                loan_loc_split[2]
            ])
    file.close()
    
    # locations
    file = open('locations.json', 'wb')
    file.write(json.dumps(locations))
    file.close()
    
    # loan ids
    file = open('loan_ids.json', 'wb')
    file.write(json.dumps(loan_ids))
    file.close()


def process_loan_data(loan_data):
    # Iterate through each loan until we've processed all the loans or
    # we've reached the user-supplied max:
    global loan_ids
    num_loans_processed = 0
    stop = 0
    for loan in loan_data['loans']:
        stop += 1
        if stop == 30:
            break
        
        # Ignore incomplete loan data.
        if 'id' not in loan or 'location' not in loan:
            continue
        
        # Ignore repeated loans.
        loan_id = str(loan['id'])
        if loan_id in loan_ids:
            continue
        
        try:
            time.sleep(SECONDS_BETWEEN_KIVA_QUERIES)
            
            # Fetch the lenders for this loan from Kiva.
            print u'{0}) Fetching lenders from kiva for loan with id "{1}".'.format(num_loans_processed + 1, loan_id)
            lenders_url = urllib.urlopen('http://api.kivaws.org/v1/loans/{0}/lenders.json'.format(loan_id))
            lenders_data = json.loads(lenders_url.read())
            
            # Ignore loans without any returned lenders.
            if not lenders_data['lenders']:
                loan_ids[loan_id] = 1
                num_loans_processed += 1
                print '   (this loan had no lenders)'.format(loan_id)
                log_warning(u'Loan with id {0} did not have any lenders'.format(loan_id), lenders_data)
                continue
            
            # Ignore loans without any valid lenders.
            has_valid_lenders = False
            for lender in lenders_data['lenders']:
                if 'whereabouts' in lender:
                    has_valid_lenders = True
                    break
            if not has_valid_lenders:
                loan_ids[loan_id] = 1
                num_loans_processed += 1
                print '   (this loan had no valid lenders)'.format(loan_id)
                log_warning(u'Loan with id {0} did not have any valid lenders'.format(loan_id), lenders_data)
                continue
            
            # Get the lat/lon pair for this loan.
            loan_loc = loan['location']['geo']['pairs']
            loan_loc_split = loan_loc.partition(' ')
            add_loan_location(loan_loc_split[0], loan_loc_split[2])
            
            # Iterate through each lender:
            num_lenders_processed = 0
            for lender in lenders_data['lenders']:
                # Ignore incomplete lender data.
                if 'whereabouts' not in lender:
                    continue
                
                loc_str = lender['whereabouts'].lower()
                if 'country_code' in lender:
                    loc_str += ', ' + lender['country_code'].upper()
                
                # Remove some URLs commonly found in location data.
                loc_str = loc_str.replace('http://www.kivafriends.org', '')
                loc_str = loc_str.replace('http://kivafriends.org', '')
                loc_str = loc_str.replace('www.kivafriends.org', '')
                loc_str = loc_str.replace('kivafriends.org', '')
                
                if loc_str not in locations:
                    time.sleep(SECONDS_BETWEEN_GMAPS_QUERIES)
                    
                    try:
                        # Fetch the lender's location from Google Maps.
                        try:
                            print u'\t-> Fetching lender location "{0}" from gmaps'.format(loc_str)
                        except UnicodeEncodeError:
                            print '\t-> Fetching lender location (cannot be displayed) from gmaps'
                        locUrl = urllib.urlopen(u'http://maps.googleapis.com/maps/geo?q={0}'.format(loc_str).encode('utf-8'))
                        locData = json.loads(locUrl.read())
                        if 'Placemark' not in locData:
                            # The address was not found by Google Maps, so save it as invalid and add a warning.
                            locations[loc_str] = -1
                            log_warning(u'Marked lender location "{0}" as invalid'.format(loc_str), locData)
                            continue
                        
                        coords = locData['Placemark'][0]['Point']['coordinates']
                        add_lender_location(loc_str, str(coords[1]), str(coords[0]))
                    except KeyboardInterrupt:
                        raise
                    except StandardError:
                        log_exception('lender', lender)
                        continue
                
                if locations[loc_str] == -1:
                    continue
                
                # Store the loan location within each lender location.
                add_lender_loan(locations[loc_str], loan_loc)
                num_lenders_processed += 1
            
            # If no lenders are processed, it might be the result of a bug, so it's logged for further evaluation.
            if num_lenders_processed == 0:
                log_warning('No lenders were processed for loan with id: ' + loan_id, lenders_data)
            
            # Store the newly processed loan id and increment the loan count.
            loan_ids[loan_id] = 1
            num_loans_processed += 1
        except KeyboardInterrupt:
            raise
        except:
            log_exception('loan', loan)
    
    return num_loans_processed


def validate_args(args):
    try:
        if len(args) >= 2 and int(args[1]) > 0:
            return True
    except ValueError:
        pass
    return False


def main(*args):
    if validate_args(args) == False:
        print 'Usage: ' + args[0] + ' <number of loan files>'
        return 0
    
    # Initialize variables used for exceptions.
    log_exception.num_errors_logged = 0
    log_warning.num_warnings_logged = 0
    log_exception.log_file = open('process_loans_log.txt', 'wb', 0)
    
    # Get the number of loan files to process from the user.
    numLoanFilesToProcess = int(args[1])
    loanFilesProcessed = 0
    total_loans_processed = 0
    
    # Start from where we left off; read in the existing loan data.
    print 'Reading in existing loan data...'
    read_existing_data()
    
    print 'Starting to process {0} loan files...'.format(numLoanFilesToProcess)
    while loanFilesProcessed < numLoanFilesToProcess:
        # Read in the loan data.
        file_path = 'loans/{0}.json'.format(loan_ids['file_num'])
        print 'Processing loans from {0}'.format(file_path)
        loan_data = read_loan_data(file_path)
        if loan_data is None:
            print 'Could not open {0}, exiting the script.'.format(file_path)
            return 0
        
        # Process the loan data and write the results to the files.
        num_loans_processed = process_loan_data(loan_data)
        total_loans_processed += num_loans_processed
        
        print 'Processed {0} loans from {1}'.format(num_loans_processed, file_path)
        loan_ids['file_num'] += 1
        write_existing_data()
        if num_loans_processed > 0:
            loanFilesProcessed += 1
    
    log_exception.log_file.close()
    print 'Finished processing {0} loans in {1} loan files.'.format(total_loans_processed, loanFilesProcessed)
    print 'There were {0} error(s) and {1} warning(s) logged.'.format(log_exception.num_errors_logged, log_warning.num_warnings_logged)


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
