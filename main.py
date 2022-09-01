import requests as requests
from datetime import date, timedelta, datetime
from jira import JIRA

everhourApiKey = None  # You will find it in your everhour settings
jiraApiKey = None  # Generate it here: https://id.atlassian.com/manage-profile/security/api-tokens
jiraEmail = None  # ex: piotr.kowalski@appunite.com
projectKey = None  # ex: XXXX,
jiraDomainName = None  # https://{jiraDomainName}.atlassian.net
yesterday = date.strftime(date.today() - timedelta(1), '%Y-%m-%d')
weekAgo = date.strftime(date.today() - timedelta(7), '%Y-%m-%d')
today = date.strftime(date.today(), '%Y-%m-%d')
startTime = weekAgo  # Provide date in YYYY-MM-DD format
endTime = today


def downloadDataFromEverhour():
    print('Downloading data from everhour')
    response = requests.get(
        f'https://api.everhour.com/team/time/export?from={startTime}&to={endTime}&fields=date%2Ctask',
        headers={"X-Api-Key": everhourApiKey, "X-Accept-Version": "1.2"})
    print('Writing data to output.csv')
    file = open('output.csv', mode='w')
    file.write("Issue Key,Time Spent,Date Started\n")
    for task in response.json():
        if task['task']['number'] is None or task['task']['number'].split('-')[0] != projectKey:
            continue
        file.write(f'{(task["task"]["number"])},{task["time"]},{task["date"]} 00:00:00Z\n')
    file.close()
    print("Exported data from everhour to output.csv")


def importDataInJira():
    print('Importing output.csv into jira')
    data = open('output.csv').read().split('\n')[1:-1]
    worklogs = [worklog.split(',') for worklog in data]
    authJira = JIRA(f'https://{jiraDomainName}.atlassian.net', basic_auth=(jiraEmail, jiraApiKey))
    print(f'Importing {len(worklogs)} worklogs')
    myAccountId = authJira.current_user()
    for worklog in worklogs:
        issue = worklog[0]
        timeSpent = int(worklog[1])
        started = datetime.fromisoformat(worklog[2].split(' ')[0])
        print(f'Adding worklog: {issue}: {timeSpent / 3600}h on {started.date()}')
        jiraWorklogs = authJira.worklogs(issue=issue)
        matchingWorklogs = list(
            filter(lambda x: datetime.fromisoformat(
                x.started.split("T")[0]) == started and x.author.accountId == myAccountId, jiraWorklogs))
        if len(matchingWorklogs) > 0:
            print('There are existing worklogs for this task on this date')
            worklogTimeSpent = 0
            for matchingWorklog in matchingWorklogs:
                worklogTimeSpent += int(matchingWorklog.timeSpentSeconds)
            print(f'JIRA time: {worklogTimeSpent / 3600}h, EVERHOUR time: {timeSpent / 3600}h')
            if worklogTimeSpent < timeSpent:
                missingTime = timeSpent - worklogTimeSpent
                print(f'Adding missing time: {missingTime / 3600}h')
                authJira.add_worklog(issue=issue, timeSpentSeconds=missingTime.__str__(), started=started)
            else:
                print("No time needs to be added. SKIPPING")
                continue
        else:
            authJira.add_worklog(issue=issue, timeSpentSeconds=timeSpent.__str__(), started=started)

    print("Imported worklogs to JIRA CHEERS!")


if __name__ == '__main__':
    if everhourApiKey is None or projectKey is None:
        print("PLEASE PROVIDE YOUR API KEY AND PROJECT KEY FOR EVERHOUR")
        exit()
    downloadDataFromEverhour()
    if jiraApiKey is None or jiraEmail is None:
        print("PLEASE PROVIDE API KEY, EMAIL AND DOMAIN NAME FOR JIRA")
        exit()
    importDataInJira()
