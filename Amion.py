import pandas as pd
import datetime as dt
import re
import builtins


class Amion:

    def __init__(self, sourceFile, shiftTimes = None):
        match type(sourceFile):
            case pd.DataFrame:
                self.rawdf = sourceFile
                self.sourceFileName = None
            case builtins.str:
                self.sourceFileName = sourceFile
                self.rawdf = pd.read_csv(self.sourceFileName,\
                        sep='\t',\
                            skip_blank_lines=True,\
                                names = ["shiftType", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]\
                                )
            case _:
                print("Error on source type match")
                
        self.df = pd.DataFrame(columns=["Start", "End", "Date", "ShiftNumber", "WeekDay", "Holiday", "ShiftType", "Doctor"])
        match type(shiftTimes):
            case NoneType:
                self.shifttimes = {
                    "Week 8a-4p": (dt.time(8, 0), dt.time(16, 0), 0),
                    "Week 3p-11p": (dt.time(15, 0), dt.time(23, 0), 1),

                    "Week night": (dt.time(23, 0), dt.time(9, 0), 2),

                    "Friday 3pm-11pm": (dt.time(15, 0), dt.time(23, 0), 1),
                    "Friday night 11p-9a": (dt.time(23, 0), dt.time(9, 0), 2),
                    "Saturday 9am-4pm": (dt.time(9, 0), dt.time(16, 0), 0),
                    "Saturday 3-11pm": (dt.time(15, 0), dt.time(23, 0), 1),
                    "Saturday 11pm-9am": (dt.time(23, 0), dt.time(9, 0), 2),
                    "Sunday 9am-4pm": (dt.time(9, 0), dt.time(16, 0), 0),
                    "Sunday 3-11pm": (dt.time(15, 0), dt.time(23, 0), 1),
                    "Sunday 11p-8a": (dt.time(23, 0), dt.time(8, 0), 2),
                    "Holiday 9am-4pm": (dt.time(9, 0), dt.time(16, 0), 0),
                    "Holiday 3pm-11pm": (dt.time(15, 0), dt.time(23, 0), 1),

                    "Holiday night": (dt.time(23, 0), dt.time(9, 0), 2),

                    "Hospitalist": (dt.time(0, 0), dt.time(0, 0), 3),
                    "Surgery": (dt.time(0, 0), dt.time(0, 0), 3),
                    "Anaesthesiology": (dt.time(0, 0), dt.time(0, 0), 3) 
                }

        return
    
    def toDataFrame(self):
        activeMonth = None
        activeYear = None
        dayDict = None
        for i, row in self.rawdf.iterrows():
            #IF HEADER ROW
            if pd.isnull(row["shiftType"]):
                #Range Header
                m = re.search(r'Call Schedule, (\d{1,2})/(\d{1,2}) to (\d{1,2})/(\d{1,2}), (\d{4})', str(row["Tue"]))
                if m:
                    startMonth, startDay, endMonth, endDay, year = m.groups()
                    startDate = dt.date(int(year), int(startMonth), int(startDay))
                    endDate = dt.date(int(year), int(endMonth), int(endDay))
                    activeMonth = startDate.month
                    activeYear = startDate.year
                else:
                    #Weekly Header
                    dayDict = dict()
                    for key in row[1:].keys():
                        #print(key, row[key])
                        daySpaceFullMonthName = re.search(r'^(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December)$', str(row[key]))
                        daySpaceFullHoliday = re.search(r'^(\d{1,2}) (?!January|February|March|April|May|June|July|August|September|October|November|December)(.*)$', str(row[key]))
                        dayDashMonthAbriviation = re.search(r'(\d{1,2})-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$', str(row[key]))
                        if daySpaceFullMonthName:
                            day, activeMonth = daySpaceFullMonthName.groups()
                            activeMonth = dt.datetime.strptime(activeMonth, "%B").month
                            day = int(day)
                            holiday = None

                        elif daySpaceFullHoliday:
                            day, holiday = daySpaceFullHoliday.groups()   
                            day = int(day)  

                        elif dayDashMonthAbriviation:
                            day, activeMonth = dayDashMonthAbriviation.groups()
                            activeMonth = dt.datetime.strptime(activeMonth,"%b").month
                            day = int(day)
                            holiday = None
                        else:
                            day = row[key]
                            holiday = None
                        if not pd.isnull(day):
                            day = int(day)
                            dayDict.update({key: (dt.date(activeYear, activeMonth, day), holiday)})
            
            else:
                assert dayDict is not None
                shiftType = row["shiftType"]
                StartTime, EndTime, ShiftNumber = self.shifttimes[shiftType]

                for key in row[1:].keys():
                    if not pd.isnull(row[key]):
                        date, holiday = dayDict[key]
                        weekday = date.strftime("%A")
                        doctor = row[key]

                        if EndTime >= StartTime:
                            StartDateTime = dt.datetime.combine(date, StartTime)
                            EndDateTime = dt.datetime.combine(date, EndTime)
                        
                        else:
                            StartDateTime = dt.datetime.combine(date, StartTime)
                            EndDateTime = dt.datetime.combine(date + dt.timedelta(days=1), EndTime)

                        self.df.loc[len(self.df)] = {
                                            "Start": StartDateTime,
                                            "End": EndDateTime,
                                            "Date": date,
                                            "ShiftNumber": ShiftNumber,
                                            "WeekDay": weekday,
                                            "Holiday": holiday,
                                            "ShiftType": shiftType,
                                            "Doctor": doctor
                                        }
           
        return self.df
 
    def toICS(self, outFile):
        import ics
        if self.df is None:
            self.toDataFrame()

        C = ics.Calendar()
        for i, row in self.df.iterrows():
            E = ics.Event()
            E.name = str(row["Doctor"]) + ' ' +  (row["ShiftType"]) + ' ' + str(row["WeekDay"]) + ' ' + str(row["Holiday"])
            E.begin = row["Start"]
            E.end = row["End"]
            C.events.add(E)

        with open(outFile, 'w') as my_file:
            my_file.writelines(C.serialize_iter())
        return

def main():
    #a = Amion(sourceFile=xl("'Amion Export'!A:H", headers=True), SourceAsDF=True).toDataFrame()
    #a = Amion(sourceFile='swap.txt', SourceAsDF=False).toDataFrame()
    source = pd.read_csv('SwapPython.csv')
    a = Amion(sourceFile=source).toDataFrame()
    print(a)
    return a

if __name__ == '__main__':
    main()