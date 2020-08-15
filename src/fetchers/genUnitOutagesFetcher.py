import datetime as dt
import cx_Oracle
from typing import List, TypedDict


class Outage(TypedDict):
    unitName: str
    owners: str
    capacity: str
    outageDate: str
    outageTime: str
    revivalDate: str
    revivalTime: str
    reason: str


def fetchMajorGenUnitOutages(conStr: str, startDt: dt.datetime, endDt: dt.datetime) -> List[Outage]:
    """fetch major generating unit outages for a start and end dates, where
    start time between outage time and revive time
    outage time between start and end time
    outage time < end time but not revived (revived time = null)

    Args:
        conStr (str): connection string to reports database
        startDt (dt.datetime): start date of report time scope
        endDt (dt.datetime): end date of report time scope

    Returns:
        List[Outage]: list of outage objects that contain the following data
        unit_name, owners, capacity, outage date, outage time, revival date, revival time, reason
    """
    # connect to app database
    con = cx_Oracle.connect(conStr)

    # sql query to fetch the outages
    outagesFetchSql = '''select oe.ELEMENT_NAME as UNIT_NAME, 
    oe.OWNERS, oe.CAPACITY,
    oe.OUTAGE_DATETIME, oe.REVIVED_DATETIME,
    oe.OUTAGE_REMARKS, oe.REASON, oe.shutdown_tag
    from mis_warehouse.outage_events oe 
    where (oe.entity_name = 'GENERATING_UNIT') and 
    (
        (oe.OUTAGE_DATETIME between :1 and :2) 
        or ((oe.OUTAGE_DATETIME < :2) and (oe.REVIVED_DATETIME = NULL))
        or (:1 between oe.OUTAGE_DATETIME and oe.REVIVED_DATETIME)
    )
    '''

    # get cursor and execute fetch sql
    cur = con.cursor()
    cur.execute(outagesFetchSql, (startDt, endDt))
    colNames = [row[0] for row in cur.description]
    targetColumns = ['UNIT_NAME', 'OWNERS', 'CAPACITY',
                     'OUTAGE_DATETIME', 'REVIVED_DATETIME', 'OUTAGE_REMARKS', 'REASON', 'SHUTDOWN_TAG']
    if (False in [(col in targetColumns) for col in colNames]):
        # all desired columns not fetched, hence return empty
        return []
    # print(colNames)

    # fetch all rows
    dbRows = cur.fetchall()

    # initialise outages to be returned
    outages: List[Outage] = []

    unitNameInd = colNames.index('UNIT_NAME')
    ownersInd = colNames.index('OWNERS')
    capInd = colNames.index('CAPACITY')
    outDtInd = colNames.index('OUTAGE_DATETIME')
    reviveDtInd = colNames.index('REVIVED_DATETIME')
    remarksInd = colNames.index('OUTAGE_REMARKS')
    reasonInd = colNames.index('REASON')
    outageTagInd = colNames.index('SHUTDOWN_TAG')

    # iterate through each row to populate result outage rows
    for row in dbRows:
        unitName: str = row[unitNameInd]
        owners: str = row[ownersInd]
        cap: str = str(row[capInd])
        outDateStr: str = dt.datetime.strftime(row[outDtInd], "%d-%m-%Y")
        outTimeStr: str = dt.datetime.strftime(row[outDtInd], "%H:%M")
        revivalDateStr: str = 'Still out'
        revivalTimeStr: str = 'Still out'
        revivalDt = row[reviveDtInd]
        if not(revivalDt == None):
            revivalDateStr = dt.datetime.strftime(revivalDt, "%d-%m-%Y")
            revivalTimeStr = dt.datetime.strftime(revivalDt, "%H:%M")
        reason = row[reasonInd]
        remarks = row[remarksInd]
        outageTag = row[outageTagInd]
        if outageTag == 'Outage':
            outageTag = None
        reasonStr = ' / '.join([r for r in [outageTag, reason,
                                            remarks] if not(r == None)])
        # create outage record
        outageObj: Outage = {
            'unitName': unitName,
            'owners': owners,
            'capacity': cap,
            'outageDate': outDateStr,
            'outageTime': outTimeStr,
            'revivalDate': revivalDateStr,
            'revivalTime': revivalTimeStr,
            'reason': reasonStr
        }
        outages.append(outageObj)
    return outages
