import  sys, urllib, json, csv, time, subprocess, os
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
#  python generate_custom_map.py <A> <B> <C>
#    A: Whether to fetch data for a specific lender or an entire 
#       lending team. L for lender, or T for team
#    B: The ID of the lender or lending team
#    C: Whether to force a re-fetch of the data from Kiva, even if 
#       it is already saved on your computer. Y for yes, N for no
#  
#####################################################################


# Initialize global vars.
SECONDS_BETWEEN_KIVA_QUERIES = 3
SECONDS_BETWEEN_GMAPS_QUERIES = 1


def read_kiva_data(url):
    stream = urllib.urlopen(url)
    dataStr = stream.read()
    try:
        data = json.loads(dataStr)
        if 'code' in data and 'message' in data:
            raise Exception(u'{0}: {1}'.format(data['code'], data['message']))
        return data
    except ValueError:
        raise Exception(u'Couldn\'t parse JSON: {0}'.format(dataStr))


def fetch_lender_location(indent, lender):
    if 'whereabouts' not in lender or len(lender['whereabouts']) == 0:
        raise Exception(u'{0} does not have any location set'.format(lender['uid']))
    
    lender_loc = lender['whereabouts'].lower()
    if 'country_code' in lender:
        lender_loc += ', ' + lender['country_code'].upper()
    
    # Remove some URLs commonly found in the lender locations. TODO: use regex...
    lender_loc = lender_loc.replace('http://www.kivafriends.org', '')
    lender_loc = lender_loc.replace('http://kivafriends.org', '')
    lender_loc = lender_loc.replace('www.kivafriends.org', '')
    lender_loc = lender_loc.replace('kivafriends.org', '')
    
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
        try:
            msg = u'{0}"{1}" is not a valid location according to Google Maps'.format(indent, lender_loc)
        except UnicodeEncodeError:
            msg = u'{0}(cannot be displayed) is not a valid location according to Google Maps'.format(indent)
        raise Exception(msg)
    
    coords = loc_data['Placemark'][0]['Point']['coordinates']
    
    # The lender location format: "<lat> <lon>"
    return '{0} {1}'.format(coords[1], coords[0])


def fetch_lender_data(lender_id):
    lender_locations = {}
    loan_locations = {}
    lender_loan_data = {}
    
    # Fetch the lender data.
    print u'Fetching data for lender {0}...'.format(lender_id)
    lenders_data = read_kiva_data('http://api.kivaws.org/v1/lenders/{0}.json'.format(lender_id))
    lender = lenders_data['lenders'][0]
    
    if 'loan_count' not in lender or lender['loan_count'] == 0:
        raise Exception(u'{0} does not have any loans'.format(lender['uid']))
    
    lender_loc = fetch_lender_location('', lender)
    lender_locations[lender_loc] = lender['loan_count']
    lender_loan_data[lender_loc] = {}
    
    # Fetch all the loans for this lender.
    print u'Fetching {0} loan(s) for lender {1}...'.format(lender['loan_count'], lender_id)
    page = 0
    num_pages = 1
    while True:
        page += 1
        if page > num_pages:
            break;
        
        time.sleep(SECONDS_BETWEEN_KIVA_QUERIES)
        print u' - Fetching page {0} of loans for lender {1}...'.format(page, lender_id)
        loans_data = read_kiva_data('http://api.kivaws.org/v1/lenders/{0}/loans.json?page={1}'.format(lender_id, page))
        
        # Update the paging.
        page = loans_data['paging']['page']
        num_pages = loans_data['paging']['pages']
        
        # Add these loans to the data.
        for loan in loans_data['loans']:
            loan_loc = loan['location']['geo']['pairs']
            if loan_loc not in loan_locations:
                loan_locations[loan_loc] = 1
            else:
                loan_locations[loan_loc] += 1
            
            if loan_loc not in lender_loan_data[lender_loc]:
                lender_loan_data[lender_loc][loan_loc] = 1
            else:
                lender_loan_data[lender_loc][loan_loc] += 1
    
    return (lender_locations, loan_locations, lender_loan_data)


def fetch_lenders_for_loan(indent, loan_id):
    lenders = set([])
    
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
                lenders.add(lender['uid'])
    
    return lenders


def fetch_data(is_individual_lender, id):
    if is_individual_lender:
        return fetch_lender_data(id)
    else:
        teamData = read_kiva_data('http://api.kivaws.org/v1/teams/using_shortname/{0}.json'.format(id))
        team = teamData['teams'][0]
        
        # [lenders_in_team] holds a map of uid -> geo point, and
        # [lender_locations*] hold maps of geo point -> count.
        lenders_in_team = {}
        lender_locations = {}
        lender_locations_with_loans = {}
        
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
                        if lender_loc not in lender_locations:
                            lender_locations[lender_loc] = 1
                        else:
                            lender_locations[lender_loc] += 1
                    except Exception, e:
                        print u'   -> [Warning] Could not process lender {0}: {1}'.format(lender['uid'], e)
        
        loan_locations = {}
        lender_loan_data = {}
        
        # Fetch all the loans for this team.
        print u'Fetching data for {0} loans in lending team {1}...'.format(team['loan_count'], id)
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
            
            # Add these loans to the data.
            for loan in loans_data['loans']:
                if 'id' in loan:
                    try:
                        lenders_for_loan = fetch_lenders_for_loan('   -> ', loan['id'])
                        
                        # Add this location to the dict of all [loan_locations].
                        loan_loc = loan['location']['geo']['pairs']
                        if loan_loc not in loan_locations:
                            loan_locations[loan_loc] = 1
                        else:
                            loan_locations[loan_loc] += 1
                        
                        # Intersect these lender ids with the ones in the team,
                        # adding to the [lender_loan_data].
                        for lender_id in lenders_for_loan:
                            if lender_id in lenders_in_team:
                                lender_loc = lenders_in_team[lender_id]
                                
                                if lender_loc not in lender_locations_with_loans:
                                    lender_locations_with_loans[lender_loc] = lender_locations[lender_loc]
                                
                                if lender_loc not in lender_loan_data:
                                    lender_loan_data[lender_loc] = {}
                                
                                if loan_loc not in lender_loan_data[lender_loc]:
                                    lender_loan_data[lender_loc][loan_loc] = 1
                                else:
                                    lender_loan_data[lender_loc][loan_loc] += 1
                    except Exception, e:
                        print u'   -> [Warning] Could not process lender {0}: {1}'.format(lender['uid'], e)
    
        return (lender_locations_with_loans, loan_locations, lender_loan_data)


def data_already_exists(id):
    try:
        open('data/{0}_lenders.csv'.format(id)).close()
        open('data/{0}_loans.csv'.format(id)).close()
        open('data/{0}_lender_loans.csv'.format(id)).close()
        return True
    except:
        return False


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


def write_data(id, lender_locations, loan_locations, lender_loan_data):
    try:
        os.mkdir('data')
    except:
        pass
    
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
    for lender_loc, loan_locations in lender_loan_data.iteritems():
        lender_loc_split = lender_loc.partition(' ')
        for loan_loc, count in loan_locations.iteritems():
            loan_loc_split = loan_loc.partition(' ')
            writer.writerow([
                lender_loc_split[0],
                lender_loc_split[2],
                loan_loc_split[0],
                loan_loc_split[2],
                haversine(lender_loc_split[0], lender_loc_split[2], loan_loc_split[0], loan_loc_split[2]),
                count
            ])
    file.close()


def is_arg_valid(arg, value1, value2):
    return arg.upper() == value1.upper() or arg.upper() == value2.upper()


def validate_args(args):
    try:
        if len(args) == 4:
            if(is_arg_valid(args[1], 'L', 'T') and
               is_arg_valid(args[3], 'Y', 'N')):
                return True
    except:
        pass
    return False


def main(*args):
    if validate_args(args) == False:
        print '\n  Proper Usage:\n'
        print '  ' + args[0] + ' A B C\n'
        print '     A: Whether to fetch data for a specific lender or an entire lending team. L for lender, or T for team'
        print '     B: The ID of the lender or lending team'
        print '     C: Whether to force a re-fetch of the data from Kiva, even if it is already saved on your computer. Y for yes, N for no'
        print '\n  Examples:\n'
        print '     generate_map.py L seand Y: force-fetches data and creates a map for user "seand"'
        print '     generate_map.py T buildkiva N: creates a map for team "buildkiva"'
        return 0
    
    # Set meaningful argument names.
    is_individual_lender = args[1].upper() == 'L'
    id = args[2]
    force_fetch_data = args[3].upper() == 'Y'
    
    try:
        if force_fetch_data == True or data_already_exists(id) == False:
            lender_locations, loan_locations, lender_loan_data = fetch_data(is_individual_lender, id)
            if len(lender_locations) == 0 or len(loan_locations) == 0:
                print u'\nERROR: There was not enough data (no lenders with valid locations or no loans) to create a map.'
                return
            write_data(id, lender_locations, loan_locations, lender_loan_data)
        
        # Execute the R script for drawing the map.
        process = subprocess.Popen([
            'Rscript',
            'draw_custom_map.R',
            '--args',
            id
        ])
        process.wait()
    except Exception, e:
        print u'ERROR: {0}'.format(e)


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
