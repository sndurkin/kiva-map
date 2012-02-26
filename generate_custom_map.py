import  sys, urllib, json, csv, time, subprocess, os, re, traceback
from    math import *

#####################################################################
#  
#  This script takes as input a Kiva lender or lending team and 
#  outputs a png with the data visualized on a world map. It will
#  fetch the data from Kiva, organize it, save it to csv files, 
#  and then execute an R script to use the csv files to draw the 
#  map.
#  
#  To execute:
#  
#  python generate_custom_map.py <A> <B>
#    A: Whether to fetch data for a specific lender or an entire 
#       lending team. L for lender, or T for team
#    B: The ID of the lender or lending team
#  
#####################################################################


# Initialize global constants.
SECONDS_BETWEEN_KIVA_QUERIES = 1
SECONDS_BETWEEN_GMAPS_QUERIES = 1
MAX_EXCEPTIONS_TOLERATED = 5


# [locations] is a map of lender location str to lat/lon point. These are
# saved locally so we can minimize the number of queries to the Google Maps API.
# Invalid locations are also stored (value is -1).
locations = {}

processed_loans = {}
lender_locations = {}
loan_locations = {}
lender_loan_data = {}


#####################################################################
# 
# Third-party Functions
# 
#####################################################################

# Credit: Michael Dunn, http://stackoverflow.com/a/4913653
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


#####################################################################
# 
# File I/O Functions
# 
#####################################################################

def create_dirs():
    for dir in [ 'data', 'images' ]:
        try:
            os.mkdir(dir)
        except:
            continue


def log_exception(data_str, data = ''):
    log_exception.num_errors_logged += 1
    
    log_exception.log_file.write('-----------------------------------------------------------\n')
    log_exception.log_file.write('Unexpected error processing {0}:\n{1}\n'.format(data_str, data))
    log_exception.log_file.write('-----------------------------------------------------------\n')
    traceback.print_exc(None, log_exception.log_file)
    log_exception.log_file.write('-----------------------------------------------------------\n\n')
    
    if(log_exception.num_errors_logged > MAX_EXCEPTIONS_TOLERATED):
        # Abort the program if the number of errors is too high.
        print 'Too many errors encountered; exiting the script.'
        sys.exit()


def log_warning(warning, data = ''):
    log_warning.num_warnings_logged += 1
    
    log_exception.log_file.write('-----------------------------------------------------------\n')
    try:
        log_exception.log_file.write(u'Warning: {0}\n{1}\n'.format(warning, data))
    except UnicodeEncodeError:
        log_exception.log_file.write(u'Exception when trying to display warning: {0}\n'.format(data))
    log_exception.log_file.write('-----------------------------------------------------------\n\n')


def unicode_csv_reader(utf8_data):
    csv_reader = csv.reader(utf8_data, delimiter=';')
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]


def read_data(id):
    # Read in the saved locations.
    try:
        file = open('data/saved_locations.json', 'r')
        global locations
        locations = json.loads(file.read())
        file.close()
    except IOError:
        pass
    except:
        log_exception('saved_locations.json')
    
    # Read in the processed loans.
    try:
        file = open('data/{0}_processed_loans.json'.format(id))
        global processed_loans
        processed_loans = json.loads(file.read())
        file.close()
    except IOError:
        pass
    except:
        log_exception('{0}_processed.json'.format(id))
    
    # Read in the lender locations.
    try:
        file = open('data/{0}_lenders.csv'.format(id))
        reader = unicode_csv_reader(file)
        reader.next()
        for row in reader:
            lender_locations['{0} {1}'.format(row[0], row[1])] = int(row[2])
        file.close()
    except IOError:
        # File doesn't exist.
        pass
    except:
        log_exception('{0}_lenders.csv'.format(id))
    
    # Read in the loan locations.
    try:
        file = open('data/{0}_loans.csv'.format(id))
        reader = unicode_csv_reader(file)
        reader.next()
        for row in reader:
            loan_locations['{0} {1}'.format(row[0], row[1])] = int(row[2])
        file.close()
    except IOError:
        # File doesn't exist.
        pass
    except:
        log_exception('{0}_loans.csv'.format(id))
    
    # Read in the lender-loan data.
    try:
        file = open('data/{0}_lender_loans.csv'.format(id))
        reader = unicode_csv_reader(file)
        reader.next()
        for row in reader:
            lender_loc = '{0} {1}'.format(row[0], row[1])
            if lender_loc not in lender_loan_data:
                lender_loan_data[lender_loc] = {}
            loan_loc = '{0} {1}'.format(row[2], row[3])
            
            lender_loan_data[lender_loc][loan_loc] = {
                'count': int(row[5]),
                'distance': row[4]
            }
        file.close()
    except IOError:
        # File doesn't exist.
        pass
    except:
        log_exception('{0}_lender_loans.csv'.format(id))


def write_data(id):
    # Write the saved locations.
    file = open('data/saved_locations.json', 'wb')
    file.write(json.dumps(locations))
    file.close()
    
    # Write the processed loans.
    file = open('data/{0}_processed_loans.json'.format(id), 'wb')
    file.write(json.dumps(processed_loans))
    file.close()
    
    # Write the lender locations.
    file = open('data/{0}_lenders.csv'.format(id), 'wb')
    writer = csv.writer(file, delimiter=';')
    writer.writerow([ 'lat', 'lon', 'count' ])
    for lender_loc, count in lender_locations.iteritems():
        lender_loc_split = lender_loc.partition(' ')
        writer.writerow([ lender_loc_split[0], lender_loc_split[2], count ])
    file.close()
    
    # Write the loan locations.
    file = open('data/{0}_loans.csv'.format(id), 'wb')
    writer = csv.writer(file, delimiter=';')
    writer.writerow([ 'lat', 'lon', 'count' ])
    for loan_loc, count in loan_locations.iteritems():
        loan_loc_split = loan_loc.partition(' ')
        writer.writerow([ loan_loc_split[0], loan_loc_split[2], count ])
    file.close()
    
    # Write the lender-loan data.
    file = open('data/{0}_lender_loans.csv'.format(id), 'wb')
    writer = csv.writer(file, delimiter=';')
    writer.writerow(['lender_lat', 'lender_lon', 'loan_lat', 'loan_lon', 'distance', 'count'])
    for lender_loc, loan_locs in lender_loan_data.iteritems():
        lender_loc_split = lender_loc.partition(' ')
        for loan_loc, lender_loan_obj in loan_locs.iteritems():
            loan_loc_split = loan_loc.partition(' ')
            writer.writerow([
                lender_loc_split[0],
                lender_loc_split[2],
                loan_loc_split[0],
                loan_loc_split[2],
                lender_loan_obj['distance'],
                lender_loan_obj['count']
            ])
    file.close()


#####################################################################
# 
# Data Processing Functions
# 
#####################################################################

def read_kiva_data(url):
    stream = urllib.urlopen(url)
    data_str = stream.read()
    data_str = re.sub('\\\\\'', '\'', data_str)

    try:
        data = json.loads(data_str)
        if 'code' in data and 'message' in data:
            raise Exception(u'{0}: {1}'.format(data['code'], data['message']))
        return data
    except ValueError:
        raise Exception(u'Couldn\'t parse JSON: {0}'.format(data_str))


def raise_invalid_location(indent, lender_loc):
    try:
        msg = u'{0}"{1}" is not a valid location according to Google Maps'.format(indent, lender_loc)
    except UnicodeEncodeError:
        msg = u'{0}(cannot be displayed) is not a valid location according to Google Maps'.format(indent)
    raise Exception(msg)


def fetch_lender_location(indent, lender):
    if 'whereabouts' not in lender or len(lender['whereabouts']) == 0:
        raise Exception(u'{0} does not have any location set'.format(lender['uid']))
    
    lender_loc = lender['whereabouts'].lower()
    if 'country_code' in lender:
        lender_loc += ', ' + lender['country_code'].lower()
    
    # Remove some URLs commonly found in the lender locations. TODO: use regex...
    lender_loc = lender_loc.replace('http://www.kivafriends.org', '')
    lender_loc = lender_loc.replace('http://kivafriends.org', '')
    lender_loc = lender_loc.replace('www.kivafriends.org', '')
    lender_loc = lender_loc.replace('kivafriends.org', '')
    
    # Check the cache first.
    if lender_loc in locations:
        if locations[lender_loc] == -1:
            raise_invalid_location(indent, lender_loc)
        
        return locations[lender_loc]            
    
    # Fetch the lender's lat/lon from Google Maps.
    try:
        print u'{0}Fetching lender location "{1}" from Google Maps'.format(indent, lender_loc)
    except UnicodeEncodeError:
        print u'{0}Fetching lender location (cannot be displayed) from Google Maps'.format(indent)
    
    time.sleep(SECONDS_BETWEEN_GMAPS_QUERIES)
    loc_url = urllib.urlopen(u'http://maps.googleapis.com/maps/geo?q={0}'.format(lender_loc).encode('utf-8'))
    loc_data = json.loads(loc_url.read())
    if 'Placemark' not in loc_data:
        # The address was not found by Google Maps, so alert the user and exit.
        locations[lender_loc] = -1
        raise_invalid_location(indent, lender_loc)
    
    coords = loc_data['Placemark'][0]['Point']['coordinates']
    
    # The lender location format: "<lat> <lon>"
    location = '{0} {1}'.format(coords[1], coords[0])
    locations[lender_loc] = location
    return location


def fetch_lender_data(lender_id):
    # Fetch the lender data.
    print u'Fetching data for lender {0}...'.format(lender_id)
    lenders_data = read_kiva_data('http://api.kivaws.org/v1/lenders/{0}.json'.format(lender_id))
    lender = lenders_data['lenders'][0]
    
    if 'loan_count' not in lender or lender['loan_count'] == 0:
        raise Exception(u'{0} does not have any loans'.format(lender['uid']))
    
    lender_loc = fetch_lender_location('', lender)
    if lender_loc not in lender_locations:
        lender_locations[lender_loc] = lender['loan_count']
    if lender_loc not in lender_loan_data:
        lender_loan_data[lender_loc] = {}
    
    # Fetch all the loans for this lender, starting with the newest.
    print u'Fetching {0} loan(s) for lender {1}...'.format(lender['loan_count'], lender_id)
    loans_to_process = []
    page = 0
    num_pages = 1
    while True:
        page += 1
        if page > num_pages:
            break
        
        time.sleep(SECONDS_BETWEEN_KIVA_QUERIES)
        print u' - Fetching page {0} of loans for lender {1}...'.format(page, lender_id)
        loans_data = read_kiva_data('http://api.kivaws.org/v1/lenders/{0}/loans.json?page={1}'.format(lender_id, page))
        
        # Update the paging.
        page = loans_data['paging']['page']
        num_pages = loans_data['paging']['pages']
        
        # Add these loans to a list.
        reached_processed_loan = False
        for loan in loans_data['loans']:
            loan_id = str(loan['id'])
            if loan_id in processed_loans:
                reached_processed_loan = True
            else:
                loans_to_process.insert(0, {
                    'id': loan_id,
                    'location': loan['location']['geo']['pairs']
                })
        
        # Once we reach a processed loan, we can exit knowing the rest
        # are older and have already been processed.
        if reached_processed_loan:
            break
    
    # Add the loans to the data.
    print u'Processing {0} new loans (since the last execution of this script).'.format(len(loans_to_process))
    for loan in loans_to_process:
        loan_loc = loan['location']
        if loan_loc not in loan_locations:
            loan_locations[loan_loc] = 1
        else:
            loan_locations[loan_loc] += 1
        
        if loan_loc not in lender_loan_data[lender_loc]:
            lender_loc_split = lender_loc.partition(' ')
            loan_loc_split = loan_loc.partition(' ')
            lender_loan_data[lender_loc][loan_loc] = {
                'count': 1,
                'distance': haversine(lender_loc_split[0], lender_loc_split[2], loan_loc_split[0], loan_loc_split[2])
            }
        else:
            lender_loan_data[lender_loc][loan_loc]['count'] += 1
        
        processed_loans[loan['id']] = 1


def fetch_lenders_for_loan(indent, loan_id):
    lenders = []
    
    page = 0
    num_pages = 1
    while True:
        page += 1
        if page > num_pages:
            break;
        
        time.sleep(SECONDS_BETWEEN_KIVA_QUERIES)
        print u'{0}Fetching page {1} of lenders for loan {2}...'.format(indent, page, loan_id)
        lenders_data = read_kiva_data('http://api.kivaws.org/v1/loans/{0}/lenders.json?page={1}'.format(loan_id, page))
        
        # Update the paging.
        page = lenders_data['paging']['page']
        num_pages = lenders_data['paging']['pages']
        
        # Add all these lender ids to the set.
        if 'lenders' in lenders_data:
            for lender in lenders_data['lenders']:
                lenders.append(lender['uid'])
    
    return lenders


def fetch_team_data(id):
    teamData = read_kiva_data('http://api.kivaws.org/v1/teams/using_shortname/{0}.json'.format(id))
    team = teamData['teams'][0]
    
    # [lenders_in_team] holds a map of uid -> geo point, and
    # [lender_locations*] hold maps of geo point -> count.
    lenders_in_team = {}
    lender_locations_tmp = {}
    
    # Fetch all the lenders in this team.
    print u'Fetching data for {0} lenders in lending team {1}...'.format(team['member_count'], id)
    page = 0
    num_pages = 1
    while True:
        page += 1
        if page > num_pages:
            break;
        
        time.sleep(SECONDS_BETWEEN_KIVA_QUERIES)
        print u' - Fetching page {0} of lenders for lending team {1}...'.format(page, id)
        lenders_data = read_kiva_data('http://api.kivaws.org/v1/teams/{0}/lenders.json?page={1}'.format(team['id'], page))
        
        # Update the paging.
        page = lenders_data['paging']['page']
        num_pages = lenders_data['paging']['pages']
        
        # Add these lenders to the data.
        for lender in lenders_data['lenders']:
            if 'uid' in lender:
                try:
                    lender_loc = fetch_lender_location('   -> ', lender)
                    lenders_in_team[lender['uid']] = lender_loc
                    if lender_loc not in lender_locations_tmp:
                        if lender_loc in lender_locations:
                            # Cover the case where the location has already been saved.
                            lender_locations_tmp[lender_loc] = lender_locations[lender_loc]
                        else:
                            lender_locations_tmp[lender_loc] = 1
                    else:
                        lender_locations_tmp[lender_loc] += 1
                except Exception, e:
                    log_warning(u'Problem fetching location for lender {0}'.format(lender['uid']), e)
    
    # Fetch all the loans for this team.
    print u'Fetching data for {0} loans in lending team {1}...'.format(team['loan_count'], id)
    loans_to_process = []
    page = 0
    num_pages = 1
    while True:
        page += 1
        if page > num_pages:
            break;
        
        time.sleep(SECONDS_BETWEEN_KIVA_QUERIES)
        print u' - Fetching page {0} of loans for lending team {1}...'.format(page, id)
        loans_data = read_kiva_data('http://api.kivaws.org/v1/teams/{0}/loans.json?page={1}'.format(team['id'], page))
        
        # Update the paging.
        page = loans_data['paging']['page']
        num_pages = loans_data['paging']['pages']
        
        # Add these loans to a list.
        reached_processed_loan = False
        for loan in loans_data['loans']:
            if 'id' in loan:
                loan_id = str(loan['id'])
                if loan_id in processed_loans:
                    reached_processed_loan = True
                else:
                    loans_to_process.insert(0, {
                        'id': loan_id,
                        'location': loan['location']['geo']['pairs']
                    })
        
        # Once we reach a processed loan, we can exit knowing the rest
        # are older and have already been processed.
        if reached_processed_loan:
            break
    
    # Add these loans to the data.
    print u'Processing {0} new loans (since the last execution of this script).'.format(len(loans_to_process))
    for loan in loans_to_process:
        try:
            lenders_for_loan = fetch_lenders_for_loan(' - ', loan['id'])
            if len(lenders_for_loan) > 0:
                # Add this location to the dict of all [loan_locations].
                loan_loc = loan['location']
                if loan_loc not in loan_locations:
                    loan_locations[loan_loc] = 1
                else:
                    loan_locations[loan_loc] += 1
                
                # Intersect these lender ids with the ones in the team,
                # adding the resulting set to the [lender_loan_data].
                for lender_id in lenders_for_loan:
                    if lender_id in lenders_in_team:
                        lender_loc = lenders_in_team[lender_id]
                        
                        if lender_loc not in lender_locations:
                            lender_locations[lender_loc] = lender_locations_tmp[lender_loc]
                        
                        if lender_loc not in lender_loan_data:
                            lender_loan_data[lender_loc] = {}
                        
                        if loan_loc not in lender_loan_data[lender_loc]:
                            lender_loc_split = lender_loc.partition(' ')
                            loan_loc_split = loan_loc.partition(' ')
                            lender_loan_data[lender_loc][loan_loc] = {
                                'count': 1,
                                'distance': haversine(lender_loc_split[0], lender_loc_split[2], loan_loc_split[0], loan_loc_split[2])
                            }
                        else:
                            lender_loan_data[lender_loc][loan_loc]['count'] += 1
            
            processed_loans[loan['id']] = 1
        except:
            log_exception(u'loan {0}'.format(loan['id']))


#####################################################################
# 
# Main + Other Functions
# 
#####################################################################

def validate_args(args):
    try:
        if len(args) == 3:
            if(args[1].upper() == 'L' or args[1].upper() == 'T'):
                return True
    except:
        pass
    return False


def main(*args):
    if validate_args(args) == False:
        print '\n  Proper Usage:\n'
        print '  ' + args[0] + ' A B\n'
        print '     A: Whether to fetch data for a specific lender or an entire lending team. L for lender, or T for team'
        print '     B: The ID of the lender or lending team'
        print '\n  Examples:\n'
        print '     generate_map.py L seand: creates a map for user "seand"'
        print '     generate_map.py T buildkiva: creates a map for team "buildkiva"'
        return 0
    
    # Set meaningful argument names.
    is_individual_lender = args[1].upper() == 'L'
    id = args[2]
    
    if is_individual_lender:
        file_id = 'l_{0}'.format(id)
    else:
        file_id = 't_{0}'.format(id)
    
    # Initialize data for logging.
    log_exception.num_errors_logged = 0
    log_warning.num_warnings_logged = 0
    log_exception.log_file = open('generate_custom_map.log', 'wb')
    
    create_dirs()
    read_data(file_id)
    
    try:
        if is_individual_lender:
            fetch_lender_data(id)
        else:
            fetch_team_data(id)
        
        if len(lender_locations) == 0 or len(loan_locations) == 0:
            print u'\nERROR: There was not enough data (no lenders with valid locations or no loans) to create a map.'
            return
        
        write_data(file_id)
        
        # Execute the R script for drawing the map.
        process = subprocess.Popen([
            'Rscript',
            'draw_custom_map.R',
            '--args',
            file_id
        ])
        process.wait()
    except SystemExit:
        # Write the data that we have before exiting.
        write_data(file_id)
    except Exception, e:
        print u'ERROR: {0}'.format(e)
    
    # Cleanup.
    log_exception.log_file.close()


if __name__ == '__main__':
    sys.exit(main(*sys.argv))

