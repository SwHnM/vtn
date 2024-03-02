from flask import Flask, render_template, request, session
import os
from jira import JIRA
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv() # This will load the environment variables from .env

class JIRAService:
    def __init__(self, username, password, server_url):
        self.username = username
        self.password = password
        self.server_url = server_url
        self.jira = JIRA(basic_auth=(username, password), options={'server': server_url})

    def get_issue(self, issue_key):
        return self.jira.issue(issue_key)

    def get_issues_from_jql(self, jql_str):
        issues = self.jira.search_issues(jql_str)
        issue_list = [
            {
                'issue_key': i.key,
                'summary': i.fields.summary,
                'status': i.fields.status.name,
                'duedate': i.fields.duedate if i.fields.duedate is not None else str(i.fields.customfield_70900)[:10]
            }
            for i in issues
        ]
        return issue_list

    def get_summary(self, issue_key):
        issue = self.get_issue(issue_key)
        return issue.fields.summary

    def make_comment(self, issue, comment):
        issue.update(comment=comment)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # set a secret key for sessions

@app.route('/')
def index():
    return render_template('login.html')  # Jinja templating engine

@app.route('/login', methods=['POST'])
def login():
    username = os.getenv('MY_USERNAME')
    password = os.getenv('MY_PASSWORD')

    # Create a JIRAService instance
    jira_service = JIRAService(username, password, 'https://servicedesk.isha.in/')
    # jira_service = JIRAService("epub.jirabot", "Yogi$123", 'https://servicedesk.isha.in/')
    # jira_service = JIRAService(username, password, 'https://servicedesk.isha.in/')

    jql_query = '("Request participants" = '+ request.form['username'] + ' or reporter = ' + request.form['username'] + ') and status not in (Closed, Cancelled) and type not in ("Video Shoot Request","Footage Request")'  # JQL query to get issues assigned to the current user
    # jql_query = '("Request participants" = '+ session['username'] + ' or reporter = ' + session['username'] + ') and status not in (Closed, Cancelled) and type not in ("Video Shoot Request","Footage Request")'  # JQL query to get issues assigned to the current user
    # jql_query = "reporter = zhang.huiqing and component = 'Video Thumbnail Only' and status not in (closed,cancelled,Delivered)"
    matching_issues = jira_service.get_issues_from_jql(jql_query)

    # Group issues by due date
    issues_by_date = defaultdict(list)
    due_dates = []  # List to hold the datetime objects for sorting
    for issue in matching_issues:
        due_date = issue['duedate']
        if due_date and due_date != 'None':
            issue_date = datetime.strptime(due_date, "%Y-%m-%d")
            issues_by_date[issue_date].append(issue)  # Use datetime objects as keys
            due_dates.append(issue_date)  # Store datetime objects for sorting
        else:
            # Special handling for 'No Due Date'
            issues_by_date['No Due Date'].append(issue)

    # Sort the datetime objects
    due_dates.sort()
    
    # Add the 'No Due Date' key at the end of the sorted dates
    due_dates.append('No Due Date')

    # Create a new dictionary for the sorted issues with user-friendly date formatting
    sorted_issues_by_date = {}
    for issue_date in due_dates:
        if issue_date == 'No Due Date':
            # No need to change the format for 'No Due Date' group
            sorted_issues_by_date[issue_date] = issues_by_date[issue_date]
        else:
            # Convert datetime objects to user-friendly strings for use in the template
            formatted_date = issue_date.strftime("%d %b %Y")
            sorted_issues_by_date[formatted_date] = issues_by_date[issue_date]
    
    return render_template('issueview.html', issues_by_date=sorted_issues_by_date)

if __name__ == '__main__':
    app.run(debug=True)