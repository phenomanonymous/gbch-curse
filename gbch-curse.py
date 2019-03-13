#!/usr/bin/env python

from subprocess import Popen, PIPE
from datetime import datetime
from time import time, sleep, strftime, gmtime
import socket
import curses
import sys

"""CURSES COLORS"""
# 0 WHITE 8 16
# 1 BLACK 9
# 2 RED 10
# 3 GREEN 11
# 4 YELLOW 12
# 5 BLUE 13
# 6 MAGENTA 14
# 7 CYAN 15

"""
If you want to run this inside tmux:
    It defaults to screen, but we need it to be screen-256color, simply run `export TERM=screen-256color`, and that should do the trick
    Consider adding this into your bash_profile so that future tmux windows would get the proper value

        if [[ -n "$TMUX" ]]; then
          export TERM=screen-256color
        fi
"""

screen_hostname = socket.gethostname()
us_hosts = []
canada_hosts = []
stage_delete = False
stale_ids = []

def display_error_screen(stdscr, getch, error):
    height,width = stdscr.getmaxyx()
    stdscr.addstr(0, 0, "Failed to get job data:")
    stdscr.addstr(1, 0, error)
    stdscr.addstr(height-1, 0, "Q:")
    stdscr.addstr(height-1, 2, "Quit ", curses.color_pair(100))
    if getch in [ord('q'), ord('Q')]:
        sys.exit(0)

def update_canada_column(stdscr, height, width, x, jobs, status, color_id):
    i = i_start = 11
    stale_ids = []
    eodssr_jobs = eodperf_jobs = eodbin_jobs = latstat_jobs = 0
    for job_id, job in jobs.iteritems():
        if status == 'Stale' and job['name'] != 'error':
            stale_ids.append(job['id'])
        if "eodssr" in job['name']: eodssr_jobs+=1
        elif "eodperf" in job['name']: eodperf_jobs+=1
        elif "eodbin" in job['name']: eodbin_jobs+=1
        elif "latstat" in job['name']: latstat_jobs+=1
        else:
            if i < height:
                if status == 'Stale':
                    if job['name'] == 'error':
                        stdscr.addstr(i, x, "(%s) error-catcher | always runs" % job['id'], curses.color_pair(11))
                    else:
                        stdscr.addstr(i, x, "(%s) %s | %s" % (job['id'], job['name'], job['date']), curses.color_pair(color_id))
                else: stdscr.addstr(i, x, "%s | %s" % (job['name'], job['time']), curses.color_pair(color_id))
            i+=1
    if eodssr_jobs: stdscr.addstr(3, x, "(%d) eodssr jobs" % (eodssr_jobs), curses.color_pair(color_id))
    if eodperf_jobs: stdscr.addstr(4, x, "(%d) eodcsv jobs" % (eodperf_jobs), curses.color_pair(color_id))
    if eodbin_jobs: stdscr.addstr(5, x, "(%d) eodbin jobs" % (eodbin_jobs), curses.color_pair(color_id))
    stdscr.addstr(1, x, "%s (%s)" % (status, (eodssr_jobs + eodperf_jobs + eodbin_jobs + latstat_jobs)), curses.color_pair(color_id))
    stdscr.addstr(9, x, "%s (%d)" % (status, (i-i_start)), curses.color_pair(color_id))
    stdscr.addstr(height-1, 0, "To clear stale jobs: gbch-jdel %s" % (' '.join(stale_ids)), curses.color_pair(9))

def update_US_column(stdscr, height, width, x, jobs, status, color_id):
    global stale_ids

    i = i_start = 11
    times = []
    times_tomorrow = []
    times_dict = {}
    times_tomorrow_dict = {}
    ssreod_jobs = eodcsv_jobs = eodbin_jobs = latstat_jobs = 0
    if status == 'Stale': stale_ids = []
    for job_id, job in jobs.iteritems():
        if status == 'Stale' and job['name'] != 'error':
            stale_ids.append(job['id'])
        if "ssreod" in job['name']: ssreod_jobs+=1
        elif "eodcsv" in job['name']: eodcsv_jobs+=1
        elif "eodbin" in job['name']: eodbin_jobs+=1
        elif "latstat" in job['name']: latstat_jobs+=1
        else:
            if len(job['time'].strip()) > 5: # if it is more than just 'XX:XX', it has a date in it, and is scheduled after today
                if job['time'] not in times_tomorrow: times_tomorrow.append(job['time'])
            else:
                if job['time'] not in times: times.append(job['time'])
            if job['time'] not in times_dict: times_dict[job['time']] = []
            times_dict[job['time']].append(job['id'])
    times.sort()
    times_tomorrow.sort()
    times.extend(times_tomorrow)
    for time in times:
        for j in times_dict[time]:
            job = jobs[j]
            if i < height:
                if status == 'Stale':
                    if job['name'] == 'error':
                        stdscr.addstr(i, x, "(%s) error-catcher | always runs" % job['id'], curses.color_pair(11))
                    else:
                        stdscr.addstr(i, x, "(%s) %s | %s" % (job['id'], job['name'], job['date']), curses.color_pair(color_id))
                else: stdscr.addstr(i, x, "%s | %s" % (job['name'], job['time']), curses.color_pair(color_id))
            i+=1
    if ssreod_jobs: stdscr.addstr(3, x, "(%d) ssreod jobs" % (ssreod_jobs), curses.color_pair(color_id))
    if eodcsv_jobs: stdscr.addstr(4, x, "(%d) eodcsv jobs" % (eodcsv_jobs), curses.color_pair(color_id))
    if eodbin_jobs: stdscr.addstr(5, x, "(%d) eodbin jobs" % (eodbin_jobs), curses.color_pair(color_id))
    if latstat_jobs: stdscr.addstr(6, x, "(%d) latstat jobs" % (latstat_jobs), curses.color_pair(color_id))
    stdscr.addstr(1, x, "%s (%s)" % (status, (ssreod_jobs + eodcsv_jobs + eodbin_jobs + latstat_jobs)), curses.color_pair(color_id))
    stdscr.addstr(9, x, "%s (%d)" % (status, (i-i_start)), curses.color_pair(color_id))

def update_column(stdscr, height, width, x, jobs, status, color_id):
    if screen_hostname in us_hosts:
        update_US_column(stdscr, height, width, x, jobs, status, color_id)
    elif screen_hostname in canada_hosts:
        update_canada_column(stdscr, height, width, x, jobs, status, color_id)
    else: # undecided on how to handled unknown host, defaulting to US setup
        update_US_column(stdscr, height, width, x, jobs, status, color_id)

def update_screen(stdscr, jobs_data, next_check, getch='', error_alert=''):
    global stage_delete

    stdscr.clear()
    height,width = stdscr.getmaxyx()

    per_client_title = "Per-Client Jobs"
    general_title = "General Jobs"
    try:
        ##########################################################################
        update_column(stdscr, height, width, 0, jobs_data['Scheduled'], 'Scheduled', 16)
        update_column(stdscr, height, width, 30, jobs_data['Run'], 'Running', 12)
        update_column(stdscr, height, width, 60, jobs_data['Err'], 'Error', 10)
        update_column(stdscr, height, width, 80, jobs_data['Abrt'], 'Aborted', 12)
        update_column(stdscr, height, width, 100, jobs_data['Canc'], 'Cancelled', 14)
        update_column(stdscr, height, width, 120, jobs_data['Stale'], 'Stale', 9)
        update_column(stdscr, height, width, 160, jobs_data['Done'], 'Done', 11)
        ##########################################################################
        stdscr.addstr(0, width-len("Next check in: XX"), "Next check in: {0:02d}".format(int(next_check)))
        stdscr.addstr(0, ((width-len(per_client_title))/2), per_client_title)
        stdscr.addstr(0, 0, strftime('%H:%M:%S'))
        stdscr.addstr(2, 0, '-' * width)
        stdscr.addstr(8, ((width-len(per_client_title))/2), "%s %s" % (general_title, error_alert))
        stdscr.addstr(10, 0, '-' * width)
        ##########################################################################
        stdscr.addstr(height-1, 0, "Q:")
        stdscr.addstr(height-1, 2, "Quit ", curses.color_pair(100))
        stdscr.addstr(height-1, 7, "D:")
        stdscr.addstr(height-1, 9, "Delete Stale Jobs ", curses.color_pair(100))
        ##########################################################################
        if stage_delete:
            msg = " ARE YOU SURE YOU WANT TO DELETE STALE JOBS [EXCLUDES error-catcher]? (y/n) "
            stdscr.addstr(height/2, ((width-len(msg))/2), msg, curses.color_pair(100))
            stale_ids.insert(0, "gbch-jdel")
            stale_ids.insert(1, "-y")
            msg = ' '.join(stale_ids)
            stdscr.addstr((height/2)+1, ((width-len(msg))/2), msg, curses.color_pair(100))
        if getch and getch != -1:
            if stage_delete:
                if getch in [ord('y'), ord('Y')]:
                    stage_delete = False
                    p = Popen(stale_ids, stdout=PIPE) # execute gbch-jdel cmd with stale_ids as args
                    # handle unexpected output from popen...
                elif getch in [ord('n'), ord('N')]:
                    stage_delete = False
                else:
                    msg = " Unrecognized input: %s " % chr(getch)
                    stdscr.addstr((height/2)+1, ((width-len(msg))/2), msg, curses.color_pair(100))
            else:
                if (getch in [ord('d'), ord('D')]):
                    stage_delete = True
                    msg = " working... "
                    stdscr.addstr(height/2, ((width-len(msg))/2), msg, curses.color_pair(100))
                elif getch in [ord('q'), ord('Q')]:
                    sys.exit(0)
                else:
                    # stdscr.addstr(height-1, 0, "(GETCH = %s)" % getch) # for debugging
                    pass
        ##########################################################################
    except curses.ERR: # End of screen reached
        pass # Avoid an unhandled Exception crash, no real need to print errors/diagnostics. Count at top of column will let user know there are more jobs off the bottom
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        with open('curseex.log', 'w') as exfile:
            exfile.write(message)

        stdscr.clear()
        stdscr.addstr(0, 0, "Please widen your terminal window")
    stdscr.refresh()

def get_job_data(stdscr):
    today_dt = datetime.today()
    today_dt = today_dt.replace(hour=0, minute=0, second=0, microsecond=0) # set today_dt to today's datetime at 00:00:00.000 for date-comparison
    today_mdy = today_dt.strftime('%m/%d/%Y') # Get current date in MM/DD/YY format for comparison to job list's 'date' column
    today_ymd = today_dt.strftime('%Y%m%d') # Get current date in YYYYMMDD format so it can be removed from a job's cmdline args for display
    last_check_time = 0 # Init time (in seconds) last check occurred at to 0
    c = 0


    with open('curse.log', 'w') as outfile:
        while True:
            c = stdscr.getch()
            cur_time = time()
            if cur_time < last_check_time + 60: # If it hasn't been at least 60s since last check
                update_screen(stdscr, jobs, (last_check_time + 60 - cur_time), getch=c) # Update the screen so the clock and countdown refresh
                sleep(1) # Sleep 1 second
                continue # Begin loop again

            # It is simpler/cleaner (arguably faster?) to wipe & recreate dict every time, rather than serach by id and move from one status-dict to another
            # As of writing this there are ~400 jobs, so line-processing is minimal
            jobs = {'Scheduled': {}, 'Abrt': {}, 'Canc': {}, 'Done': {}, 'Run': {}, 'Err': {}, 'Stale': {}} # Init master dict of empty status-dicts

            try:
                p = Popen(["gbch-jlist"], stdout=PIPE) # Run `gbch-jlist` to get the gbch job list output, so that we can parse into something more readable
                joblist = p.communicate()[0] # Pipe the output of gbch-jlist to variable 'joblist'

                for line in joblist.strip().split('\n'): # strip the empty line off the bottom of stdout, then split by newline
                    try:
                        header, full_cmd, footer = line.split('"') # Split the line by " which encompasses a job's cmdline args in almost all cases
                        header = header.strip() # Remove outside whitespace
                        full_cmd = full_cmd.strip() # Remove outside whitespace
                        footer = footer.strip() # Remove outside whitespace
                        job_id, job_name = header.split(' ') # Split header by space into the job's id and the job's name
                        try:
                            status, date, jtime = footer.split() # This will raise an Exception if there is no status in the text, which means the job is scheduled to run at a later time
                        except ValueError:
                            date, jtime = footer.split()
                            status = 'Scheduled' # Invent and assign a status called 'Scheduled', since all jobs scheduled for the future have no status
                    except ValueError: # one and only one job doesn't have double quotes around the cmd, and it is gbch-error-alert.sh, hence this Exception
                        if "gbch-error-alert.sh" in line: # If we hit the expected ValueError for gbch-error-alert, treat the special case
                            cols = line.split()
                            job_id = cols[0]
                            job_name = '_'.join(cols[1:3])
                            full_cmd = cols[3]
                            status = 'Scheduled'
                            date = cols[4]
                            jtime = cols[5]
                        else: # We hit an unexpected ValueError Exception, this should only happen for gbch-error-alert
                            outfile.write("%s\n" % line)

                    # Clean up data for display
                    if '_' in job_name: job_name = '_'.join(job_name.split('_')[:-1]) # Remove the unnecessary date off the end of job_name
                    full_cmd = full_cmd.replace(today_ymd, '').strip() # Remove the unnecessary date off the front of full_cmd

                    # Set 'job' variable and handle it as needed
                    job = {'id':job_id, 'name':job_name, 'cmd':full_cmd, 'status':status, 'date':date, 'time':jtime} # Create job dict of all details
                    if datetime.strptime(date, "%m/%d/%Y") > today_dt: job['time'] = "%s %s" % (job['date'], job['time'])
                    elif today_dt > datetime.strptime(date, "%m/%d/%Y"):
                        status = 'Stale' # If current date is later than job date, job is stale
                        outfile.write("[%s] > [%s]\n" % (today_dt, datetime.strptime(date, "%m/%d/%Y")))
                    jobs[status][job_id] = job # Once any modifications to date values are made, add job to dict

                update_screen(stdscr, jobs, 60, getch=c) # Update the screen with current full job list data, and refresh
                last_check_time = time() # Now that a full check has been completed, reset timestamp of last check
            except OSError as e:
                display_error_screen(stdscr, c, "gbch-jlist: %s" % e)

def main(stdscr):
    stdscr.clear() # Wipe the screen, in case anything is somehow currently displayed on it
    stdscr.nodelay(1) # Should make getch non-blocking, we'll see...
    curses.start_color() # required initialization to use colors, not clearly understood why
    curses.use_default_colors() # required initialization to use colors, not clearly understood why
    for i in range(0, curses.COLORS): # required initialization to use colors, not clearly understood why
        curses.init_pair(i + 1, i, -1)
    curses.init_pair(100, 0, 6) # Black on Blue
    get_job_data(stdscr)

curses.wrapper(main)
