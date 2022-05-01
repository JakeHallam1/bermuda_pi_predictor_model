from datetime import datetime as dt


def decimalYear(date):
    def s(date):
      # returns seconds since epoch
      return (date - dt(1900,1,1)).total_seconds()

    year = date.year
    startOfThisYear = dt(year=year, month=1, day=1)
    startOfNextYear = dt(year=year+1, month=1, day=1)

    yearElapsed = s(date) - s(startOfThisYear)
    yearDuration = s(startOfNextYear) - s(startOfThisYear)
    fraction = yearElapsed/yearDuration

    return date.year + fraction

def decimalYearGregorianDate(date, form="datetime"):
  def s(date):
    # returns seconds since epoch
    return (date - dt(1900,1,1)).total_seconds()
  
  # Shift the input of 1e-2 microseconds
  # This step accounts for rounding issues.
  date += 1e-5/(365.*86400.0)
  
  year = int(date)
  yearFraction = float(date) - int(date)
  startOfThisYear = dt(year=year, month=1, day=1)
  startOfNextYear = dt(year=year+1, month=1, day=1)
  secondsInYear = (s(startOfNextYear) - s(startOfThisYear)  ) * yearFraction
  # Find the month
  m = 1
  while m<=12 and s(dt(year=year, month=m, day=1)) - s(startOfThisYear) <= secondsInYear: m+=1
  m-=1
  # Find the day
  d = 1
  tdt = dt(year=year, month=m, day=d)
  while s(tdt) - s(startOfThisYear) <= secondsInYear:
    d+=1
    try: tdt=dt(year=year, month=m, day=d)
    except: break
  d-=1 
  # Find the time
  secondsRemaining = secondsInYear + s(startOfThisYear) - s(dt(year=year, month=m, day=d))
  hh = int(secondsRemaining/3600.)
  mm = int((secondsRemaining - hh*3600) / 60.)
  ss = int(secondsRemaining - hh*3600 - mm * 60) 
  ff = secondsRemaining - hh*3600 - mm * 60 - ss
  
  # Output formating
  if "tuple" == form:
    r = (year, m, d, hh, mm, ss, int(ff*1000))
  elif "datetime" == form:
    r = dt(year, m, d, hh, mm, ss, int(ff*1000))
  elif "dd-mm-yyyy" in form:
    r = str("%02i-%02i-%04i" % (d,m,year))
    if "hh:mm:ss" in form:
      r+=str(" %02i:%02i:%02i" % (hh,mm,ss))
  elif "yyyy-mm-dd" in form:
    r = str("%04i-%02i-%02i" % (year,m,d))
    if "hh:mm:ss" in form:
      r+=str(" %02i:%02i:%02i" % (hh,mm,ss))
  else:
    return None
  return r
