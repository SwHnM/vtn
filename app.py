from flask import Flask, render_template, request, session
import os
from jira import JIRA
from datetime import datetime
from collections import defaultdict

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
    username = request.form['username']
    password = request.form['passw']
    session['username'] = username
    session['password'] = password

    # Create a JIRAService instance
    jira_service = JIRAService(username, password, 'https://servicedesk.isha.in/')

    jql_query = "reporter = zhang.huiqing and component = 'Video Thumbnail Only' and status not in (closed,cancelled,Delivered)"
    matching_issues = jira_service.get_issues_from_jql(jql_query)

     # Group issues by due date
    issues_by_date = defaultdict(list)
    for issue in matching_issues:
        due_date = issue['duedate']
        if due_date and due_date != 'None':
            issue_date = datetime.strptime(due_date, "%Y-%m-%d")
            # Format it into a user-friendly format
            formatted_date = issue_date.strftime("%d %b %Y")
            issues_by_date[formatted_date].append(issue)
        else:
            # Assign issues without a due date to a special key
            issues_by_date['No Due Date'].append(issue)

    # Sort the dates, but keep 'No Due Date' at the end
    sorted_dates = sorted([date for date in issues_by_date.keys() if date != 'No Due Date'])
    sorted_dates.append('No Due Date')  # Add the 'No Due Date' key at the end of the sorted list
    sorted_issues_by_date = {date: issues_by_date[date] for date in sorted_dates}
    
    return render_template('issueview.html', issues_by_date=sorted_issues_by_date)

if __name__ == '__main__':
    app.run(debug=True)